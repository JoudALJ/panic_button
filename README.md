##PANIC_BUTTON
#Overview
Panic Button is a short, silly, interactive command-line game. You play a rookie negotiator sent to stop a bandit who is holding a hostage next to a rigged bomb, with a countdown clock running the whole time. Every choice you make leads to its own distinct (and pretty silly) ending.

#Features & User Stories
- See a live countdown timer running the whole round.
- See the full list of available commands shown every turn.
- Look around the room for a quick description of the scene.
- Check inventory.
- Try to cut a wire on the bomb.
- Try to physically stop the kidnapper.
- Negotiate with the kidnapper and get a different reply each time.
- Call for backup over the radio.
- Wait and let time pass.
- Quit the round early.
- Get asked to play again immediately after any ending, without restarting the program.

#Usage:
- type in look to look around the room.
- type in inventory to see what you're carrying.
- type in cut wire to attempt to defuse the bomb (you'll then pick a wire).
- type in stab kidnapper to attempt to physically stop the kidnapper.
- type in negotiate to try talking the kidnapper down.
- type in call backup to radio for help.
- type in wait to let time pass.
- type in quit to give up on the round early.
- and so on...
Most choices are chosen as as a numbered list — just type the number of the option you want.

#Optional: enable AI bandit replies (Ollama)
The game works fine without this — negotiate just uses a canned line. To get live AI-generated replies instead:
- Install Ollama: https://ollama.com/download
- Start the Ollama server: ollama serve (leave it running in a terminal)
- Pull a model once, ahead of time (do this before any live demo, the first pull can take a few minutes): ollama pull llama3.2
- Make sure the ollama Python package is installed: pip install ollama (already in requirements.txt)
- Run the game as normal: python main.py, then try negotiate
If Ollama isn't running or isn't installed, the game catches the error and silently falls back to a canned line instead of crashing.

#Some technologies used are:
Python 3, colorama, ollama (optional).

#Project structure
main.py               # entry point
game/
  constants.py        # settings (time limit, inventory, etc.)
  state.py             # GameState class (clock, inventory, game-over flag)
  display.py           # banners, colors, timer display
  menu.py               # numbered pick-a-number menus
  actions.py            # player commands
  ai.py                  # optional Ollama-powered bandit replies
  endings.py            # every ending screen
  game.py               # main loop + countdown watchdog
  
#Install & run
python -m venv venv
source venv/bin/activate      # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python main.py
NOTE: before submitting the final project, run:
pip freeze > requirements.txt to record the exact package versions used.
