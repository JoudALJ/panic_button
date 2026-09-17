"""Every possible ending. Each one is a different way for the round
to go wrong (or, in exactly one case, right). None of these exit the
process -- the main loop decides whether to restart afterward.
"""

from colorama import Fore, Style
from .display import hr, type_out


def _end(state, won):
    state.game_over.set()
    state.won = won


def _bad_ending(state, headline, detail):
    hr(50, Fore.RED)
    # Reveal the outcome one character at a time so the player can read what
    # their choice actually did before the GAME OVER banner lands.
    type_out(headline, color=Fore.RED + Style.BRIGHT)
    type_out(detail, color=Fore.RED)
    print(Fore.MAGENTA + Style.BRIGHT + ">>> GAME OVER <<<")


# --- cutting wires -----------------------------------------------------

def red_wire_electrocution(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "ZAP. The red wire was live mains power, not a bomb wire.",
        "You are electrocuted, which also sets off the bomb. Two for one.",
    )


def blue_wire_gas_leak(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "HISSSS... the blue wire releases a hidden gas leak.",
        "A spark from your pocketknife lights it. The room goes up.",
    )


def gnawed_wire_panic(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "With no knife, you try gnawing the wire like a confused beaver.",
        "The bandit finds this deeply unsettling and hits the detonator.",
    )


# --- attacking the kidnapper ---------------------------------------------

def stabbed_with_knife(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "You lunge at the kidnapper with the pocketknife.",
        "They sidestep, take the knife, and things get much worse from there.",
    )


def punched_bare_handed(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "You throw a bare-handed punch at a man holding a detonator.",
        "This goes exactly as badly as it sounds.",
    )


# --- negotiation ---------------------------------------------------------

def negotiation_backfires(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "Your speech about the power of friendship lands very badly.",
        "The bandit, offended, decides the hostage will not be needing it.",
    )


def negotiation_over_radio_backfires(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "You broadcast your speech over the walkie-talkie for dramatic effect.",
        "Feedback screech drowns out the message and spooks the bandit into acting.",
    )


def hostage_shot_bored(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "The bandit stops mid-sentence. 'You're boring me,' he says.",
        "He raises the pistol, sighs, and shoots the hostage. Then the bomb.",
    )


def hostage_shot_irritated(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "The bandit snaps: 'Two chances was generous.'",
        "Irritation wins. He shoots the hostage before you can say anything else.",
    )


def hostage_murdered_happy(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "The bandit grins. 'I have never felt this good.'",
        "In a burst of unbearable joy, he shoots the hostage and skips away.",
    )


def hostage_shot_offended(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "You said exactly the wrong thing.",
        "The bandit's face goes flat, he shoots the hostage, and walks out.",
    )


# --- calling backup --------------------------------------------------------

def backup_never_arrives(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "Backup radios back: 'two minutes out.' It is never two minutes.",
        "You keep waiting. The bomb does not share your patience.",
    )


def mimed_call_insults_bandit(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "With no walkie-talkie, you mime calling for backup instead.",
        "The bandit is insulted by your impression and lobs the bomb at you.",
    )


# --- quitting / running out the clock -------------------------------------

def abandoned_post(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "You climb out a window and just... leave.",
        "The bomb, unbothered by your exit, detonates right on schedule.",
    )


def vanished_into_night(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "You disconnect without a word.",
        "The bomb does not care that you left. It goes off anyway.",
    )


def clock_runs_out(state):
    _end(state, won=False)
    _bad_ending(
        state,
        "TIME'S UP. You never committed to a plan.",
        "The timer hits zero while you're still deciding what to do.",
    )


# --- the one and only win ------------------------------------------------

def dev_win(state):
    _end(state, won=True)
    hr(50, Fore.GREEN)
    type_out("DEVELOPER OVERRIDE ACCEPTED.", color=Fore.GREEN + Style.BRIGHT)
    type_out("Bomb disarmed. Hostage saved. You are the developer.", color=Fore.GREEN)
    print(Fore.GREEN + Style.BRIGHT + ">>> GAME OVER: YOU WIN <<<")
