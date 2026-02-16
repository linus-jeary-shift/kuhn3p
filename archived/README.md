# Archived Files

This directory contains files from the original 2014 APAC Kuhn Poker competition that are not needed for running local tournaments.

## Files

### `connect_to_dealer.py`
- **Purpose**: Connects to the official APAC tournament dealer server
- **Status**: Not needed for local tournaments
- **When to use**: Only if running against official APAC dealer infrastructure
- **Notes**: Implements ACPC (Annual Computer Poker Competition) dealer protocol

### `run_match.py`
- **Purpose**: Simple example of running a single 3000-hand match
- **Status**: Replaced by `tournament_example.py` and `run_tournament.py`
- **When to use**: Reference only - for understanding the basic API
- **Replacement**: Use `tournament_example.py` for examples or `run_tournament.py` for actual tournaments

## Local Tournament Setup

For running 3-player Kuhn poker tournaments locally:

1. **Simple examples**: See `tournament_example.py`
2. **CLI tournaments**: Use `run_tournament.py`
3. **Custom tournaments**: Use the `Tournament` class from `kuhn3p/tournament.py`

See [../TOURNAMENT_GUIDE.md](../TOURNAMENT_GUIDE.md) for detailed documentation.
