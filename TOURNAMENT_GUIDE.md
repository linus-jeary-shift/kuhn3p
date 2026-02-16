# Kuhn Poker Tournament Framework

This guide explains how to use the tournament framework to run 3-player Kuhn poker competitions with multiple agents.

## Quick Start

Run an example tournament:
```bash
python tournament_example.py
```

## Components

### Core Classes

#### `Match`
Represents a single match between 3 players over multiple hands.

```python
from kuhn3p import players, tournament

player1 = players.Bluffer(0.2)
player2 = players.Chump(0.99, 0.01, 0.0)
player3 = players.Chump(0.5, 0.5, 0.5)

match = tournament.Match([player1, player2, player3], num_hands=1000)
scores = match.play()
print(f"Final scores: {scores}")
```

#### `Tournament`
Manages round-robin tournaments where all unique combinations of 3 agents play together.

```python
from kuhn3p import tournament, agents

registry = agents.get_registry()

agent_list = [
    ('Bluffer', registry.create('Bluffer')),
    ('Chump_passive', registry.create('Chump_passive')),
    ('Chump_aggressive', registry.create('Chump_aggressive')),
]

t = tournament.Tournament(agent_list)
results = t.run_round_robin(hands_per_matchup=500, num_rounds=2)
t.print_results()
```

#### `TournamentMatch`
Convenience class for running a single match with simplified interface.

```python
from kuhn3p import tournament

result = tournament.TournamentMatch.run(player1, player2, player3, hands=1000)
print(f"Winner: Player {result['winner']}")
print(f"Scores: {result['scores']}")
```

### Agent Management

#### Using the Registry

The framework includes an agent registry for registering and managing agents:

```python
from kuhn3p import agents

registry = agents.get_registry()

# List available agents
print(registry.list_agents())

# Get info about an agent
info = registry.get_info('Bluffer')

# Create an agent instance
agent = registry.create('Bluffer')

# Register a custom agent
from kuhn3p import players
registry.register('MyCustomBluffer', players.Bluffer, bluff=0.3)
```

Pre-registered agents:
- `Bluffer` - Bluffs 20% of the time
- `Bluffer_aggressive` - Bluffs 50% of the time
- `Bluffer_conservative` - Bluffs 10% of the time
- `Chump_passive` - Calls rarely (1%), folds never
- `Chump_aggressive` - Calls 80% of the time
- `Chump_balanced` - Equal probabilities

## Creating Custom Agents

All agents must inherit from `kuhn3p.Player`:

```python
from kuhn3p import Player
from kuhn3p import betting, deck

class MyAgent(Player):
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
    
    def act(self, state, card):
        """Return action: betting.BET (1) or betting.CHECK/CALL/FOLD (0)."""
        if betting.can_bet(state):
            if card == deck.ACE:
                return betting.BET
            else:
                return betting.CHECK
        else:
            if card == deck.ACE:
                return betting.CALL
            else:
                return betting.FOLD
    
    def start_hand(self, position, card):
        """Called at the start of each hand."""
        pass
    
    def end_hand(self, position, card, state, shown_cards):
        """Called at the end of each hand for bookkeeping."""
        pass
    
    def __str__(self):
        return f'MyAgent(p1={self.param1}, p2={self.param2})'
```

Register your agent:
```python
from kuhn3p import agents

agents.register_agent('MyAgent', MyAgent, param1=0.5, param2=0.3)
```

## Tournament Modes

### Round-Robin Tournament

Every unique combination of 3 agents plays together:

```python
t = tournament.Tournament(agents_list)
t.run_round_robin(
    hands_per_matchup=1000,  # Hands per match
    num_rounds=3,             # Repeat each matchup 3 times
    seed=42,                  # Random seed for reproducibility
    verbose=True
)
```

For N agents, this runs:
- C(N, 3) unique matchups (combinations of 3)
- Each matchup played num_rounds times
- Total matches = C(N, 3) × num_rounds

### Single Match

```python
result = tournament.TournamentMatch.run(
    player1, player2, player3,
    hands=1000,
    seed=None
)

print(f"Scores: {result['scores']}")
print(f"Winner: {result['winner']}")
```

## Results and Rankings

After running a tournament, view results:

```python
# Print formatted results
t.print_results(sort_by='total_score')

# Get rankings as a list
rankings = t.get_rankings(sort_by='total_score')
for rank, (name, stats) in enumerate(rankings, 1):
    print(f"{rank}. {name}: {stats['total_score']} points")

# Access raw results
results = t.results  # Dict indexed by agent index
matchups = t.matchups  # Dict of all match results
```

Result statistics:
- `total_score` - Sum of payoffs across all matches
- `matches_played` - Number of matches agent participated in
- `num_first_places` - Matches won
- `num_second_places` - Matches tied for second
- `num_third_places` - Matches lost

## Advanced Usage

### Loading Agents from Directory

```python
from kuhn3p.agents import load_agents_from_directory

agents_dict = load_agents_from_directory('./my_agents/')
# agents_dict = {'AgentName': AgentClass, ...}
```

### Setting Random Seeds

For reproducibility, use the `seed` parameter:

```python
# Tournament
t.run_round_robin(..., seed=12345)

# Match
match = tournament.Match(players, num_hands=1000, rng=12345)
scores = match.play()
```

### Collecting Match Details

```python
match = tournament.Match(players, num_hands=1000)
scores = match.play()

# Access match data
print(match.scores)  # [score_p1, score_p2, score_p3]
print(match.num_hands)
print(match.rng.random())  # Check RNG state
```

## Common Patterns

### Run tournament with all default agents

```python
from kuhn3p import agents
from kuhn3p.tournament import Tournament

registry = agents.get_registry()
agent_names = registry.list_agents()

tournament_agents = [
    (name, registry.create(name))
    for name in agent_names
]

t = Tournament(tournament_agents)
t.run_round_robin(hands_per_matchup=1000, num_rounds=1, seed=42)
t.print_results()
```

### Run head-to-head with fixed third player

```python
from kuhn3p.tournament import Match

baseline = players.Chump(0.5, 0.5, 0.5)

for bluff_rate in [0.1, 0.2, 0.3, 0.4, 0.5]:
    agent = players.Bluffer(bluff_rate)
    match = Match([agent, baseline, baseline], num_hands=5000)
    scores = match.play()
    print(f"Bluff={bluff_rate}: {scores[0]}/{sum(abs(s) for s in scores)}")
```

## Notes

- Matches are played with button rotation by default (dealer changes each hand)
- All Kuhn poker hands use standard deck: Jack, Queen, King, Ace
- Betting is simplified: players can only check/bet in first decision, call/fold in response
- Player order affects results due to positional advantage - tournaments account for this through rotation
- Agents should be deterministic or properly seed their RNGs for reproducible results

## API Reference

See code docstrings in `kuhn3p/tournament.py` and `kuhn3p/agents.py` for complete API documentation.
