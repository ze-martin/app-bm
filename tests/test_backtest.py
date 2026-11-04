import unittest
from datetime import datetime,timedelta,timezone
from scripts.backtest_october import goal_timeline,settle_entry,reconstructed_rank

def fixture(id=1,home=1,away=2,hg=0,ag=1,at='2026-10-10T18:00:00+00:00',phase='Regular Season'):
    return {'fixture':{'id':id,'date':at,'status':{'short':'FT'}},
        'league':{'id':39,'season':2026,'round':phase+' - 10'},
        'teams':{'home':{'id':home},'away':{'id':away}},'goals':{'home':hg,'away':ag},'score':{'fulltime':{'home':hg,'away':ag}}}

def event(team,minute,detail='Normal Goal',extra=None):
    return {'type':'Goal','detail':detail,'team':{'id':team},'time':{'elapsed':minute,'extra':extra}}

class Retrospective(unittest.TestCase):
    def test_goal_exactly_70_does_not_qualify_entry(self):
        self.assertFalse(settle_entry(1,[{'teamId':1,'minute':70}])['entry'])
    def test_goal_after_70_wins_both_markets(self):
        result=settle_entry(1,[{'teamId':1,'minute':71}])
        self.assertTrue(result['entry'] and result['teamGoalAfter70'] and result['anyGoalAfter70'])
    def test_rival_goal_only_wins_any_goal(self):
        result=settle_entry(1,[{'teamId':2,'minute':89}])
        self.assertTrue(result['entry'] and result['anyGoalAfter70'])
        self.assertFalse(result['teamGoalAfter70'])
    def test_45_plus_is_not_after_70(self):
        result=settle_entry(1,[{'teamId':2,'minute':45,'extra':4}])
        self.assertFalse(result['anyGoalAfter70'])
    def test_90_plus_is_regulation_goal(self):
        f=fixture()
        goals,state=goal_timeline(f,[event(2,90,extra=5)])
        self.assertIsNotNone(goals)
        self.assertTrue(settle_entry(1,goals)['anyGoalAfter70'])
    def test_missing_events_not_counted_as_no_goals(self):
        self.assertEqual(goal_timeline(fixture(),[])[1],'goal_events_do_not_match_score')
    def test_extra_time_and_penalty_miss_excluded(self):
        f=fixture(hg=0,ag=0)
        goals,_=goal_timeline(f,[event(2,105),event(1,80,'Missed Penalty')])
        self.assertEqual(goals,[])
    def test_own_goal_credit_can_be_reconciled(self):
        goals,state=goal_timeline(fixture(),[event(1,80,'Own Goal')])
        self.assertEqual(goals[0]['teamId'],2)
        self.assertEqual(state,'validated_own_goal_reassigned')
    def test_future_result_does_not_enter_reconstructed_table(self):
        current=fixture(home=1,away=7)
        past=[fixture(id=i,home=i,away=7,hg=1,ag=0,at='2026-09-01T18:00:00+00:00') for i in range(1,7)]
        future=fixture(id=100,home=7,away=1,hg=50,ag=0,at='2026-10-11T18:00:00+00:00')
        rank,state,band=reconstructed_rank(current,past+[current,future],7)
        self.assertEqual(state,'outside_top5_reconstructed')
        self.assertEqual(rank,7)
    def test_complex_phase_is_not_fabricated(self):
        current=fixture(phase='Championship Round')
        self.assertEqual(reconstructed_rank(current,[],2)[1],'complex_phase')
    def test_conference_is_not_treated_as_global_table(self):
        current=fixture()
        current['league']['id']=253
        self.assertEqual(reconstructed_rank(current,[],2)[1],'conference_table')
    def test_apertura_knockout_not_treated_as_regular_table(self):
        current=fixture()
        current['league']['round']='Apertura - Quarter-finals'
        self.assertEqual(reconstructed_rank(current,[],2)[1],'complex_phase')
    def test_overlapping_game_result_not_used_if_rank_is_already_clear(self):
        current=fixture(home=1,away=7)
        past=[fixture(id=i,home=i,away=7,hg=1,ag=0,at='2026-09-01T18:00:00+00:00') for i in range(1,7)]
        overlap=fixture(id=99,home=1,away=2,hg=100,ag=0,at='2026-10-10T16:00:00+00:00')
        rank,status,band=reconstructed_rank(current,past+[current,overlap],7)
        self.assertEqual(status,'outside_top5_reconstructed')
        self.assertEqual(band,[7,7])
    def test_phantom_first_half_goal_requires_full_score_reconciliation(self):
        f=fixture(hg=2,ag=1)
        f['score']['halftime']={'home':0,'away':0}
        goals,state=goal_timeline(f,[event(1,45),event(2,52),event(1,55),event(1,63)])
        self.assertEqual(state,'validated_scoreless_halftime_reconciliation')
        self.assertEqual([g['minute'] for g in goals],[52,55,63])
        self.assertFalse(settle_entry(1,goals)['entry'])

if __name__=='__main__':unittest.main()
