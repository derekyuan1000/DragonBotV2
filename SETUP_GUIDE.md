# Setup and Usage Guide

This guide will help you set up and run the DragonBotV2 grandmaster-level chess bot.

## Prerequisites

- Python 3.7 or higher
- A Lichess account upgraded to Bot account (see below)
- Internet connection

## Step-by-Step Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `chess` - Python chess library
- `PyYAML` - YAML configuration parser
- `requests` - HTTP library for Lichess API
- `backoff` - Retry logic
- `rich` - Beautiful terminal output

### 2. Upgrade Your Lichess Account to Bot Account

**IMPORTANT**: Regular Lichess accounts cannot be used for bots. You need to upgrade.

1. Go to https://lichess.org/account/oauth/token/create
2. Create a new token with the scopes:
   - `Play games with the bot API`
   - (Optional) `Read incoming challenges`
3. Copy the generated token (you'll need it in step 3)
4. Go to https://lichess.org/api#operation/botAccountUpgrade
5. Click "Try it out"
6. Paste your token in the Authorization field as: `Bearer YOUR_TOKEN_HERE`
7. Click "Execute" to upgrade your account to a bot account

**Note**: Once you upgrade to a bot account, you can't play games manually on the website anymore. Only bots can use this account.

### 3. Configure the Bot

Create your configuration file:

```bash
cp config.yml.default config.yml
```

Edit `config.yml` and make these changes:

1. **Add your token**:
```yaml
token: "lip_YOUR_ACTUAL_TOKEN_HERE"
```

2. **Set the engine**:
```yaml
engine:
  dir: "./"
  name: "GrandmasterEngine"
  protocol: "homemade"
  ponder: true
```

3. **(Optional) Adjust challenge settings**:
```yaml
challenge:
  concurrency: 1              # Number of simultaneous games
  accept_bot: true            # Accept challenges from bots
  variants:
    - standard               # Only play standard chess
  time_controls:
    - bullet
    - blitz
    - rapid
    - classical
```

### 4. Run the Bot

```bash
python3 lichess-bot.py
```

You should see:
```
.   _/|
.  // o\
.  || ._)  lichess-bot 2025.10.31.1
.  //__\
.  )___(   Play on Lichess with a bot

INFO     Checking engine configuration ...
INFO     Engine configuration OK
```

The bot is now running and waiting for challenges!

## Playing Games

### Accepting Challenges

The bot will automatically accept challenges based on your `config.yml` settings.

To challenge your bot:
1. Go to https://lichess.org/@/YOUR_BOT_USERNAME
2. Click "Challenge to a game"
3. Choose your time control and variant
4. The bot will accept and play

### Manual Challenges

You can also have the bot challenge other bots by enabling matchmaking:

```yaml
matchmaking:
  allow_matchmaking: true
  challenge_timeout: 30      # Challenge after 30 minutes of idle
```

## Testing the Engine

Before connecting to Lichess, test the engine locally:

```bash
python3 test_grandmaster_engine.py
```

This runs the engine through several test positions and shows:
- Search depth achieved
- Nodes searched
- Evaluation scores
- Best moves found

## Advanced Configuration

### Opening Books (Optional)

To add opening book knowledge:

1. Download a Polyglot opening book (`.bin` format)
2. Place it at `./engines/book.bin`
3. The engine will automatically detect and use it

Popular books:
- [Performance book](http://www.talkchess.com/forum3/viewtopic.php?t=48603)
- [Cerebellum book](https://github.com/sshivaji/cerebellum-polyglot)

### Endgame Tablebases (Optional)

To add perfect endgame play:

1. Download Syzygy tablebases from https://syzygy-tables.info/
2. Extract to `./engines/syzygy/`
3. The engine will automatically detect and use them

Recommended: Start with 3-4-5 piece tablebases (~1GB)

### Performance Tuning

Adjust these settings in `config.yml`:

```yaml
move_overhead: 2000          # Increase if flagging
abort_time: 30               # Time before aborting inactive games
```

For faster games (bullet):
```yaml
challenge:
  bullet_requires_increment: true  # Safer for bullet
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'chess'"

Run: `pip install -r requirements.txt`

### "Authentication failed"

- Check your token in `config.yml`
- Make sure your account is upgraded to a Bot account
- Regenerate your token at https://lichess.org/account/oauth/token

### "Engine configuration error"

Make sure `config.yml` has:
```yaml
engine:
  name: "GrandmasterEngine"
  protocol: "homemade"
```

### Bot doesn't accept challenges

Check your challenge settings in `config.yml`:
- `accept_bot: true` to accept bot challenges
- Appropriate `time_controls` and `variants`
- `concurrency: 1` or higher

### Bot plays too slowly

The engine searches 4-6 moves deep. This is normal. To play faster:
- Use faster time controls (bullet/blitz)
- Reduce search depth (requires code modification)

### Bot plays too quickly (flags in long games)

Increase time management margins:
```yaml
move_overhead: 3000  # Give more safety margin
```

## How to Stop the Bot

Press `Ctrl+C` to stop the bot. It will finish current games before shutting down if:
```yaml
quit_after_all_games_finish: true
```

Otherwise it stops immediately.

## Engine Behavior

### Opening Phase (moves 1-20)
- Uses opening book if available
- Falls back to search if no book move

### Middlegame (moves 20-40)
- Full minimax search with alpha-beta pruning
- Evaluates material, position, king safety, pawn structure
- Searches 4-6 moves deep

### Endgame (≤7 pieces)
- Uses Syzygy tablebases if available
- Otherwise continues with regular search
- Strong endgame evaluation

## Expected Performance

- **Rating**: ~2000-2400 Elo
- **Nodes/sec**: 3,000-10,000
- **Search depth**: 4-6 plies
- **Time per move**: 0.5-5 seconds (depending on time control)

## Support

For issues or questions:
1. Check this guide first
2. Review the README.md
3. Check Lichess bot API docs: https://lichess.org/api#tag/Bot
4. Review the code in `homemade.py` for engine details

## Example Session

```bash
$ python3 lichess-bot.py
[INFO] Checking engine configuration ...
[INFO] Engine configuration OK
[INFO] Found opening book: ./engines/book.bin
[INFO] Handling challenges and games ...
```

When a challenge arrives:
```bash
[INFO] Challenge from opponent123: 5+3 blitz
[INFO] Accepting challenge...
[INFO] Game started: https://lichess.org/abc123
[INFO] Move 1: e2e4 (from opening book)
[INFO] Move 5: Nf3 (search depth=4, nodes=5234, score=+0.15)
```

Game end:
```bash
[INFO] Game finished: You won by checkmate
[INFO] Waiting for challenges...
```
