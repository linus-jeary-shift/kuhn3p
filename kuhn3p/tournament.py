"""Tournament framework for running Kuhn poker competitions."""

from kuhn3p import deck, dealer
from kuhn3p.validator import AgentValidator
from random import Random


class Match:
    """Represents a match between three players over multiple hands."""
    
    def __init__(self, players, num_hands=1000, rng=None):
        """
        Initialize a match.
        
        Args:
            players: List of 3 Player instances
            num_hands: Number of hands to play in this match
            rng: Random number generator (or seed value)
        """
        assert len(players) == 3, "Match requires exactly 3 players"
        self.players = players
        self.num_hands = num_hands
        
        if rng is None:
            rng = Random()
        elif isinstance(rng, int):
            temp_rng = Random()
            temp_rng.seed(rng)
            rng = temp_rng
        
        self.rng = rng
        self.scores = [0, 0, 0]
    
    def play(self, button_rotation=True):
        """
        Play the match.
        
        Args:
            button_rotation: If True, rotate button position each hand
            
        Returns:
            List of final scores for the three players
        """
        for hand_num in range(self.num_hands):
            if button_rotation:
                # Rotate button position
                first = hand_num % 3
                second = (first + 1) % 3
                third = (second + 1) % 3
                hand_players = [self.players[first], self.players[second], self.players[third]]
            else:
                hand_players = self.players
            
            # Play the hand
            (state, delta) = dealer.play_hand(hand_players, deck.shuffled(self.rng))
            
            if button_rotation:
                # Map results back to original player order
                for i in range(3):
                    self.scores[(first + i) % 3] += delta[i]
            else:
                for i in range(3):
                    self.scores[i] += delta[i]
        
        # Verify zero-sum property (poker is zero-sum, so all scores should sum to ~0)
        score_sum = sum(self.scores)
        if abs(score_sum) > 0.1:  # Allow small floating point tolerance
            import warnings
            warnings.warn(
                f"Match scores do not sum to zero (sum={score_sum:.2f}). "
                f"Expected ~0 for a zero-sum game. Scores: {self.scores}"
            )
        
        return self.scores


