#!/usr/bin/env python
"""
Example tournament runner showing how to use the tournament framework.

This script demonstrates:
1. Running a match between 3 specific agents
2. Running a full round-robin tournament
3. Viewing results and rankings
"""

from kuhn3p import players, agents, tournament
from kuhn3p.tournament import Tournament, Match


def example_single_match():
    """Example: Run a single match between 3 agents."""
    print("=" * 80)
    print("EXAMPLE 1: Single Match")
    print("=" * 80)
    
    # Create player instances
    player1 = players.Bluffer(0.2)
    player2 = players.Chump(0.99, 0.01, 0.0)
    player3 = players.Chump(0.5, 0.5, 0.5)
    
    # Run the match
    result = tournament.TournamentMatch.run(
        player1, player2, player3, 
        hands=1000, 
        seed=12345
    )
    
    print(f"Match Results:")
    scores = result['scores']
    score_sum = sum(scores)
    print(f"  Winner: Player {result['winner']} with score {scores[result['winner']]:,.1f}")
    print(f"  Scores: [{scores[0]:,.1f}, {scores[1]:,.1f}, {scores[2]:,.1f}]")
    print(f"  Score sum (should be ~0): {score_sum:.1f}")
    print()


def example_tournament():
    """Example: Run a full round-robin tournament."""
    print("=" * 80)
    print("EXAMPLE 2: Round-Robin Tournament with Multiple Agents")
    print("=" * 80)
    
    # Create agents using the registry
    registry = agents.get_registry()
    
    agent_names = [
        'Bluffer',
        'Bluffer_aggressive', 
        'Bluffer_conservative',
        'Chump_passive',
        'Chump_aggressive',
        'Chump_balanced',
    ]
    
    # Create agent list with names
    tournament_agents = [
        (name, registry.create(name))
        for name in agent_names
    ]
    
    # Create and run tournament
    t = Tournament(tournament_agents)
    t.run_round_robin(
        hands_per_matchup=500,
        num_rounds=2,
        seed=42,
        verbose=True
    )
    
    # Print results
    t.print_results(sort_by='total_score')
    
    # Verify zero-sum
    total_score = sum(result['total_score'] for result in t.results.values())
    print(f"\nTotal tournament score sum: {total_score:.1f} (should be ~0 for zero-sum game)")


def example_custom_agents():
    """Example: Register and run tournament with custom agents."""
    print()
    print("=" * 80)
    print("EXAMPLE 3: Custom Agent Registration")
    print("=" * 80)
    
    # Register some custom configurations
    registry = agents.get_registry()
    
    # You can also register custom subclasses or configurations
    # For this example, we'll use the existing ones with different names
    registry.register('MyBluffer', players.Bluffer, bluff=0.3)
    registry.register('MyChump', players.Chump, bet=0.7, call=0.2, fold=0.1)
    
    print("Custom agents registered:", registry.list_agents()[-2:])
    
    # Create a small tournament with these
    agent_list = []
    for name in ['MyBluffer', 'MyChump', 'Chump_balanced']:
        agent_list.append((name, registry.create(name)))
    
    t = Tournament(agent_list)
    t.run_round_robin(
        hands_per_matchup=300,
        num_rounds=1,
        seed=99,
        verbose=False
    )
    
    t.print_results()


if __name__ == '__main__':
    # Run all examples
    example_single_match()
    
    print()
    example_tournament()
    
    print()
    example_custom_agents()
