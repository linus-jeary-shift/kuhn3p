"""Tournament framework for running Kuhn poker competitions.

Key design principles
---------------------
* Cross-match learning is **disabled by default** in both run_round_robin modes.
  Each match receives a deep-copy of every agent so that information gathered
  in one match cannot influence decisions in another.  This is the fair
  competition rule.
* Parallelism via ProcessPoolExecutor + 'fork' context is the default mode.
  The serial run_round_robin is retained for debugging and sequential analysis.
* Optional hand recording captures every hand to memory; results can then be
  saved as CSV / JSON and visualised with plot_results().
"""

import copy
import csv
import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from itertools import combinations
from random import Random

from kuhn3p import betting, deck, dealer
from kuhn3p.validator import AgentValidator

# All 6 permutations of seating slots [0,1,2] arranged so that every pair
# of consecutive rounds uses one seating from each "high-exposure" class.
# In a 3-player match with button rotation, one agent always occupies
# acting-position 1 when the last-listed agent (typically the Exploiter) is
# in acting-position 2 — the most advantageous position for an Exploiter.
# Alternating between the two classes each round means that over any even
# number of rounds, both Nash agents see each exposure type equally often.
#
# Classes (for matchup [A=slot0, B=slot1, E=slot2]):
#   B_HIGH (E in pos 2 at h=3k, B in pos 1): (0,1,2), (1,2,0), (2,0,1)
#   A_HIGH (E in pos 2, A in pos 1):          (0,2,1), (1,0,2), (2,1,0)
# Ordering below alternates B_HIGH / A_HIGH so any 2-round window is balanced.
_SEAT_PERMS = [
    (0, 1, 2),   # round % 6 == 0  →  B_HIGH
    (0, 2, 1),   # round % 6 == 1  →  A_HIGH
    (1, 2, 0),   # round % 6 == 2  →  B_HIGH
    (1, 0, 2),   # round % 6 == 3  →  A_HIGH
    (2, 0, 1),   # round % 6 == 4  →  B_HIGH
    (2, 1, 0),   # round % 6 == 5  →  A_HIGH
]


# ---------------------------------------------------------------------------
# Hand record helper
# ---------------------------------------------------------------------------

def _make_hand_record(
    match_id,
    hand_num,
    agent_names,
    cards,
    terminal_state,
    payoffs,
    shown_cards,
):
    """
    Build a flat dict describing one completed hand, suitable for CSV export.

    Fields
    ------
    match_id            : "(idx0,idx1,idx2)" string — which agents played
    hand_num            : sequential hand number within the match
    seat{i}_agent       : name of the agent in seat i
    seat{i}_card        : card held by seat i (0=J, 1=Q, 2=K, 3=A)
    seat{i}_card_name   : human-readable card name
    terminal_state      : integer terminal state (12-24)
    action_sequence     : e.g. "crc" — 'c'=check/call, 'r'=bet, 'f'=fold
    pot_size            : total chips in the pot
    seat{i}_payoff      : net chips won/lost by seat i
    seat{i}_shown       : card shown at showdown (empty string if folded)
    """
    CARD_NAMES = {0: 'J', 1: 'Q', 2: 'K', 3: 'A'}
    record = {
        'match_id': str(match_id),
        'hand_num': hand_num,
    }
    for i in range(3):
        record[f'seat{i}_agent']     = agent_names[i]
        record[f'seat{i}_card']      = cards[i]
        record[f'seat{i}_card_name'] = CARD_NAMES[cards[i]]
    record['terminal_state']  = terminal_state
    record['action_sequence'] = betting.to_string(terminal_state)
    record['pot_size']        = betting.pot_size(terminal_state)
    for i in range(3):
        record[f'seat{i}_payoff'] = payoffs[i]
        sc = shown_cards[i]
        record[f'seat{i}_shown'] = CARD_NAMES[sc] if sc is not None else ''
    return record


