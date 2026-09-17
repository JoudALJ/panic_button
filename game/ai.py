"""AI flavor text via a local Ollama model, run on a background thread.

Two things matter here, and they are the reason this is threaded rather than
a simple blocking call:

1. The countdown clock must keep ticking while the model is thinking. If we
   called Ollama directly the whole game would freeze (and the clock would
   appear to stop) for several seconds. So requests run on a worker thread
   and the game polls for the result.
2. The reply is handed back as *text*, so the caller can reveal it slowly with
   the typewriter effect instead of dumping it all at once.

Everything degrades to a canned line if Ollama isn't installed or isn't
running, so live demos never crash.
"""

import queue
import random
import threading

FALLBACK_LINES = [
    "The bandit stares at you, unimpressed.",
    "The bandit checks their watch, bored.",
    "The bandit says: 'Cool speech. Anyway.'",
]

FALLBACK_NARRATION = (
    "A bomb. A hostage. A bandit monologuing. The rookie's hands are shaking."
)

MODEL_NAME = "llama3.2"

_SYSTEM_BANDIT = (
    "You are a silly, low-budget movie villain holding a hostage. Reply in "
    "ONE short, sarcastic sentence to the negotiator. Never agree to let the "
    "hostage go."
)
_SYSTEM_NARRATOR = (
    "You are the dramatic narrator of a cheesy action movie. Describe the "
    "scene in ONE punchy sentence (max 20 words). Be vivid but silly."
)

# Used to decide whether the rookie's line was fun, dull or offensive. The model
# must answer with a single keyword so the game can branch on it reliably.
_SYSTEM_JUDGE = (
    "You are the hostage-holding villain judging the negotiator's latest line. "
    "Answer with EXACTLY ONE word, no punctuation:\n"
    "ENTERTAINED - if the line is funny, charming, clever or genuinely calming.\n"
    "BORED - if the line is dull, generic, repetitive or a non-answer.\n"
    "OFFENDED - if the line insults, threatens or mocks the villain."
)

# Words that reliably mean the villain takes it personally, checked before
# asking the model so the game reacts instantly even with no AI running.
_OFFENSIVE_MARKERS = (
    "stupid", "idiot", "dumb", "ugly", "loser", "shut up", "moron",
    "kill you", "hate you", "shoot you", "your mother", "f***",
)
_COMPLIMENT_MARKERS = (
    "pretty", "beautiful", "handsome", "smart", "clever", "kind",
    "nice", "great", "good job", "love your",
)

# Fallback verdicts used when the model is unavailable.
FALLBACK_VERDICTS = ["ENTERTAINED", "BORED", "BORED", "ENTERTAINED", "BORED"]

# How the villain feels, shown beside his name as "Bandit [mood]: ...".
# The verdict we already compute for every line drives the mood, so the tag is
# never out of step with his behaviour.
MOOD_FOR_VERDICT = {
    "ENTERTAINED": "happy",
    "BORED": "bored",
    "OFFENDED": "furious",
}
DEFAULT_MOOD = "calm"

# How much a mood moves the villain toward the shoot ending:
#   "heal"   - a happy line moves the hidden happiness counter down by one.
#   "strike" - adds one strike; reach STRIKES_TO_SHOOT and he shoots.
#   "shoot"  - he snaps on the spot, no strikes required.
#   "none"   - no effect (the neutral starting mood).
MOOD_EFFECT = {
    "happy": "heal",
    "bored": "strike",
    "irritated": "strike",
    "furious": "shoot",
    "calm": "none",
}

# The villain tolerates this many strikes before he reaches for the gun.
STRIKES_TO_SHOOT = 3
# Irritation is a shorter fuse than ordinary boredom.
IRRITATED_TO_SHOOT = 2
# Happiness can go too far, but this negative value stays hidden from the player.
HAPPY_TO_SHOOT = -5

def mood_for_verdict(verdict):
    # Map an ENTERTAINED/BORED/OFFENDED verdict to a short mood word.
    return MOOD_FOR_VERDICT.get(str(verdict or "").strip().upper(), DEFAULT_MOOD)


def mood_effect(mood):
    # Map a mood to its effect on the strike count (see MOOD_EFFECT).
    return MOOD_EFFECT.get(str(mood or "").strip().lower(), "none")


def is_available():
    """True only if the ollama package is importable (no network call)."""
    try:
        import ollama  # noqa: F401

        return True
    except Exception:
        return False


def _chat(system_prompt, user_prompt):
    """Send one chat turn to Ollama. Returns text, or None on any failure."""
    try:
        import ollama  # imported lazily so the game runs without it

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"num_predict": 60},  # short replies -> fast, demo-friendly
        )
        text = response["message"]["content"].strip()
        return text or None
    except Exception:
        return None


