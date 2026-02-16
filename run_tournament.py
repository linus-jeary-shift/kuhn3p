#!/usr/bin/env python
"""
Tournament runner utility for Kuhn poker agent competition.

This script provides utilities for running tournaments with competitor agents.
"""

import sys
import argparse
from pathlib import Path
from kuhn3p import agents, tournament


def run_tournament(agents_list, num_agents=None, hands_per_match=1000, 
                   num_rounds=1, seed=None, output_file=None):
    """
    Run a round-robin tournament.
    
    Args:
        agents_list: List of (name, agent_instance) tuples
        num_agents: If provided, only use first N agents
        hands_per_match: Number of hands per match
        num_rounds: Number of rounds
        seed: Random seed for reproducibility
        output_file: Optional file to save results to
        
    Returns:
        Tournament object with results
    """
    if num_agents:
        agents_list = agents_list[:num_agents]
    
    print(f"Running tournament with {len(agents_list)} agents")
    print(f"Hands per match: {hands_per_match}")
    print(f"Rounds: {num_rounds}")
    print()
    
    t = tournament.Tournament(agents_list)
    t.run_round_robin(
        hands_per_matchup=hands_per_match,
        num_rounds=num_rounds,
        seed=seed,
        verbose=True
    )
    
    # Print results
    t.print_results()
    
    # Save results if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write("Rank,Agent,Total Score,Matches,1st Place,2nd Place,3rd Place\n")
            for rank, (name, stats) in enumerate(t.get_rankings(), 1):
                f.write(f"{rank},{name},{stats['total_score']},{stats['matches_played']},"
                       f"{stats['num_first_places']},{stats['num_second_places']},"
                       f"{stats['num_third_places']}\n")
            print(f"\nResults saved to {output_file}")
    
    return t


def list_agents(agents_dir):
    """List all agents in a directory."""
    agents_dict = agents.load_agents_from_directory(agents_dir)
    
    print("Available agents:")
    print("-" * 40)
    for name, agent_class in sorted(agents_dict.items()):
        print(f"  {name}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Kuhn poker tournament runner'
    )
    
    parser.add_argument('command', 
                       choices=['run', 'list'],
                       help='Command to run')
    
    parser.add_argument('--agents-dir',
                       default='./agents/',
                       help='Directory containing agent files')
    
    parser.add_argument('--hands',
                       type=int,
                       default=1000,
                       help='Number of hands per match (default: 1000)')
    
    parser.add_argument('--rounds',
                       type=int,
                       default=1,
                       help='Number of tournament rounds (default: 1)')
    
    parser.add_argument('--num-agents',
                       type=int,
                       help='Limit to first N agents')
    
    parser.add_argument('--seed',
                       type=int,
                       help='Random seed for reproducibility')
    
    parser.add_argument('--output',
                       help='File to save results to (CSV format)')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        agents_dir = Path(args.agents_dir)
        if agents_dir.exists():
            list_agents(agents_dir)
        else:
            print(f"Agents directory not found: {agents_dir}")
            sys.exit(1)
    
    elif args.command == 'run':
        agents_dir = Path(args.agents_dir)
        
        if not agents_dir.exists():
            print(f"Agents directory not found: {agents_dir}")
            sys.exit(1)
        
        # Load agent modules
        print(f"Loading agents from {agents_dir}...")
        discovered_agents = agents.load_agents_from_directory(agents_dir)
        
        if not discovered_agents:
            print("No agents found!")
            sys.exit(1)
        
        # Create instances
        tournament_agents = [
            (name, agent_class())
            for name, agent_class in sorted(discovered_agents.items())
        ]
        
        # Run tournament
        t = run_tournament(
            tournament_agents,
            num_agents=args.num_agents,
            hands_per_match=args.hands,
            num_rounds=args.rounds,
            seed=args.seed,
            output_file=args.output
        )


if __name__ == '__main__':
    main()
