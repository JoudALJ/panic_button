"""Player-facing actions. Every path here leads to a different bad ending."""

import time
from colorama import Fore, Style
from . import endings, ai, menu
from .display import (
    live_input,
    type_out,
    show_clock,
    hr,
    bandit_label,
    mood_color,
    print_mood_legend,
)
from .constants import DEV_OVERRIDE_CODE


def has_item(state, item_name):
    """Demonstrates the `in` membership check on a list."""
    return item_name in state.inventory


def look(state):
    # Returns an AIRequest; the game loop waits for it while the clock ticks.
    return ai.AIRequest.narrate_scene()


def show_inventory(state):
    type_out("Carrying: " + ", ".join(state.inventory), color=Fore.WHITE)
    return None


def cut_wire(state):
    if not has_item(state, "pocketknife"):
        endings.gnawed_wire_panic(state)
        return None
    choice = menu.choose(
        "Cut which wire?",
        [("Red wire", "red"), ("Blue wire", "blue")],
    )
    if choice == "red":
        endings.red_wire_electrocution(state)
    else:
        endings.blue_wire_gas_leak(state)
    return None


# The strike budget now lives on GameState (state.strikes / state.strike_limit),
# driven by the mood effects in ai.MOOD_EFFECT. See negotiate() below.

def negotiate(state):
    """Run a full back-and-forth conversation with the kidnapper.

    Every line the player types is judged, which sets the villain's mood and
    moves him along one of three tracks:

    * ``happy``     - moves the hidden happiness counter down by one.
    * ``bored`` / ``irritated`` - adds one visible strike.
    * ``furious``   - he snaps on the spot; there is no coming back.

    Three bored strikes, two irritated strikes, or five happy lines in a row
    each have their own ending. Happy progress is hidden from the strike tag.

    Typing `end` / `done` / `leave` walks away (its own bad ending). Returns
    ``None`` - the game loop does not wait on it.
    """
    print(Fore.CYAN + Style.BRIGHT + "\n-- Negotiation started --" + Style.RESET_ALL)
    type_out("Talk to the kidnapper. Keep him entertained.", color=Fore.WHITE)
    type_out("Type 'end' when you want to stop talking.", color=Fore.WHITE)
    hr(50, Fore.CYAN)
    print_mood_legend()
    hr(50, Fore.CYAN)

    history = []          # list of (speaker, text)
    while not state.game_over.is_set():
        show_clock(state.time_remaining())
        line = live_input(
            Fore.CYAN + "You: ", state.time_remaining
        )
        if line is None:  # Ctrl-C / EOF
            endings.vanished_into_night(state)
            return None
        line = line.strip()

        if line.lower() in ("end", "done", "leave", "stop"):
            type_out("You lower your hands and back away from the talk.", color=Fore.YELLOW)
            return None
        if not line:
            type_out("Say something, or type 'end' to stop.", color=Fore.RED)
            continue
        # live_input already echoes the typed line on the prompt, so we
        # only need to record it here (avoids a doubled "You:").
        history.append(("Player", line))

        # 1) Judge the line (entertaining? boring? offensive?). This runs on a
        #    worker thread; we poll so the clock keeps ticking meanwhile.
        verdict = _await_verdict(state, history, line)
        if state.game_over.is_set():
            return None
        # The verdict picks the villain's mood for the tag beside his name.
        state.bandit_mood = ai.mood_for_verdict(verdict)
        effect = ai.mood_effect(state.bandit_mood)

        if effect == "shoot":
            # Furious: no strike budget, he just goes for the gun.
            tag = bandit_label(state.bandit_mood, state.strikes, state.strike_limit)
            type_out(f"{tag}: '...Wrong answer.'", color=Fore.RED)
            endings.hostage_shot_offended(state)
            return None
        if effect == "strike":
            state.strikes += 1
        elif effect == "heal":
            # The negative side is hidden over-happiness, not visible damage.
            state.strikes -= 1
        # 2) The villain replies in character (also threaded + typewriter).
        reply = _await_reply(state, history)
        if state.game_over.is_set():
            return None
        history.append(("Bandit", reply))

        # 3) Has he run out of patience?
        if state.bandit_mood == "happy" and state.strikes <= ai.HAPPY_TO_SHOOT:
            endings.hostage_murdered_happy(state)
            return None
        if state.bandit_mood == "irritated" and state.strikes >= ai.IRRITATED_TO_SHOOT:
            endings.hostage_shot_irritated(state)
            return None
        if state.bandit_mood == "bored" and state.strikes >= state.strike_limit:
            type_out("[The kidnapper is losing interest...]", color=Fore.YELLOW)
            endings.hostage_shot_bored(state)
            return None
        elif state.strikes > 0:
            remaining = state.strike_limit - state.strikes
            type_out(
                f"[Strikes: {state.strikes}/{state.strike_limit} - "
                f"{remaining} before he shoots]",
                color=mood_color(state.bandit_mood),
            )
    return None

def _await_verdict(state, history, line):
    """Wait for the ENTERTAINED/BORED/OFFENDED verdict, clock still ticking."""
    request = ai.AIRequest.judge_line(history[:-1], line)
    last_shown = None
    while request.pending:
        if state.game_over.is_set():
            return "BORED"
        remaining = int(state.time_remaining())
        if remaining != last_shown:
            show_clock(state.time_remaining())
            last_shown = remaining
        request.poll()
        time.sleep(0.1)
    return ai.classify_verdict(request.result, line)

def _await_reply(state, history):
    """Wait for the villain's next line, then type it out slowly."""
    request = ai.AIRequest.bandit_turn(history[:-1], history[-1][1])
    last_shown = None
    while request.pending:
        if state.game_over.is_set():
            return "(silence)"
        remaining = int(state.time_remaining())
        if remaining != last_shown:
            show_clock(state.time_remaining())
            last_shown = remaining
        request.poll()
        time.sleep(0.1)
    turn = request.result
    text = turn.reply if isinstance(turn, ai.ConversationTurn) else str(turn)
    tag = bandit_label(state.bandit_mood, state.strikes, state.strike_limit)
    type_out(f"{tag}: " + text, color=Fore.YELLOW)
    return text


def taunt(state):
    # Taunting is not a verdict-scored line, so it directly irritates him.
    state.bandit_mood = "irritated"
    state.strikes += 1
    type_out("You: 'Nice bomb. Did you build it yourself?'", color=Fore.YELLOW)
    if state.strikes >= ai.IRRITATED_TO_SHOOT:
        type_out("[You have pushed him too far.]", color=Fore.RED)
        endings.hostage_shot_irritated(state)
        return None
    return ai.AIRequest(
        "You are a smug, low-budget movie villain. Deliver ONE short menacing "
        "taunt to the rookie negotiator. Stay corny, never graphic.",
        "Taunt the rookie for stalling.",
        "The bandit laughs at your bluff.",
    )


def stab_kidnapper(state):
    if has_item(state, "pocketknife"):
        endings.stabbed_with_knife(state)
    else:
        endings.punched_bare_handed(state)
    return None


def call_backup(state):
    if has_item(state, "walkie_talkie"):
        endings.backup_never_arrives(state)
    else:
        endings.mimed_call_insults_bandit(state)
    return None


def do_wait(state):
    type_out("Nothing happens. The clock disagrees.", color=Fore.WHITE)
    return None


def quit_game(state):
    endings.abandoned_post(state)
    return None


def check_dev_override(state, command):
    """The only real win path -- a hidden developer command."""
    (secret,) = DEV_OVERRIDE_CODE
    if command in (secret.lower(), f"devmode {secret.lower()}"):
        endings.dev_win(state)
        return True
    return False