def _classify(text, fallback):
    # Turn a free-text model answer into a clean verdict keyword.
    # Keyword scan first (catches an obviously offensive line even if the
    # model rambles), then fall back to the supplied default.
    lowered = (text or '').lower()
    for m in _OFFENSIVE_MARKERS:
        if m in lowered:
            return 'OFFENDED'
    for verdict in ('ENTERTAINED', 'OFFENDED', 'BORED'):
        if verdict.lower() in lowered:
            return verdict
    return fallback


def classify_verdict(model_result, player_line):
    """Keep obvious insults and compliments stable despite model drift."""
    line = str(player_line or '').lower()
    if any(marker in line for marker in _OFFENSIVE_MARKERS):
        return "OFFENDED"
    if any(marker in line for marker in _COMPLIMENT_MARKERS):
        return "ENTERTAINED"
    return _classify(model_result, "BORED")


class ConversationTurn:
    # Result of one negotiation turn: the villain's line + a verdict.
    #
    # reply   - what the bandit says back.
    # verdict - ENTERTAINED / BORED / OFFENDED.

    def __init__(self, reply, verdict):
        self.reply = reply
        self.verdict = verdict

    @classmethod
    def player(cls, player_line):
        verdict = _classify(player_line, random.choice(FALLBACK_VERDICTS))
        return cls(random.choice(FALLBACK_LINES), verdict)


class AIRequest:
    """A single AI request running on a worker thread.

    Usage:
        req = AIRequest.bandit_reply("please calm down")
        while req.pending:      # poll each loop iteration; the clock keeps going
            ...
        print(req.result)
    """

    def __init__(self, system_prompt, user_prompt, fallback):
        self._queue = queue.Queue()
        self.result = None
        self._thread = threading.Thread(
            target=self._run,
            args=(system_prompt, user_prompt, fallback),
            daemon=True,
        )
        self._thread.start()

    def _run(self, system_prompt, user_prompt, fallback):
        text = _chat(system_prompt, user_prompt)
        if text:
            result = text
        else:
            result = fallback
        # When the caller expects a ConversationTurn (fallback is one), wrap a
        # raw model string up so the shape stays consistent either way.
        if isinstance(fallback, ConversationTurn) and isinstance(result, str):
            result = ConversationTurn(result, fallback.verdict)
        self._queue.put(result)

    @property
    def pending(self):
        return self.result is None

    def poll(self):
        """Return the result once ready, otherwise None (non-blocking)."""
        if self.result is not None:
            return self.result
        try:
            self.result = self._queue.get_nowait()
        except queue.Empty:
            return None
        return self.result

    @classmethod
    def bandit_reply(cls, player_line):
        return cls(_SYSTEM_BANDIT, player_line, random.choice(FALLBACK_LINES))

    @classmethod
    def narrate_scene(cls, context="the bomb room"):
        prompt = (
            f"Describe the current scene: {context}. The hostage is tied up, a "
            "bomb counts down, and a bandit is watching."
        )
        return cls(_SYSTEM_NARRATOR, prompt, FALLBACK_NARRATION)

    # -- multi-turn conversation -------------------------------------------

    @classmethod
    def bandit_turn(cls, history, player_line):
        """One conversational turn.

        ``history`` is a list of ``(speaker, text)`` tuples so far (speaker is
        "Player" or "Bandit"). Returns a special result object exposing both
        ``reply`` (the villain's next line) and ``verdict`` (one of
        ENTERTAINED / BORED / OFFENDED).
        """
        lines = []
        for speaker, text in history:
            lines.append(f"{speaker}: {text}")
        lines.append(f"Player: {player_line}")
        convo = "\n".join(lines)
        reply_prompt = (
            "Here is the negotiation so far. Stay in character as the villain."
            f"\n\n{convo}\n\nBandit:"
        )
        return cls(
            _SYSTEM_BANDIT,
            reply_prompt,
            ConversationTurn.player(player_line),
        )

    @classmethod
    def judge_line(cls, history, player_line):
        """Return an AIRequest whose result is a verdict keyword."""
        convo = "\n".join(f"{s}: {t}" for s, t in history)
        prompt = (
            f"Negotiation so far:\n{convo}\nPlayer: {player_line}\n\n"
            "Verdict for the Player's latest line?"
        )
        return cls(_SYSTEM_JUDGE, prompt, random.choice(FALLBACK_VERDICTS))


# --- simple blocking wrappers kept for convenience / non-interactive use ----

def bandit_reply(player_line):
    req = AIRequest.bandit_reply(player_line)
    while req.pending:
        req.poll()
        threading.Event().wait(0.05)
    return req.result


def narrate_scene(context="the bomb room"):
    req = AIRequest.narrate_scene(context)
    while req.pending:
        req.poll()
        threading.Event().wait(0.05)
    return req.result
