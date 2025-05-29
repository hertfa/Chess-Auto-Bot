# Chess.com Live Chess Bot

This GUI tool connects to a Chess.com live game, displays the move list, runs Stockfish analysis in real time, and draws a suggestion arrow on the board.

# Features
- Live monitoring of Chess.com moves
- Stockfish integration:
- Max Time (s): Maximum Time Stockfish has to think of a move in seconds
- Max Depth: Maximum Depth Stockfish is allowed to go
- Threads: How much CPU-Threads Stockfish is allowed to use (the higher, the better the moves, duh)
- Hash (MB): How much RAM Memory Stockfish is allowed to use in MegaBytes
- Arrow overlay on the Chess.com board
# Setup
1. Clone the repo:
- "git clone https://github.com/your-username/chess-com-stockfish-helper.git"

- "cd chess-com-stockfish-helper"

2. Install dependencies:

- "pip install -r requirements.txt"

or

- "py -m pip install -r requirements.txt"

3. Run it:

- "main.py"

# Important:
- Download Chrome here: https://www.google.com/chrome/
- Download Stockfish here: https://stockfishchess.org/download/

# Future Plans:
- Lichess.org and other various Chess websites support
- Auto-move your pieces
- Opening Books
- Chess Variants such as 960
- syzygy End Game Tablebases

# Disclaimer
This tool is provided for educational purposes only. It was created to help chess players improve their understanding of game analysis and study common patterns. It is not affiliated with or endorsed by Chess.com. Use this software responsibly and at your own risk; the author is not liable for any damages or misuse resulting from its use.
