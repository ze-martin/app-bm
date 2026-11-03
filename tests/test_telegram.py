import unittest
from datetime import datetime, timezone
from scripts.telegram_monitor import should_alert, message

class TelegramRules(unittest.TestCase):
    def setUp(self):
        self.selection={'prequalified':True,'teamId':1,'team':'ADT'}
        self.fixture={'fixture':{'id':10,'status':{'short':'2H','elapsed':70}},
            'teams':{'home':{'id':2,'name':'Comerciantes'},'away':{'id':1,'name':'ADT'}},
            'goals':{'home':1,'away':0}}
    def test_real_minute_70_and_zero_goals(self):
        self.assertTrue(should_alert(self.selection,self.fixture))
    def test_already_scored_no_alert(self):
        self.fixture['goals']['away']=1
        self.assertFalse(should_alert(self.selection,self.fixture))
    def test_unknown_score_no_alert(self):
        self.fixture['goals']['away']=None
        self.assertFalse(should_alert(self.selection,self.fixture))
    def test_before_70_and_after_75_no_alert(self):
        for minute in [69,76,None]:
            self.fixture['fixture']['status']['elapsed']=minute
            self.assertFalse(should_alert(self.selection,self.fixture))
    def test_late_poll_reports_real_minute(self):
        self.fixture['fixture']['status']['elapsed']=72
        self.assertTrue(should_alert(self.selection,self.fixture))
        self.assertIn('minuto 72',message(self.selection,self.fixture))
    def test_stopped_or_finished_no_alert(self):
        for status in ['FT','HT','SUSP','PST','ET']:
            self.fixture['fixture']['status']['short']=status
            self.assertFalse(should_alert(self.selection,self.fixture))
    def test_unqualified_no_alert(self):
        self.selection['prequalified']=False
        self.assertFalse(should_alert(self.selection,self.fixture))
    def test_wrong_team_no_alert(self):
        self.selection['teamId']=99
        self.assertFalse(should_alert(self.selection,self.fixture))
    def test_expired_external_standings_no_alert(self):
        self.selection['rankVerification']={'status':'verified','checkedAt':'2026-11-01T12:00:00+00:00'}
        self.assertFalse(should_alert(self.selection,self.fixture,datetime(2026,11,3,tzinfo=timezone.utc)))

if __name__=='__main__':
    unittest.main()
