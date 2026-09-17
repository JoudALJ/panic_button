"""Small terminal display helpers (colors, timer, banners)."""

import sys
import time

from colorama import Fore, Style, init

init(convert=True, strip=False)

BANNER = f"""{Fore.CYAN}{Style.BRIGHT}
   PANIC BUTTON
   A hostage rescue you cannot win. Probably.
{Style.RESET_ALL}"""

HELP_TEXT = f"""{Fore.YELLOW}
Commands: [1] look | [2] inventory | [3] cut wire | [4] stab kidnapper | [5] negotiate | [6] taunt | [7] call backup | [8] wait | [9] quit
(Type the number, then Enter.)
{Style.RESET_ALL}"""


def hr(width=50, color=Fore.YELLOW):
    print(color + "-" * width + Style.RESET_ALL)

# Colour-code each mood so the villain's temper reads at a glance.
# Green = good for you, yellow/cyan = getting worse, red = about to snap.
MOOD_COLORS = {
    "calm": Fore.WHITE,
    "happy": Fore.GREEN,
    "bored": Fore.CYAN,
    "irritated": Fore.YELLOW,
    "furious": Fore.RED,
}

def mood_color(mood):
    return MOOD_COLORS.get(str(mood or "").strip().lower(), Fore.WHITE)


def strikes_color(strikes, limit=3):
    # Green with no strikes, yellow part-way, red when the next strike is fatal.
    if strikes <= 0:
        return Fore.GREEN
    if strikes >= limit - 1:
        return Fore.RED
    return Fore.YELLOW

def bandit_label(mood, strikes=None, limit=3):
    # Speaker tag with mood + optional strike counter.
    if not mood:
        return "Bandit"
    color = mood_color(mood)
    tag = color + Style.BRIGHT + "[" + str(mood) + "]" + Style.RESET_ALL
    label = "Bandit " + tag
    # Negative strikes are hidden happiness progress, not a player-facing stat.
    if strikes is not None and strikes >= 0:
        label = label + " (" + color + str(strikes) + "/" + str(limit) + " strikes)" + Style.RESET_ALL
    return label


def print_mood_legend():
    """Explain the mood colors before the player starts making choices."""
    print("Bandit mood colors:")
    for mood, explanation in (
        ("calm", "the starting mood"),
        ("happy", "he is entertained by what you said"),
        ("bored", "dull answers add strikes; three strikes ends the negotiation"),
        ("irritated", "taunting adds strikes; two strikes ends the negotiation"),
        ("furious", "an offensive answer makes him shoot immediately"),
    ):
        print(f"  {mood_color(mood)}{Style.BRIGHT}[{mood}]{Style.RESET_ALL}: {explanation}")

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def show_clock(remaining):
    color = Fore.GREEN if remaining > 30 else Fore.YELLOW if remaining > 10 else Fore.RED
    print(color + Style.BRIGHT + f"[TIME LEFT: {format_time(remaining)}]")


def print_intro():
    print(BANNER)
    type_out("A bandit has a hostage and a bomb. You're the rookie sent in.",
             color=Fore.WHITE)
    hr()


# --- slow "typewriter" output ------------------------------------------------

# How fast AI text is revealed (characters per second). Lower = slower.
TYPEWRITER_CPS = 45.0


def type_out(text, color="", chars_per_second=TYPEWRITER_CPS, interactive=True):
    """Print ``text`` one character at a time to simulate the AI typing.

    While this is running the main loop's input is naturally blocked (we are
    inside this call), so the player watches the sentence appear instead of
    it flashing by. If a real keyboard is attached the player can press Enter
    to reveal the rest immediately.
    """
    # ANSI sequences must remain intact. Applying the reset code after each
    # character would split mood tags into visible text such as ``[33m``.
    # Tagged speaker lines are short, so print them in one pass.
    if "\x1b[" in text:
        print(color + text + Style.RESET_ALL)
        return

    # When stdout is redirected (tests, piped input) skip the slow path so
    # scripted runs stay fast and deterministic.
    if not sys.stdout.isatty():
        print(color + text + Style.RESET_ALL)
        return

    _wait_for_keypress_ready()
    printed = 0
    delay = 1.0 / chars_per_second if chars_per_second > 0 else 0
    for ch in text:
        if _key_pressed():
            # Player asked to skip: dump the remainder at once.
            print(color + text[printed:] + Style.RESET_ALL)
            _drain_keypresses()
            return
        sys.stdout.write(color + ch + Style.RESET_ALL)
        sys.stdout.flush()
        printed += 1
        time.sleep(delay)
    print()