# ---------------------------------------------------------------------------
# Module-level worker (must be top-level for pickle / fork)
# ---------------------------------------------------------------------------

def _run_match_worker(
    agents_snapshot,
    agent_names,
    idx1, idx2, idx3,
    num_hands,
    seed,
    record_hands,
    round_num=0,
):
    """
    Worker function executed in a subprocess for each match.

    Agents arrive as a pickled snapshot; each worker therefore operates on
    an independent copy — cross-match learning is structurally impossible.

    Structured seating rotation
    ---------------------------
    The three agents are assigned to match-player slots 0/1/2 using the
    deterministic permutation _SEAT_PERMS[round_num % 6].  Over any 6
    consecutive rounds of the same matchup this cycles through all 6
    permutations of {0,1,2} exactly once, guaranteeing that each agent
    occupies each match-player slot equally often and that both Nash-type
    agents see each "high-exposure" seating class (the slot that acts in
    position 1 when the Exploiter is in position 2) the same number of
    times.  The internal match seed is still derived from `seed` so
    hand sequences remain reproducible.

    Returns
    -------
    (idx1, idx2, idx3, scores, hand_log)
      scores    : length-3 list of net chip totals indexed as (idx1, idx2, idx3)
      hand_log  : list of hand-record dicts (empty when record_hands=False)
    """
    seat_order  = _SEAT_PERMS[round_num % 6]
    all_indices = [idx1, idx2, idx3]
    seated      = [all_indices[seat_order[k]] for k in range(3)]

    players  = [agents_snapshot[i] for i in seated]
    names    = [agent_names[i]     for i in seated]
    match_id = (idx1, idx2, idx3)
    match = Match(
        players,
        num_hands    = num_hands,
        rng          = seed,
        agent_names  = names,
        match_id     = match_id,
        record_hands = record_hands,
    )
    scores = match.play()
    # Un-permute: map match-player-slot scores back to the (idx1,idx2,idx3) order.
    result_scores = [0, 0, 0]
    for k in range(3):
        result_scores[seat_order[k]] = scores[k]
    return (idx1, idx2, idx3, result_scores, match.hand_log)


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------

class Match:
    """Represents a match between three players over multiple hands."""

    def __init__(
        self,
        players,
        num_hands=1000,
        rng=None,
        agent_names=None,
        match_id=None,
        record_hands=False,
    ):
        """
        Parameters
        ----------
        players      : list of 3 Player instances
        num_hands    : number of hands to play
        rng          : Random instance or integer seed
        agent_names  : display names for the three players
        match_id     : tuple identifier written into hand records
        record_hands : if True, populate self.hand_log with one dict per hand
        """
        assert len(players) == 3, "Match requires exactly 3 players"
        self.players      = players
        self.num_hands    = num_hands
        self.agent_names  = agent_names or [str(p) for p in players]
        self.match_id     = match_id or (0, 1, 2)
        self.record_hands = record_hands

        if rng is None:
            rng = Random()
        elif isinstance(rng, int):
            r = Random()
            r.seed(rng)
            rng = r
        self.rng      = rng
        self.scores   = [0, 0, 0]
        self.hand_log = []   # populated only when record_hands=True

    def play(self, button_rotation=True):
        """
        Play all hands and return the final scores list.

        Parameters
        ----------
        button_rotation : rotate the dealer button each hand (default True)
        """
        for hand_num in range(self.num_hands):
            if button_rotation:
                first  = hand_num % 3
                second = (first + 1) % 3
                third  = (second + 1) % 3
                order  = [first, second, third]
            else:
                order = [0, 1, 2]

            hand_players = [self.players[order[i]] for i in range(3)]
            cards_dealt  = deck.shuffled(self.rng)

            state, delta = dealer.play_hand(hand_players, cards_dealt)

            for i in range(3):
                self.scores[order[i]] += delta[i]

            if self.record_hands:
                seat_cards   = [cards_dealt[order[i]] for i in range(3)]
                seat_payoffs = list(delta)
                shown = [
                    cards_dealt[order[i]]
                    if betting.at_showdown(state, i) else None
                    for i in range(3)
                ]
                self.hand_log.append(_make_hand_record(
                    match_id       = self.match_id,
                    hand_num       = hand_num,
                    agent_names    = [self.agent_names[order[i]] for i in range(3)],
                    cards          = seat_cards,
                    terminal_state = state,
                    payoffs        = seat_payoffs,
                    shown_cards    = shown,
                ))

        score_sum = sum(self.scores)
        if abs(score_sum) > 0.1:
            import warnings
            warnings.warn(
                f"Match scores do not sum to zero (sum={score_sum:.2f}). "
                f"Scores: {self.scores}"
            )
        return self.scores


