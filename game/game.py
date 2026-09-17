"""The main game loop and countdown watchdog.

Features layered on top of the original terminal game:

* **Numbered commands** - every command is shown as ``[n] label`` and can be
  picked by typing its number (see ``COMMANDS`` and ``HELP_TEXT``).
* **A clock that never stops** - the countdown is wall-clock based and the
  watchdog thread ends the game the moment it hits zero, *even while an AI
  request is still in flight*. While the AI is thinking we keep redrawing the
  clock so the player sees it counting down.
* **Slow AI text** - AI replies are revealed one character at a time by the
  typewriter in ``display.type_out``; because that runs synchronously, command
  input is locked until the sentence finishes (Enter skips it).
"""

import time
import threading

from colorama import Fore, Style

from .state import GameState
from .display import print_intro, HELP_TEXT, show_clock, type_out, live_input, bandit_label
from . import actions, endings, menu, ai

# Numbered commands: (number, label, function). The number is what the player
# types; the label is shown in the helper line.
COMMANDS = {
    1: ("look", actions.look),
    2: ("inventory", actions.show_inventory),
    3: ("cut wire", actions.cut_wire),
    4: ("stab kidnapper", actions.stab_kidnapper),
    5: ("negotiate", actions.negotiate),
    6: ("taunt", actions.taunt),
    7: ("call backup", actions.call_backup),
    8: ("wait", actions.do_wait),
    9: ("quit", actions.quit_game),
}

# Also allow the old words, so both styles work.
NAME_TO_NUMBER = {name: num for num, (name, _fn) in COMMANDS.items()}


def countdown_watchdog(state):
    """Forces a bad ending the instant time runs out, even mid-input()."""
    while not state.game_over.is_set():
        if state.time_remaining() <= 0:
            endings.clock_runs_out(state)
            state.game_over.set()
            return
        time.sleep(0.2)


def _await_ai(state, request, prefix=""):
    """Wait for ``request`` while keeping the clock visibly ticking.

    The watchdog thread is still running, so if the clock hits zero during
    this wait the round ends immediately. Otherwise, once the reply arrives we
    print it with the slow typewriter effect (which also locks input).
    """
    last_shown = None
    while request.pending:
        if state.game_over.is_set():
            return
        remaining = int(state.time_remaining())
        if remaining != last_shown:
            show_clock(state.time_remaining())
            last_shown = remaining
        request.poll()
        time.sleep(0.1)

    if state.game_over.is_set():
        return
    reply = request.result
    type_out(prefix + reply, color=Fore.YELLOW)


def play_one_round():
    """Runs a single round. Returns True if the player won."""
    state = GameState()
    state.start_clock()
    threading.Thread(target=countdown_watchdog, args=(state,), daemon=True).start()

    while not state.game_over.is_set():
        show_clock(state.time_remaining())
        print(HELP_TEXT)  # help is always shown, no need to ask for it
        # Live input: the countdown is redrawn on this line as you type, so
        # the clock is visible the whole time, not just after Enter.
        raw = live_input(Fore.GREEN + "> " + Style.RESET_ALL, state.time_remaining)
        if raw is None:
            endings.vanished_into_night(state)
            break
        command = raw.strip().lower()

        if actions.check_dev_override(state, command):
            break

        # Map either a number ("1") or the old word ("look") to a command.
        number = None
        if command.isdigit() and int(command) in COMMANDS:
            number = int(command)
        elif command in NAME_TO_NUMBER:
            number = NAME_TO_NUMBER[command]

        if number is not None:
            name, func = COMMANDS[number]
            if name == "quit":
                actions.quit_game(state)
                continue
            request = func(state)
            if isinstance(request, ai.AIRequest):
                prefix = (
                    f"{bandit_label(state.bandit_mood, state.strikes, state.strike_limit)}: "
                    if name == "negotiate"
                    else ""
                )
                _await_ai(state, request, prefix=prefix)
        else:
            type_out(
                f"'{raw}' does nothing. Type a number from the list above.",
                color=Fore.RED,
            )

    return state.won


def main():
    print_intro()
    while True:
        won = play_one_round()
        again = menu.choose(
            "Play again?", [("Yes", "yes"), ("No", "no")], default_index=1
        )
        if again != "yes":
            print(Fore.WHITE + "Thanks for playing!")
            break
        print()
