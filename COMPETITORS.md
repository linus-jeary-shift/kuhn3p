# For Competitors: How to Submit Your Agent

Welcome to the 3-Player Kuhn Poker Tournament! This guide explains how to create and submit your agent.

## Quick Start

1. **Copy the template:**
   ```bash
   cp AGENT_TEMPLATE.py {FirstName}{LastName}Agent.py
   ```

2. **Implement your strategy** in the `act()` method:
   ```python
   def act(self, state, card):
       if betting.can_bet(state):
           # You can bet or check
           if card == deck.ACE:
               return betting.BET
           else:
               return betting.CHECK
       else:
           # You must call or fold
           if card == deck.ACE:
               return betting.CALL
           else:
               return betting.FOLD
   ```

3. **Test locally:**
   ```bash
   python {FirstName}{LastName}Agent.py
   ```

4. **Submit** your `.py` file

## Understanding the Game

### Card Values
- **Jack (0)** - Lowest
- **Queen (1)**
- **King (2)**  
- **Ace (3)** - Highest

You'll be dealt one unique card at random. Your goal is to maximize your winnings against the other two players.

### Betting Basics

Each hand has two betting decision points:

**First Decision (everyone got their card)**
- You can **BET** or **CHECK**

**If someone bets, second decision (if you didn't fold)**
- You can **CALL** or **FOLD**

The pot goes to the highest card if everyone checks/calls, or to the last remaining player if others fold.

## The `act()` Method

This is where your strategy lives. You get two pieces of information:

```python
def act(self, state, card):
    # state: Current betting situation (tells you the action history)
    # card: Your card (0=Jack, 1=Queen, 2=King, 3=Ace)
    
    # Return your action
    return betting.BET, betting.CHECK, betting.CALL, or betting.FOLD
```

### Useful Helper Functions

```python
# Check what decision you're making
betting.can_bet(state)      # True if you're choosing bet/check
betting.can_call(state)     # True if you're choosing call/fold
betting.facing_bet(state)   # True if someone bet before you

# Get information about the state
betting.actor(state)        # Which player is acting (0, 1, or 2)
betting.to_decision(state)  # Which betting round (0-3)
```

See [TOURNAMENT_GUIDE.md](TOURNAMENT_GUIDE.md) for advanced details.

## Optional: Learning from Hands

You can track information about hands to improve your strategy:

```python
def start_hand(self, position, card):
    """Called at the start of each hand"""
    self.hands_played += 1
    self.my_card = card

def end_hand(self, position, card, state, shown_cards):
    """Called at the end - you can see revealed opponent cards"""
    if shown_cards[0] is not None:  # Opponent 1 showed their card
        self.opponent_cards.append(shown_cards[0])
```

## Testing Before Submission

Use the test code originating in `AGENT_TEMPLATE.py`:

```bash
python {FirstName}{LastName}Agent.py
```

Or test against specific agents:

```python
from kuhn3p.tournament import TournamentMatch
from kuhn3p.players import Bluffer, Chump

my_agent = {FirstName}{LastName}Agent()
result = TournamentMatch.run(
    my_agent,
    Bluffer(0.2),
    Chump(0.5, 0.5, 0.5),
    hands=1000
)
print(f"Your score: {result['scores'][0]}")
```

## Example Strategies

### 1. Simple (from template)
- Bet/call with Ace
- Check/fold with everything else

### 2. Card-Based
- Bet/call if card > Queen
- Check/fold if card <= Queen

### 3. Aggressive
- Bet/call more often
- Risk more for bigger wins

### 4. Defensive
- Fold when facing bets
- Check safe hands

### 5. Learning
- Track opponent cards across hands
- Adapt decisions based on history

### 6. Game theoretic
- Agent adopts a Nash equilibrium strategy.
- See the references section in [README.md](README.md) for more details.

## Submission Details

- Your agent class inherits from `kuhn3p.Player`
- You implemented the `act()` method
- It returns valid actions (0 or 1)
- `python {FirstName}{LastName}Agent.py` runs without errors
- File is saved as `{FirstName}{LastName}Agent.py` (or your chosen name)
- No external dependencies beyond Python stdlib
- Send to me on Slack DMs by 

## Anti-Cheating Rules & Validation

The tournament framework includes automatic validation to ensure fair play:

### Action Validation
Your `act()` method **must return 0 or 1** (integer):
- `0` = Check or Fold (depending on context)
- `1` = Bet or Call (depending on context)

**Invalid returns will cause you to lose that hand:**
- Returning `99`, `"bet"`, `None`, `True/False` as-is, or any other value
- Returning a float like `1.0` instead of integer `1`

**Valid:** Boolean `True`/`False` are automatically converted to `1`/`0`

### Exception Safety
If your `act()` method raises an exception:
- That hand is forfeited (you lose)
- The tournament continues
- The error is logged

Example of hand loss:
```python
def act(self, state, card):
    pot = betting.pot_size(state)  # This works
    return card / 0  # ERROR! Zero division - hand lost
```

### Sandboxing
You can only safely call:
- Methods from the `betting` module (can_bet, can_call, etc)
- Methods from the `deck` module
- Your own methods

You cannot:
- Access internal state structure
- Modify the game in any way
- Call private methods
- Import and use external packages (except stdlib)

### Summary
```python
def act(self, state, card):
    # GOOD: Return 0 or 1
    if card >= 2:
        return 1  # Bet/Call
    else:
        return 0  # Check/Fold
    
    # BAD: Return anything else (hand lost)
    # return "bet"  # String
    # return None   # None value
    # return card   # Returns 0-3, invalid!
    
    # BAD: Raise exception (hand lost)
    # return 1 / 0  # ZeroDivisionError
    # return self.nonexistent_method()  # AttributeError
```

## Tournament Format

- **Players per match:** 3
- **Hands per match:** 1,000,000
- **Tournament:** Round-robin (every unique 3-player combo plays together)
- **Ranking:** Total score across all matches


Your position changes each hand to balance advantages. Higher scores = better strategy!

## Submission details

Send your `{FirstName}{LastName}Agent.py` to me on Slack DMs by `31/03/2026` to guarantee your entry to the tournament.

You can also rename your agent file to something witty or clever, but it should ideally be unique.

## Questions?

See [TOURNAMENT_GUIDE.md](TOURNAMENT_GUIDE.md) for detailed API documentation or ask me in **#uk-ds-poker-challenge**.

Good luck! 🎰