class Tournament:
    """Manages a round-robin tournament with multiple agents."""
    
    def __init__(self, agents):
        """
        Initialize a tournament.
        
        Args:
            agents: List of (name, player_instance) tuples or Player instances.
                   If Player instances, names are generated automatically.
        """
        self.agents = []
        if agents and isinstance(agents[0], tuple):
            # List of (name, player) tuples
            self.agents = agents
        else:
            # List of Player instances
            self.agents = [(f"Agent_{i}", agent) for i, agent in enumerate(agents)]
        
        self.results = {}  # (idx1, idx2, idx3) -> scores
        self.matchups = {}  # (idx1, idx2, idx3) -> list of match results
    
    def run_round_robin(self, hands_per_matchup=1000, num_rounds=1, seed=None, verbose=True):
        """
        Run a round-robin tournament where every unique combination of 3 agents plays together.
        
        Args:
            hands_per_matchup: Number of hands per match
            num_rounds: Number of times to repeat each unique matchup
            seed: Random seed for reproducibility
            verbose: Whether to print progress
            
        Returns:
            Dictionary of results organized by agent index
        """
        from itertools import combinations
        
        n = len(self.agents)
        rng = Random(seed)
        
        # Generate all unique 3-player matchups
        matchups = list(combinations(range(n), 3))
        
        if verbose:
            print(f"Tournament: {n} agents")
            print(f"Total unique matchups: {len(matchups)}")
            print(f"Rounds per matchup: {num_rounds}")
            print(f"Hands per match: {hands_per_matchup}")
            print()
        
        total_matches = len(matchups) * num_rounds
        match_count = 0
        
        for round_num in range(num_rounds):
            for idx1, idx2, idx3 in matchups:
                match_count += 1
                
                # Create player instances for this match
                players = [self.agents[idx1][1], self.agents[idx2][1], self.agents[idx3][1]]
                
                # Create and run match
                match = Match(players, num_hands=hands_per_matchup, rng=rng)
                scores = match.play()
                
                # Store results
                matchup_key = (idx1, idx2, idx3)
                if matchup_key not in self.matchups:
                    self.matchups[matchup_key] = []
                self.matchups[matchup_key].append(scores)
                
                if verbose and match_count % max(1, total_matches // 10) == 0:
                    print(f"Progress: {match_count}/{total_matches} matches completed")
        
        # Calculate aggregate results
        self._calculate_results()
        
        if verbose:
            print("\nTournament complete!")
        
        return self.results
    
    def _calculate_results(self):
        """Calculate aggregate results from all matches."""
        self.results = {}
        
        for i in range(len(self.agents)):
            self.results[i] = {
                'name': self.agents[i][0],
                'total_score': 0,
                'matches_played': 0,
                'num_first_places': 0,
                'num_second_places': 0,
                'num_third_places': 0,
            }
        
        for (idx1, idx2, idx3), matches in self.matchups.items():
            for scores in matches:
                for position, idx in enumerate([idx1, idx2, idx3]):
                    self.results[idx]['total_score'] += scores[position]
                    self.results[idx]['matches_played'] += 1
                    
                    # Find placement in this match
                    sorted_scores = sorted(
                        [(scores[j], [idx1, idx2, idx3][j]) for j in range(3)],
                        key=lambda x: x[0],
                        reverse=True
                    )
                    
                    for place, (score, player_idx) in enumerate(sorted_scores):
                        if player_idx == idx:
                            if place == 0:
                                self.results[idx]['num_first_places'] += 1
                            elif place == 1:
                                self.results[idx]['num_second_places'] += 1
                            else:
                                self.results[idx]['num_third_places'] += 1
                            break
    
    def get_rankings(self, sort_by='total_score'):
        """
        Get ranked list of agents.
        
        Args:
            sort_by: 'total_score', 'matches_played', 'win_rate', etc.
            
        Returns:
            Sorted list of (name, stats) tuples
        """
        if sort_by == 'total_score':
            key_func = lambda x: x[1]['total_score']
        elif sort_by == 'win_rate':
            key_func = lambda x: x[1]['num_first_places'] / max(1, x[1]['num_first_places'] + 
                                                                    x[1]['num_second_places'] + 
                                                                    x[1]['num_third_places'])
        else:
            key_func = lambda x: x[1][sort_by]
        
        ranked = sorted(self.results.items(), key=key_func, reverse=True)
        return [(name_idx[1]['name'], name_idx[1]) for name_idx in ranked]
    
    def print_results(self, sort_by='total_score'):
        """Print tournament results in a formatted table."""
        rankings = self.get_rankings(sort_by)
        
        print("\n" + "="*80)
        print(f"Tournament Results (sorted by {sort_by})")
        print("="*80)
        print(f"{'Rank':<6} {'Agent':<30} {'Score':<12} {'Matches':<10} {'1st':<6} {'2nd':<6} {'3rd':<6}")
        print("-"*80)
        
        for rank, (name, stats) in enumerate(rankings, 1):
            score = stats['total_score']
            print(f"{rank:<6} {name:<30} {score:>11.1f} {stats['matches_played']:<10} "
                  f"{stats['num_first_places']:<6} {stats['num_second_places']:<6} {stats['num_third_places']:<6}")
        
        print("="*80)


class TournamentMatch:
    """Simpler interface for running a single match between specific agents."""
    
    @staticmethod
    def run(player1, player2, player3, hands=1000, seed=None):
        """
        Run a single match and return results.
        
        Args:
            player1, player2, player3: Player instances
            hands: Number of hands to play
            seed: Random seed
            
        Returns:
            Dictionary with match results and statistics
        """
        match = Match([player1, player2, player3], num_hands=hands, rng=seed)
        scores = match.play()
        
        total_bet = abs(scores[0]) + abs(scores[1]) + abs(scores[2])
        
        return {
            'scores': scores,
            'winner': scores.index(max(scores)),
            'runner_up': sorted(range(3), key=lambda i: scores[i], reverse=True)[1],
            'result': [scores[i] for i in range(3)],
            'total_chips_wagered': total_bet,
        }
