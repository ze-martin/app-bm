import unittest
from datetime import datetime, timezone
from scripts.refresh import evaluate

def fixture(id, home=1, away=2, goals=(0, 1), date='2026-02-01T12:00:00+00:00', status='FT'):
    return {'fixture': {'id': id, 'date': date, 'status': {'short': status}},
        'teams': {'home': {'id': home, 'name': str(home), 'winner': goals[0] > goals[1]},
                  'away': {'id': away, 'name': str(away), 'winner': goals[1] > goals[0]}},
        'goals': dict(zip(['home', 'away'], goals))}

class Rules(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.future = fixture(1, date='2026-11-05T12:00:00+00:00', status='NS')
        self.h2h = fixture(2, home=2, away=1)
        self.previous = {1: fixture(3, goals=(2, 0))}
    def run_rule(self, ranks=None, history=None):
        return evaluate(self.future, [self.h2h] if history is None else history,
            {2: 6} if ranks is None else ranks, self.previous, self.now)[0]
    def test_away_one_goal_qualifies_current_home(self):
        self.assertEqual(self.run_rule()['status'], 'candidate')
    def test_top_five_excluded(self):
        self.assertEqual(self.run_rule({2: 5})['status'], 'excluded')
    def test_missing_rank_pending(self):
        self.assertEqual(self.run_rule({})['status'], 'pending')
    def test_non_reversed_venue_not_accepted(self):
        self.assertEqual(self.run_rule(history=[fixture(4)])['status'], 'excluded')
    def test_future_h2h_ignored(self):
        self.h2h['fixture']['date'] = '2026-11-04T12:00:00+00:00'
        self.assertEqual(self.run_rule()['status'], 'excluded')
    def test_previous_draw_excluded(self):
        self.previous[1] = fixture(5, goals=(1,1))
        self.assertEqual(self.run_rule()['status'], 'excluded')
    def test_previous_year_ignored(self):
        self.h2h['fixture']['date'] = '2025-02-01T12:00:00+00:00'
        self.assertEqual(self.run_rule()['status'], 'excluded')
    def test_started_fixture_excluded(self):
        self.future['fixture']['status']['short'] = '2H'
        self.assertEqual(self.run_rule()['status'], 'excluded')
    def test_historical_home_needs_two_goals(self):
        self.h2h['goals'] = {'home': 1, 'away': 1}
        self.previous[2] = fixture(6, home=2, away=3, goals=(2,0))
        result = evaluate(self.future, [self.h2h], {1: 6, 2: 6}, self.previous, self.now)
        self.assertEqual(result[1]['status'], 'excluded')
        self.h2h['goals']['home'] = 2
        result = evaluate(self.future, [self.h2h], {1: 6, 2: 6}, self.previous, self.now)
        self.assertEqual(result[1]['status'], 'candidate')

if __name__ == '__main__':
    unittest.main()
