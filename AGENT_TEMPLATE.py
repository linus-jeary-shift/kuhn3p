"""
Template for creating a custom Kuhn poker player agent.

Instructions for competitors:
1. Copy this file and rename it to your agent's name (e.g., MyAgent.py)
2. Modify the class name and implementation
3. Place it in the agents/ directory
4. Submit it for the tournament

The framework will automatically discover and load your agent.
"""

from kuhn3p import Player
from kuhn3p import betting, deck
import random


class TemplateAgent(Player):
    """
    A template agent for the Kuhn poker tournament.
    
    Your agent must:
    - Inherit from kuhn3p.Player
    - Implement the act() method
    - Optionally implement start_hand() and end_hand() for state tracking
    
    IMPORTANT: Safeguards Against Cheating
    ======================================
    The tournament framework includes anti-cheating mechanisms:
    
    1. Return Value Validation:
       - act() MUST return an integer 0 or 1
       - Returning anything else (99, "bet", None, etc) causes you to LOSE that hand
       - Boolean True/False are accepted and converted to 1/0
    
    2. Exception Handling:
       - If your code raises an exception in act() you LOSE that hand
       - If your code raises an exception in start_hand() or end_hand(), 
         the error is logged but doesn't affect the hand
    
    3. Action Validation:
       - Returned action must be valid for the current state
       - Invalid actions cause hand loss
    
    You cannot:
    - Access the betting state's internal structure
    - Modify the game state
    - Return values other than 0 or 1
    - Call methods other than the ones explicitly provided
    """
    
    def __init__(self, name="TemplateAgent", rng=None):
        """
        Initialize your agent.
        
        Args:
            name: Display name for your agent
            rng: Random number generator (optional)
        """
        self.name = name
        self.rng = rng if rng is not None else random.Random()
        
        # You can add any state tracking here
        self.hand_count = 0
        self.total_score = 0
    
    def start_hand(self, position, card):
        """
        Called at the start of each hand.
        
        Args:
            position: Your position (0, 1, or 2)
            card: Your card (deck.JACK=0, deck.QUEEN=1, deck.KING=2, deck.ACE=3)
        """
        self.hand_count += 1
        # You can use this to track hand information
    
    def act(self, state, card):
        """
        Make a decision on your turn.
        
        Args:
            state: Current betting state (integer from 0-24)
            card: Your card (0=Jack, 1=Queen, 2=King, 3=Ace)
        
        Returns:
            Action: betting.BET or betting.CHECK if you can bet
                   betting.CALL or betting.FOLD if facing a bet
        
        Useful functions:
            - betting.can_bet(state): True if you can bet/check
            - betting.can_call(state): True if you can call/fold
            - betting.facing_bet(state): True if you're facing a bet
            - betting.actor(state): Current actor's position
            - betting.to_decision(state): Decision number (0-3)
        
        Card values:
            - deck.JACK = 0 (lowest)
            - deck.QUEEN = 1
            - deck.KING = 2
            - deck.ACE = 3 (highest)
        """
        
        # SIMPLE EXAMPLE: Bet/Call with Ace, otherwise Check/Fold
        if betting.can_bet(state):
            # We can bet or check
            if card == deck.ACE:
                return betting.BET
            else:
                return betting.CHECK
        else:
            # We must call or fold
            if card == deck.ACE:
                return betting.CALL
            else:
                return betting.FOLD
    
    def end_hand(self, position, card, state, shown_cards):
        """
        Called at the end of each hand.
        
        Args:
            position: Your position
            card: Your card
            state: Final betting state
            shown_cards: List of shown cards (or None if folded before showdown)
                        shown_cards[i] is your opponent's card if shown, None otherwise
        """
        # You can use this for updating statistics or learning
        pass
    
    def __str__(self):
        return f"{self.name}(hands={self.hand_count})"


class SmartAgent(Player):
    """
    A slightly more sophisticated example using card strength and position.
    """
    
    def __init__(self, aggression=0.5, rng=None):
        """
        Args:
            aggression: How likely to bet/call (0.0 to 1.0)
        """
        self.aggression = aggression
        self.rng = rng if rng is not None else random.Random()
    
    def act(self, state, card):
        """Make decisions based on card strength and position."""
        
        # Calculate basic card strength (0 to 1)
        card_strength = card / float(deck.ACE)
        
        if betting.can_bet(state):
            # Decide whether to bet
            # More likely to bet with strong cards or if aggressive
            if card_strength > 0.5 or self.rng.random() < (self.aggression * 0.2):
                return betting.BET
            else:
                return betting.CHECK
        else:
            # Decide whether to call
            # More likely to call with strong cards or if aggressive
            call_threshold = 0.5 - (self.aggression * 0.3)
            if card_strength > call_threshold:
                return betting.CALL
            else:
                return betting.FOLD
    
    def __str__(self):
        return f"SmartAgent(aggression={self.aggression})"


if __name__ == "__main__":
    # Test your agent
    from kuhn3p.tournament import TournamentMatch
    from kuhn3p.players import Chump
    
    my_agent = TemplateAgent()
    opponent1 = Chump(0.5, 0.5, 0.5)
    opponent2 = Chump(0.99, 0.01, 0.0)
    
    result = TournamentMatch.run(my_agent, opponent1, opponent2, hands=100)
    print(f"Test match result: {result['scores']}")
    print(f"Your agent won: {result['winner'] == 0}")