# ---------------------------------------------------------------------------
# Tournament
# ---------------------------------------------------------------------------

class Tournament:
    """
    Manages a round-robin tournament with multiple agents.

    Cross-match learning policy
    ---------------------------
    Both run_round_robin and run_round_robin_parallel deep-copy every agent
    before each match.  State accumulated during one match is discarded before
    the next — no cross-match learning is possible.  Within a single match,
    agents may update internal state normally.
    """

    def __init__(self, agents):
        """
        Parameters
        ----------
        agents : list of (name, player_instance) tuples or bare Player instances
        """
        if agents and isinstance(agents[0], tuple):
            self.agents = list(agents)
        else:
            self.agents = [(f"Agent_{i}", a) for i, a in enumerate(agents)]

        self.results  = {}
        self.matchups = {}      # (idx1, idx2, idx3) -> [scores_per_round, ...]
        self.hand_log = []      # flat list of hand dicts (when record_hands=True)

    # ------------------------------------------------------------------
    # Serial round-robin
    # ------------------------------------------------------------------

    def run_round_robin(
        self,
        hands_per_matchup=1000,
        num_rounds=1,
        seed=None,
        verbose=True,
        record_hands=False,
    ):
        """
        Serial round-robin tournament.

        Agents are deep-copied before every match (cross-match learning
        is prohibited).  Tasks run sequentially in the main process.

        Parameters
        ----------
        record_hands : capture per-hand data into self.hand_log
        """
        n        = len(self.agents)
        rng      = Random(seed)
        matchups = list(combinations(range(n), 3))
        total    = len(matchups) * num_rounds

        if verbose:
            print(f"Tournament (serial): {n} agents")
            print(f"Total unique matchups: {len(matchups)}")
            print(f"Rounds per matchup:    {num_rounds}")
            print(f"Hands per match:       {hands_per_matchup}")
            print()

        done = 0
        for round_num in range(num_rounds):
            seat_perm = _SEAT_PERMS[round_num % 6]
            for idx1, idx2, idx3 in matchups:
                done += 1
                all_idx = [idx1, idx2, idx3]
                seated  = [all_idx[seat_perm[k]] for k in range(3)]
                players = [copy.deepcopy(self.agents[seated[k]][1]) for k in range(3)]
                names   = [self.agents[seated[k]][0]               for k in range(3)]
                match = Match(
                    players,
                    num_hands    = hands_per_matchup,
                    rng          = rng,
                    agent_names  = names,
                    match_id     = (idx1, idx2, idx3),
                    record_hands = record_hands,
                )
                raw_scores = match.play()
                # Un-permute scores back to (idx1, idx2, idx3) order.
                scores = [0, 0, 0]
                for k in range(3):
                    scores[seat_perm[k]] = raw_scores[k]
                self.matchups.setdefault((idx1, idx2, idx3), []).append(scores)
                if record_hands:
                    self.hand_log.extend(match.hand_log)
                if verbose and done % max(1, total // 10) == 0:
                    print(f"Progress: {done}/{total} matches completed")

        self._calculate_results()
        if verbose:
            print("\nTournament complete!")
        return self.results

    # ------------------------------------------------------------------
    # Parallel round-robin
    # ------------------------------------------------------------------

    def run_round_robin_parallel(
        self,
        hands_per_matchup=1000,
        num_rounds=1,
        seed=None,
        verbose=True,
        max_workers=None,
        record_hands=False,
    ):
        """
        Parallel round-robin using ProcessPoolExecutor and fork workers.

        Each match task runs in an isolated subprocess.  Agents are pickled
        (deep-copied) at the point of task submission, so cross-match
        learning is structurally impossible.

        Parameters
        ----------
        max_workers  : worker processes (default: all logical CPUs)
        record_hands : capture per-hand data into self.hand_log
        """
        n           = len(self.agents)
        rng         = Random(seed)
        matchups    = list(combinations(range(n), 3))
        total_tasks = len(matchups) * num_rounds

        if max_workers is None:
            max_workers = os.cpu_count() or 1

        if verbose:
            print(f"Tournament (parallel, {max_workers} workers): {n} agents")
            print(f"Total unique matchups: {len(matchups)}")
            print(f"Rounds per matchup:    {num_rounds}")
            print(f"Hands per match:       {hands_per_matchup}")
            print(f"Total tasks:           {total_tasks}")
            print()

        agents_snap = [a for _, a in self.agents]
        agent_names = [n for n, _ in self.agents]

        tasks = []
        for round_num in range(num_rounds):
            for idx1, idx2, idx3 in matchups:
                tasks.append((idx1, idx2, idx3, rng.randint(0, 2**31 - 1), round_num))

        completed = 0
        with ProcessPoolExecutor(
            max_workers=max_workers,
            mp_context=multiprocessing.get_context('fork'),
        ) as pool:
            futures = {
                pool.submit(
                    _run_match_worker,
                    agents_snap, agent_names,
                    idx1, idx2, idx3, hands_per_matchup, task_seed, record_hands,
                    round_num,
                ): (idx1, idx2, idx3)
                for idx1, idx2, idx3, task_seed, round_num in tasks
            }
            for future in as_completed(futures):
                idx1, idx2, idx3, scores, hand_log = future.result()
                self.matchups.setdefault((idx1, idx2, idx3), []).append(scores)
                if record_hands:
                    self.hand_log.extend(hand_log)
                completed += 1
                if verbose and completed % max(1, total_tasks // 10) == 0:
                    print(f"Progress: {completed}/{total_tasks} matches completed")

        self._calculate_results()
        if verbose:
            print("\nTournament complete!")
        return self.results

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _calculate_results(self):
        self.results = {
            i: {
                'name':              self.agents[i][0],
                'total_score':       0,
                'matches_played':    0,
                'num_first_places':  0,
                'num_second_places': 0,
                'num_third_places':  0,
                'match_scores':      [],
                # (opp1_name, opp2_name) tuple -> list of per-match scores
                'matchup_scores':    {},
            }
            for i in range(len(self.agents))
        }
        for (idx1, idx2, idx3), matches in self.matchups.items():
            indices = [idx1, idx2, idx3]
            for scores in matches:
                for pos, idx in enumerate(indices):
                    self.results[idx]['total_score']    += scores[pos]
                    self.results[idx]['matches_played'] += 1
                    self.results[idx]['match_scores'].append(scores[pos])
                    place = sorted(range(3), key=lambda j: scores[j], reverse=True).index(pos)
                    if   place == 0: self.results[idx]['num_first_places']  += 1
                    elif place == 1: self.results[idx]['num_second_places'] += 1
                    else:            self.results[idx]['num_third_places']  += 1
                    # record per-matchup breakdown
                    opp_names = tuple(
                        self.agents[indices[j]][0]
                        for j in range(3) if j != pos
                    )
                    self.results[idx]['matchup_scores'] \
                        .setdefault(opp_names, []) \
                        .append(scores[pos])

    def get_rankings(self, sort_by='total_score'):
        if sort_by == 'win_rate':
            key = lambda x: x[1]['num_first_places'] / max(1, x[1]['matches_played'])
        else:
            key = lambda x: x[1][sort_by]
        return [
            (s['name'], s)
            for _, s in sorted(self.results.items(), key=key, reverse=True)
        ]

    def print_matchup_extremes(self):
        """
        For every agent, print their single best and single worst opponent pair
        by average chips won/lost across all rounds of that matchup.

        This reveals which specific two-opponent combinations a player thrives
        against or struggles with — useful for identifying exploitable patterns
        and potential collusion effects in the field.
        """
        import statistics as _stats

        rankings = self.get_rankings('total_score')
        W = 94
        print("\n" + "=" * W)
        print("Best & Worst Matchups Per Agent  (average chips vs that opponent pair)")
        print("=" * W)

        for name, s in rankings:
            ms = s.get('matchup_scores', {})
            if not ms:
                continue
            avgs = {
                pair: _stats.mean(vals)
                for pair, vals in ms.items()
            }
            best_pair  = max(avgs, key=avgs.__getitem__)
            worst_pair = min(avgs, key=avgs.__getitem__)
            best_avg   = avgs[best_pair]
            worst_avg  = avgs[worst_pair]
            best_n     = len(ms[best_pair])
            worst_n    = len(ms[worst_pair])

            print(f"\n  {name}")
            opp_str = ' & '.join(best_pair)
            print(f"    Best  vs  {opp_str:<44}  avg {best_avg:>+9.1f}  "
                  f"({best_n} match{'es' if best_n != 1 else ''})")
            opp_str = ' & '.join(worst_pair)
            print(f"    Worst vs  {opp_str:<44}  avg {worst_avg:>+9.1f}  "
                  f"({worst_n} match{'es' if worst_n != 1 else ''})")

        print("\n" + "=" * W)

    def print_results(self, sort_by='total_score'):
        """Print a formatted rankings table to stdout."""
        rankings = self.get_rankings(sort_by)
        W = 86
        print("\n" + "=" * W)
        print(f"Tournament Results (sorted by {sort_by})")
        print("=" * W)
        print(f"{'Rank':<6} {'Agent':<28} {'Score':>12} {'Matches':<10} "
              f"{'1st':<6} {'2nd':<6} {'3rd':<6} {'Score/Match':>12}")
        print("-" * W)
        for rank, (name, s) in enumerate(rankings, 1):
            spm = s['total_score'] / max(1, s['matches_played'])
            print(f"{rank:<6} {name:<28} {s['total_score']:>12.1f} "
                  f"{s['matches_played']:<10} {s['num_first_places']:<6} "
                  f"{s['num_second_places']:<6} {s['num_third_places']:<6} {spm:>12.2f}")
        print("=" * W)

    # ------------------------------------------------------------------
    # Data export
    # ------------------------------------------------------------------

    def save_results(self, output_dir='.', label=None):
        """
        Save tournament results to *output_dir*.

        Files written
        -------------
        tournament_summary.json
            Full results dict plus metadata (timestamp, agent list, totals).
        match_results.csv
            One row per (matchup x round): agent names, indices, scores.
        hand_data.csv   [only if self.hand_log is populated]
            One row per hand across all matches.

        Parameters
        ----------
        output_dir : directory path; created if it does not exist
        label      : optional string appended to all filenames
        """
        os.makedirs(output_dir, exist_ok=True)
        suffix = f"_{label}" if label else ""
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")

        # tournament_summary.json
        import statistics as _stats

        summary = {
            'created':       ts,
            'label':         label or '',
            'agents':        [name for name, _ in self.agents],
            'total_matches': sum(len(v) for v in self.matchups.values()),
            'results': {},
        }
        for s in self.results.values():
            # Build a JSON-safe per-agent entry
            ms = s.get('matchup_scores', {})
            best_matchup  = None
            worst_matchup = None
            if ms:
                avgs = {pair: _stats.mean(vals) for pair, vals in ms.items()}
                bp = max(avgs, key=avgs.__getitem__)
                wp = min(avgs, key=avgs.__getitem__)
                best_matchup  = {'opponents': list(bp), 'avg_score': round(avgs[bp],  2)}
                worst_matchup = {'opponents': list(wp), 'avg_score': round(avgs[wp], 2)}
            entry = {k: v for k, v in s.items()
                     if k not in ('match_scores', 'matchup_scores')}
            entry['best_matchup']  = best_matchup
            entry['worst_matchup'] = worst_matchup
            summary['results'][s['name']] = entry
        json_path = os.path.join(output_dir, f"tournament_summary{suffix}.json")
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved: {json_path}")

        # match_results.csv
        match_rows = []
        for (idx1, idx2, idx3), rounds in self.matchups.items():
            n0, n1, n2 = (self.agents[idx1][0], self.agents[idx2][0], self.agents[idx3][0])
            for rnd, scores in enumerate(rounds):
                match_rows.append({
                    'idx0': idx1, 'idx1': idx2, 'idx2': idx3,
                    'agent0': n0, 'agent1': n1, 'agent2': n2,
                    'round':  rnd,
                    'score0': scores[0], 'score1': scores[1], 'score2': scores[2],
                    'winner': [n0, n1, n2][scores.index(max(scores))],
                })
        if match_rows:
            csv_match = os.path.join(output_dir, f"match_results{suffix}.csv")
            with open(csv_match, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(match_rows[0].keys()))
                w.writeheader()
                w.writerows(match_rows)
            print(f"Saved: {csv_match}  ({len(match_rows)} rows)")

        # hand_data.csv
        if self.hand_log:
            csv_hand = os.path.join(output_dir, f"hand_data{suffix}.csv")
            with open(csv_hand, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(self.hand_log[0].keys()))
                w.writeheader()
                w.writerows(self.hand_log)
            print(f"Saved: {csv_hand}  ({len(self.hand_log):,} rows)")

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def plot_results(self, output_dir=None, show=True, label=None):
        """
        Generate a four-panel performance visualisation.

        Panels
        ------
        1  Total score (horizontal bar, ranked highest to lowest)
        2  Score per match — mean ± std dev across all matches
        3  Placement counts — stacked 1st / 2nd / 3rd bar chart
        4  Score distribution — per-match box plot

        Parameters
        ----------
        output_dir : if given, saves as {output_dir}/performance[_label].png
        show       : call plt.show() after plotting
        label      : appended to figure title and filename
        """
        try:
            import matplotlib
            matplotlib.use('Agg' if not show else matplotlib.get_backend())
            import matplotlib.pyplot as plt
            import matplotlib.cm as cm
            import statistics
        except ImportError:
            raise ImportError(
                "matplotlib is required for plot_results(). "
                "Install with:  pip install matplotlib"
            )

        if not self.results:
            raise RuntimeError("No results — run the tournament first.")

        rankings = self.get_rankings('total_score')
        names    = [n for n, _ in rankings]
        stats    = [s for _, s in rankings]
        n        = len(names)
        colours  = [cm.tab10(i / max(n - 1, 1)) for i in range(n)]

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        title = "Tournament Performance"
        if label:
            title += f"  —  {label}"
        fig.suptitle(title, fontsize=15, fontweight='bold')

        # 1. Total score ---------------------------------------------------
        ax = axes[0, 0]
        total_scores = [s['total_score'] for s in stats]
        span = max(abs(v) for v in total_scores) or 1
        bars = ax.barh(range(n), total_scores, color=colours,
                       edgecolor='white', linewidth=0.4)
        ax.set_yticks(range(n))
        ax.set_yticklabels(names, fontsize=9)
        ax.invert_yaxis()
        ax.axvline(0, color='#333', linewidth=0.8, linestyle='--')
        ax.set_xlabel('Total chips')
        ax.set_title('Total Score')
        for bar, v in zip(bars, total_scores):
            ax.text(bar.get_width() + span * 0.015,
                    bar.get_y() + bar.get_height() / 2,
                    f'{v:,.0f}', va='center', fontsize=8)

        # 2. Score per match -----------------------------------------------
        ax = axes[0, 1]
        means, stds = [], []
        for s in stats:
            ms = s['match_scores']
            means.append(statistics.mean(ms) if ms else 0.0)
            stds.append(statistics.stdev(ms) if len(ms) > 1 else 0.0)
        ax.barh(range(n), means, xerr=stds, color=colours,
                edgecolor='white', linewidth=0.4,
                capsize=3, error_kw={'linewidth': 1.0, 'ecolor': '#555'})
        ax.set_yticks(range(n))
        ax.set_yticklabels(names, fontsize=9)
        ax.invert_yaxis()
        ax.axvline(0, color='#333', linewidth=0.8, linestyle='--')
        ax.set_xlabel('Chips per match  (mean ± std)')
        ax.set_title('Score Per Match')

        # 3. Placement counts ----------------------------------------------
        ax = axes[1, 0]
        firsts  = [s['num_first_places']  for s in stats]
        seconds = [s['num_second_places'] for s in stats]
        thirds  = [s['num_third_places']  for s in stats]
        ax.barh(range(n), firsts,  color='#27ae60', label='1st', edgecolor='white')
        ax.barh(range(n), seconds, left=firsts,
                color='#e67e22', label='2nd', edgecolor='white')
        ax.barh(range(n), thirds,
                left=[f + s for f, s in zip(firsts, seconds)],
                color='#c0392b', label='3rd', edgecolor='white')
        ax.set_yticks(range(n))
        ax.set_yticklabels(names, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel('Number of matches')
        ax.set_title('Placement Counts')
        ax.legend(loc='lower right', fontsize=8)

        # 4. Score distribution --------------------------------------------
        ax = axes[1, 1]
        data = [s['match_scores'] for s in stats]
        bp = ax.boxplot(
            data, vert=False, patch_artist=True, labels=names,
            medianprops=dict(color='black', linewidth=1.5),
            flierprops=dict(marker='o', markersize=2, alpha=0.4),
        )
        for patch, c in zip(bp['boxes'], colours):
            patch.set_facecolor(c)
            patch.set_alpha(0.75)
        ax.axvline(0, color='#333', linewidth=0.8, linestyle='--')
        ax.set_xlabel('Score per match')
        ax.set_title('Score Distribution (per match)')
        ax.tick_params(axis='y', labelsize=9)

        fig.tight_layout()

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            suffix    = f"_{label}" if label else ""
            plot_path = os.path.join(output_dir, f"performance{suffix}.png")
            fig.savefig(plot_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {plot_path}")

        if show:
            plt.show()

        return fig


# ---------------------------------------------------------------------------
# Simple single-match helper (API-compatible with the old version)
# ---------------------------------------------------------------------------

class TournamentMatch:
    """Convenience wrapper for running a single match between specific agents."""

    @staticmethod
    def run(player1, player2, player3, hands=1000, seed=None):
        """
        Run a single match and return a results dict.

        Returns
        -------
        dict with keys: scores, winner, runner_up, result, total_chips_wagered
        """
        match  = Match([player1, player2, player3], num_hands=hands, rng=seed)
        scores = match.play()
        return {
            'scores':              scores,
            'winner':              scores.index(max(scores)),
            'runner_up':           sorted(range(3), key=lambda i: scores[i], reverse=True)[1],
            'result':              list(scores),
            'total_chips_wagered': sum(abs(s) for s in scores),
        }
