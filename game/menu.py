"""A simple numbered menu: print the options, type the number to pick one.
No arrow keys, no extra libraries -- works the same in every terminal,
which matters for a live/projected demo.
"""

from colorama import Fore, Style
from .display import type_out

def choose(prompt_text, options, default_index=0):
    """options: list of (label, value) pairs. Returns the chosen value.
    Pressing Enter with nothing typed picks options[default_index]."""
    type_out(prompt_text, color=Fore.CYAN)
    for i, (label, _value) in enumerate(options, start=1):
        marker = "  <- default (press Enter)" if i - 1 == default_index else ""
        type_out(f"  {i}) {label}{marker}", color=Fore.CYAN)
    while True:
        try:
            raw = input(Fore.CYAN + "> " + Style.RESET_ALL).strip()
        except (EOFError, KeyboardInterrupt):
            return options[default_index][1]
        if raw == "":
            return options[default_index][1]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][1]
        print(Fore.RED + "Please enter a valid number.")
