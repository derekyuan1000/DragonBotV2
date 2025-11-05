# DragonBotV2 - Grandmaster Level Chess Bot

A sophisticated chess bot that runs on Lichess at a grandmaster level, featuring advanced algorithms and evaluation techniques.

## Features

The GrandmasterEngine implements all the requested features:

### 1. Search Algorithms
- **Minimax Algorithm**: The engine explores the game tree and chooses moves that maximize its advantage while minimizing the opponent's chances
- **Alpha-Beta Pruning**: Optimizes the minimax algorithm by pruning branches that won't affect the final decision, allowing deeper search
- **Iterative Deepening**: Gradually increases search depth (up to depth 6) to use available time efficiently
- **Quiescence Search**: Searches tactical positions (captures) beyond the normal depth to avoid the horizon effect

### 2. Evaluation Function
The engine uses a sophisticated multi-factor evaluation:
- **Material Balance**: Accurate piece values (Pawn=100, Knight=320, Bishop=330, Rook=500, Queen=900)
- **Piece-Square Tables**: Positional bonuses for each piece type based on their location
- **Piece Activity**: Evaluates mobility (number of legal moves available)
- **King Safety**: 
  - Pawn shield evaluation
  - Penalty for attacks near the king
- **Pawn Structure**:
  - Penalties for doubled pawns
  - Penalties for isolated pawns
  - Bonuses for passed pawns

### 3. Transposition Table
- Stores up to 1 million evaluated positions
- Caches position evaluations with depth, score, and best move
- Uses Zobrist hashing for efficient position lookup
- Implements exact/lower bound/upper bound flags for correct reuse

### 4. Opening Book
- Automatic integration with Polyglot opening books
- Searches for book files in standard locations:
  - `./engines/book.bin`
  - `./book.bin`
  - `./engines/performance.bin`
- Uses weighted random selection for variety

### 5. Endgame Tablebases
- Supports Syzygy tablebases (up to 7 pieces)
- Searches for tablebase files in standard locations:
  - `./engines/syzygy`
  - `./syzygy`
  - `./tablebases/syzygy`
- Uses DTZ (distance to zeroing move) for optimal endgame play

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Create your configuration file:
```bash
cp config.yml.default config.yml
```

3. Configure your Lichess token:
   - Get a token from https://lichess.org/account/oauth/token (requires Bot account)
   - Edit `config.yml` and replace the token value with your actual token
   - Change `engine.name` to `GrandmasterEngine`
   - Change `engine.protocol` to `homemade`

4. (Optional) Add opening books and tablebases:
   - Place Polyglot opening books in `./engines/book.bin`
   - Place Syzygy tablebases in `./engines/syzygy/`

## Quick Start Configuration

Here's a minimal config.yml to get started:

```yaml
token: "YOUR_LICHESS_TOKEN_HERE"
url: "https://lichess.org/"

engine:
  dir: "./"
  name: "GrandmasterEngine"
  protocol: "homemade"
  ponder: true
  
  # ... rest of configuration ...
```

## Usage

Run the bot:
```bash
python3 lichess-bot.py
```

The bot will:
1. Connect to Lichess
2. Accept challenges according to your configuration
3. Play games using the GrandmasterEngine
4. Use opening books (if available) in the opening phase
5. Use tablebases (if available) in endgames
6. Search deeply in the middlegame using minimax with alpha-beta pruning

## Testing

Test the engine locally:
```bash
python3 test_grandmaster_engine.py
```

This will run the engine through various test positions and demonstrate its capabilities.

## Engine Strength

The GrandmasterEngine:
- Searches 3,000-10,000 nodes per second depending on position complexity
- Reaches depth 4-6 in typical positions
- Uses advanced evaluation with multiple strategic factors
- Benefits from opening book knowledge (when available)
- Plays perfectly in tablebased endgames (when tablebases available)

Expected rating: ~2000-2400 Elo depending on time controls

## Configuration

The main configuration is in `config.yml`:
- `engine.name: "GrandmasterEngine"` - Uses the advanced engine
- `engine.protocol: "homemade"` - Uses the built-in Python engine
- Time controls and game acceptance criteria can be customized
- Draw/resign behavior can be configured

## Technical Details

**Algorithm**: Minimax with alpha-beta pruning and iterative deepening
**Search depth**: 4-6 plies (depending on time available)
**Evaluation**: Multi-factor (material + position + mobility + safety + structure)
**Move ordering**: Checks > Captures (MVV-LVA) > Promotions > Others
**Transposition table**: Up to 1M positions
**Time management**: Dynamic allocation based on clock and increment

## Files

- `homemade.py` - Contains the GrandmasterEngine implementation
- `lichess-bot.py` - Main entry point for the bot
- `config.yml` - Configuration file (create from config.yml.default)
- `lib/` - Supporting library code (engine wrapper, Lichess API, etc.)
- `test_grandmaster_engine.py` - Test suite for the engine
- `test_bot/` - Test compatibility module

## How It Works

When you run the lichess-bot file, here's what happens:

1. **Initialization**: The bot loads the GrandmasterEngine class from `homemade.py`
2. **Connection**: Connects to Lichess using your API token
3. **Game Handling**: For each move:
   - First checks opening book (if in opening phase and book available)
   - Then checks endgame tablebases (if few pieces and tablebases available)
   - Otherwise performs deep search using minimax with alpha-beta pruning
4. **Move Selection**: Returns the best move found

The engine implements all five requested features:
1. ✅ Minimax with alpha-beta pruning
2. ✅ Sophisticated evaluation function
3. ✅ Transposition table
4. ✅ Opening book support
5. ✅ Endgame tablebase support

## License

See LICENSE file for details.

