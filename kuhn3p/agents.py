"""Agent management and registry for tournament framework."""

import importlib
import inspect
from pathlib import Path
from kuhn3p import Player


class AgentRegistry:
    """Registry for managing and loading tournament agents."""
    
    def __init__(self):
        self.agents = {}  # name -> player_class
        self.instances = {}  # name -> player_instance
    
    def register(self, name, agent_class, **default_kwargs):
        """
        Register an agent class.
        
        Args:
            name: Friendly name for the agent
            agent_class: Class that extends Player
            **default_kwargs: Default initialization parameters
        """
        assert issubclass(agent_class, Player), f"{agent_class} must extend Player"
        self.agents[name] = (agent_class, default_kwargs)
    
    def create(self, name, **kwargs):
        """
        Create an instance of a registered agent.
        
        Args:
            name: Registered agent name
            **kwargs: Initialization parameters (override defaults)
            
        Returns:
            Player instance
        """
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not registered. Available: {list(self.agents.keys())}")
        
        agent_class, defaults = self.agents[name]
        params = {**defaults, **kwargs}
        return agent_class(**params)
    
    def create_instance(self, name, **kwargs):
        """Create and cache an instance."""
        if name not in self.instances:
            self.instances[name] = self.create(name, **kwargs)
        return self.instances[name]
    
    def list_agents(self):
        """Return list of registered agent names."""
        return list(self.agents.keys())
    
    def get_info(self, name):
        """Get detailed info about a registered agent."""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not registered")
        
        agent_class, defaults = self.agents[name]
        sig = inspect.signature(agent_class.__init__)
        
        return {
            'name': name,
            'class': agent_class.__name__,
            'module': agent_class.__module__,
            'parameters': {
                param: sig.parameters[param].default 
                for param in sig.parameters 
                if param not in ('self', 'rng')
            },
            'defaults': defaults,
        }


# Global registry instance
_default_registry = None


def get_registry():
    """Get or create the default registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
        _setup_default_agents(_default_registry)
    return _default_registry


def _setup_default_agents(registry):
    """Setup default agents in the registry."""
    from kuhn3p.players import Bluffer, Chump
    
    registry.register('Bluffer', Bluffer, bluff=0.2)
    registry.register('Bluffer_aggressive', Bluffer, bluff=0.5)
    registry.register('Bluffer_conservative', Bluffer, bluff=0.1)
    registry.register('Chump_passive', Chump, bet=0.99, call=0.01, fold=0.0)
    registry.register('Chump_aggressive', Chump, bet=0.1, call=0.8, fold=0.1)
    registry.register('Chump_balanced', Chump, bet=0.5, call=0.5, fold=0.5)


def register_agent(name, agent_class, **defaults):
    """Convenience function to register an agent globally."""
    get_registry().register(name, agent_class, **defaults)


def create_agent(name, **kwargs):
    """Convenience function to create an agent from the global registry."""
    return get_registry().create(name, **kwargs)


def load_agents_from_directory(directory):
    """
    Load all agent classes from a directory.
    
    Expects files to contain classes that extend kuhn3p.Player.
    Classes should be named with CamelCase.
    
    Args:
        directory: Path to directory containing agent modules
        
    Returns:
        Dictionary of {agent_name: agent_class}
    """
    agents = {}
    dir_path = Path(directory)
    
    for py_file in dir_path.glob('*.py'):
        if py_file.name.startswith('_'):
            continue
        
        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find all Player subclasses in the module
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, Player) and 
                obj is not Player and
                obj.__module__ == module_name):
                agents[name] = obj
    
    return agents
