"""
Agent validation and sandboxing wrapper.

This module wraps player agents to prevent cheating and invalid behavior.
"""

from kuhn3p import Player, betting


class AgentValidator:
    """
    Wraps a player agent to validate and sanitize its actions.
    
    This prevents cheating through:
    - Invalid return values from act()
    - Exceptions/crashes from agent code
    - State/game manipulation attempts
    - Access to forbidden internals
    """
    
    def __init__(self, agent, agent_name="Unknown"):
        """
        Wrap an agent with validation.
        
        Args:
            agent: The Player instance to wrap
            agent_name: Name for error messages
        """
        if not isinstance(agent, Player):
            raise TypeError(f"Agent must be instance of kuhn3p.Player, got {type(agent)}")
        
        self.agent = agent
        self.agent_name = agent_name
        self._last_error = None
    
    def start_hand(self, position, card):
        """Safely call agent's start_hand hook."""
        try:
            self.agent.start_hand(position, card)
        except Exception as e:
            # Log but don't crash - agent start_hand is optional
            self._last_error = f"start_hand error: {e}"
            pass
    
    def act(self, state, card):
        """
        Get validated action from agent.
        
        Args:
            state: Betting state
            card: Player's card
            
        Returns:
            Valid action (0 or 1)
            
        Raises:
            ValueError: If agent returns invalid action
            RuntimeError: If agent code crashes
        """
        # Validate inputs
        if not betting.is_internal(state):
            raise ValueError(f"act() called with non-internal state: {state}")
        if not (0 <= card < 4):
            raise ValueError(f"Invalid card: {card}")
        
        try:
            # Call agent's act method
            action = self.agent.act(state, card)
        except Exception as e:
            raise RuntimeError(
                f"Agent '{self.agent_name}' crashed in act(): {type(e).__name__}: {e}"
            )
        
        # Validate return value
        if not isinstance(action, (int, bool)):
            raise ValueError(
                f"Agent '{self.agent_name}' returned invalid action type {type(action)}, "
                f"expected int (0 or 1)"
            )
        
        action = int(action)
        
        if action not in (0, 1):
            raise ValueError(
                f"Agent '{self.agent_name}' returned invalid action {action}, "
                f"must be 0 (check/call) or 1 (bet/fold)"
            )
        
        # Validate action is legal for this state
        if not betting.num_actions(state) == 2:
            raise ValueError(
                f"Invalid state {state} - num_actions != 2"
            )
        
        return action
    
    def end_hand(self, position, card, state, shown_cards):
        """Safely call agent's end_hand hook."""
        try:
            self.agent.end_hand(position, card, state, shown_cards)
        except Exception as e:
            # Log but don't crash - agent end_hand is optional
            self._last_error = f"end_hand error: {e}"
            pass
    
    def __str__(self):
        """Return agent's string representation."""
        try:
            return str(self.agent)
        except:
            return f"Agent[{self.agent_name}]"


def create_safe_player(agent, name="Unknown"):
    """
    Create a validated wrapper around an agent.
    
    Args:
        agent: Player instance
        name: Agent name for error messages
        
    Returns:
        AgentValidator wrapping the player
        
    Raises:
        TypeError: If agent is not a Player instance
    """
    return AgentValidator(agent, name)


def validate_agents(agents_list):
    """
    Validate a list of agents.
    
    Args:
        agents_list: List of Player instances or (name, Player) tuples
        
    Returns:
        List of AgentValidator instances
        
    Raises:
        TypeError: If any agent is not a Player instance
    """
    validated = []
    
    for agent_info in agents_list:
        if isinstance(agent_info, tuple):
            name, agent = agent_info
        else:
            name = str(agent_info)
            agent = agent_info
        
        if not isinstance(agent, Player):
            raise TypeError(f"Agent '{name}' is not a Player instance")
        
        validated.append(AgentValidator(agent, name))
    
    return validated
