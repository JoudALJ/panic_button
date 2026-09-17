"""Holds all mutable game state in one place."""

import time
import threading

from .constants import TIME_LIMIT_SECONDS, STARTING_INVENTORY
from .ai import DEFAULT_MOOD, STRIKES_TO_SHOOT
class GameState:
    def __init__(self):
        self.time_limit = TIME_LIMIT_SECONDS
        self.start_time = None
        self.game_over = threading.Event()
        self.inventory = list(STARTING_INVENTORY)
        self.won = False
        # The villain's current mood, shown beside his name: "Bandit [bored]:".
        # Updated as the negotiation verdicts come in.
        self.bandit_mood = DEFAULT_MOOD
        # Positive values are visible strikes; negative values track hidden
        # over-happiness until the happy ending threshold is reached.
        self.strikes = 0
        self.strike_limit = STRIKES_TO_SHOOT

    def start_clock(self):
        self.start_time = time.time()

    def time_remaining(self):
        elapsed = time.time() - self.start_time
        return max(0, self.time_limit - elapsed)