# --- tiny cross-platform "a key is waiting" check (no extra dependency) -----

def _key_pressed():
    try:
        import msvcrt  # Windows
        return msvcrt.kbhit()
    except Exception:
        pass
    try:
        import select  # Unix
        return bool(select.select([sys.stdin], [], 0)[0])
    except Exception:
        return False


def _wait_for_keypress_ready():
    """Non-blocking-ish guard so a stray buffered Enter isn't consumed."""
    return None


def _drain_keypresses():
    while _key_pressed():
        try:
            import msvcrt
            msvcrt.getwch()
        except Exception:
            try:
                sys.stdin.read(1)
            except Exception:
                return
# --- live input with a ticking clock on the prompt line ----------------------

def live_input(prompt, remaining_fn, interval=0.5):
    """Read a line while re-drawing the countdown on the prompt continuously.

    Unlike ``input()``, this does not freeze the screen: every ``interval``
    seconds (and after every keypress) it repaints the prompt line so the
    player watches the clock count down *while they type*.

    ``remaining_fn`` is a zero-argument callable returning seconds left.
    Returns the entered string, or None on EOF / Ctrl-C.

    Falls back to plain ``input()`` when stdin isn't a real terminal (piped
    input, tests), so scripted runs still work.
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None
    buffer = []
    last_paint = 0.0
    def erase_line():
        # \r back to column 0, then clear everything to the end of the line so
        # a shorter repaint never leaves debris from a longer previous one.
        sys.stdout.write("\r\x1b[K")

    def paint():
        clock = _clock_tag(remaining_fn())
        erase_line()
        sys.stdout.write(f"{prompt}{clock} {''.join(buffer)}")
        sys.stdout.flush()

    paint()
    while True:
        ch = _read_char_blocking(timeout=0.2)
        now = time.time()
        if ch is None:
            # No key within the timeout: repaint so the clock keeps moving.
            if now - last_paint >= interval:
                paint()
                last_paint = now
            continue
        if ch in ("\r", "\n"):
            # Final clean paint, then move to a fresh line for the next print.
            paint()
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(buffer)
        if ch == "\x03":  # Ctrl-C
            sys.stdout.write("\n")
            sys.stdout.flush()
            return None
        if ch in ("\x08", "\x7f"):  # Backspace
            if buffer:
                buffer.pop()
        elif ch >= " ":
            buffer.append(ch)
        paint()
        last_paint = time.time()


def _clock_tag(remaining):
    """A compact, colour-coded ``[TIME LEFT mm:ss]`` tag for inline use."""
    if remaining > 60:
        color = Fore.GREEN
    elif remaining > 20:
        color = Fore.YELLOW
    else:
        color = Fore.RED
    return f"{color}{Style.BRIGHT}[{format_time(remaining)}]{Style.RESET_ALL}"


def _read_char_blocking(timeout=0.2):
    """Return one character, or None if none arrived within ``timeout``."""
    try:
        import msvcrt  # Windows
        end = time.time() + timeout
        while time.time() < end:
            if msvcrt.kbhit():
                return msvcrt.getwch()
            time.sleep(0.02)
        return None
    except Exception:
        pass
    try:
        import select  # Unix
        ready, _, _ = select.select([sys.stdin], [], timeout)
        if ready:
            return sys.stdin.read(1)
        return None
    except Exception:
        # Last resort: a single blocking read (no live clock, but works).
        try:
            return sys.stdin.read(1)
        except Exception:
            return None
