# Kuhn Poker 3-Player Tournament Framework

A Python framework for running 3-player Kuhn poker agent competitions.

**Original Author:** Kevin Waugh  
**Extended with Tournament Framework** for multi-agent competitions

## Overview

This package provides a complete framework for running competitive 3-player Kuhn poker tournaments where participants submit agents to compete with each other.

## Quick Navigation

- **Are you a competitor submitting an agent?**  
  → See [COMPETITORS.md](COMPETITORS.md)

- **Want detailed API documentation?**  
  → See [TOURNAMENT_GUIDE.md](TOURNAMENT_GUIDE.md)

- **Want to understand the framework?**  
  → Read below

## Example

### For Competitors
```python
from kuhn3p import Player, betting, deck

class MyAgent(Player):
    def act(self, state, card):
        if betting.can_bet(state):
            return betting.BET if card == deck.ACE else betting.CHECK
        else:
            return betting.CALL if card == deck.ACE else betting.FOLD
```

### For Tournament Organiser
```bash
python run_tournament.py run --agents-dir ./agents/ --hands 1000 --rounds 3 --seed 42
```

Results automatically show winner and detailed statistics.

## The Game: 3-Player Kuhn Poker

**Setup:**
- 4-card deck (Jack, Queen, King, Ace)
- 3 players, 1 card each dealt randomly
- Goal: Win the most chips

**Betting:**
- Round 1: Each player can bet or check (going around)
- Round 2: If bet, players can call or fold
- Winner: Highest card remaining, or last unfolded player

**Tournament:**
- All unique 3-player combinations play together
- Each match is multiple hands with rotating positions
- Scores sum to zero (zero-sum game)
- Higher score = better strategy

## Project Structure

```
kuhn3p/                          # Game framework
├── tournament.py                # Tournament classes
├── agents.py                    # Agent registry & discovery
├── betting.py, deck.py, dealer.py  # Game logic
├── players/
│   ├── Bluffer.py              # Example agents
│   └── Chump.py
└── __init__.py

run_tournament.py               # CLI for running tournaments
tournament_example.py           # Usage examples
AGENT_TEMPLATE.py               # Template for competitors

Documentation:
├── README.md                   # This file (overview)
├── COMPETITORS.md              # Guide for competitors
└── TOURNAMENT_GUIDE.md         # Full API reference
```
## Running Examples

Test the framework works:

```bash
python tournament_example.py
```

This runs 3 complete examples with built-in agents.

## Game Rules: 3-Player Kuhn Poker

3-player Kuhn poker is a simplified betting game:

- **Deck**: 4 cards (Jack < Queen < King < Ace)
- **Deal**: Each player gets 1 unique random card
- **Round 1 Betting**: Each player can bet or check
- **Round 2 Betting**: If bet, players can call or fold
- **Showdown**: Highest remaining card wins the pot
- **Zero-Sum**: Total winnings always sum to 0

## Requirements

- Python 3.6+
- No external dependencies (uses only Python stdlib)

## Original Work

The core Kuhn poker implementation is based on code from the 2014 APAC 3-Player Kuhn Poker Competition. See [archived/README.md](archived/README.md) for history.

**Original Framework Author:** Kevin Waugh (kevin.waugh@gmail.com)

## References

- [3-player Kuhn poker project](https://medium.com/ganzfried-gleans/3-player-kuhn-poker-project-ce1b818b4d5e) 

- [A Parameterized Family of Equilibrium Profiles for
Three-Player Kuhn Poker](https://poker.cs.ualberta.ca/publications/AAMAS13-3pkuhn.pdf) 

## License

See LICENSE file.
