import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from scripts.telegram_monitor import should_alert, should_capture, message
from scripts import telegram_monitor as monitor

class TelegramRules(unittest.TestCase):
    def setUp(self):
        self.selection={'prequalified':True,'teamId':1,'team':'ADT'}
        self.fixture={'fixture':{'id':10,'status':{'short':'2H','elapsed':65}},
            'teams':{'home':{'id':2,'name':'Comerciantes'},'away':{'id':1,'name':'ADT'}},
            'goals':{'home':1,'away':0}}
    def test_real_minute_65_and_zero_goals(self):
        self.assertTrue(should_alert(self.selection,self.fixture))
        self.assertIn('faltan aproximadamente 5',message(self.selection,self.fixture))
    def test_already_scored_no_alert(self):
        self.fixture['goals']['away']=1
        self.assertFalse(should_alert(self.selection,self.fixture))
    def test_unknown_score_no_alert(self):
        self.fixture['goals']['away']=None
        self.assertFalse(should_alert(self.selection,self.fixture))
    def test_before_65_and_at_70_no_early_alert(self):
        for minute in [64,70,76,None]:
            self.fixture['fixture']['status']['elapsed']=minute
            self.assertFalse(should_alert(self.selection,self.fixture))
    def test_late_poll_reports_real_minute(self):
        self.fixture['fixture']['status']['elapsed']=66
        self.assertTrue(should_alert(self.selection,self.fixture))
        self.assertIn('minuto 66',message(self.selection,self.fixture))
        self.assertIn('aproximadamente 4',message(self.selection,self.fixture))
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
    def test_65_notice_does_not_create_70_capture(self):
        self.assertFalse(should_capture(self.selection,self.fixture))
    def test_70_capture_does_not_send_late_65_notice(self):
        self.fixture['fixture']['status']['elapsed']=70
        self.assertTrue(should_capture(self.selection,self.fixture))
        self.assertFalse(should_alert(self.selection,self.fixture))
    def test_65_sends_once_without_creating_70_snapshot(self):
        now=datetime.now(monitor.TZ)
        self.fixture['fixture']['date']=(now-timedelta(minutes=90)).isoformat()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data').mkdir()
            (root/'data/matches.json').write_text(json.dumps({'updatedAt':now.isoformat(),'matches':[{'fixture':self.fixture,'selections':[self.selection]}]}),encoding='utf-8')
            with patch.object(monitor,'ROOT',root),patch.dict(monitor.os.environ,{'FOOTBALL_API_KEY':'test','TELEGRAM_BOT_TOKEN':'test','TELEGRAM_CHAT_ID':'test'}),patch.object(monitor,'fetch_live',return_value=[self.fixture]),patch.object(monitor,'fetch_statistics',return_value=None),patch.object(monitor,'telegram') as send,patch.object(monitor,'save_observation') as capture:
                monitor.run_once()
                monitor.run_once()
                self.assertEqual(send.call_count,1)
                capture.assert_not_called()
                self.assertIn('10:1:65',json.loads((root/'.cache/telegram-sent.json').read_text()))
    def test_70_captures_even_after_65_notice(self):
        now=datetime.now(monitor.TZ)
        self.fixture['fixture']['date']=(now-timedelta(minutes=90)).isoformat()
        self.fixture['fixture']['status']['elapsed']=70
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data').mkdir();(root/'.cache').mkdir()
            (root/'data/matches.json').write_text(json.dumps({'updatedAt':now.isoformat(),'matches':[{'fixture':self.fixture,'selections':[self.selection]}]}),encoding='utf-8')
            (root/'.cache/telegram-sent.json').write_text(json.dumps({'10:1:65':now.isoformat()}))
            with patch.object(monitor,'ROOT',root),patch.dict(monitor.os.environ,{'FOOTBALL_API_KEY':'test','TELEGRAM_BOT_TOKEN':'test','TELEGRAM_CHAT_ID':'test'}),patch.object(monitor,'fetch_live',return_value=[self.fixture]),patch.object(monitor,'fetch_statistics',return_value=None),patch.object(monitor,'telegram') as send,patch.object(monitor,'save_observation',return_value=({'observations':[]},True)) as capture:
                monitor.run_once()
                send.assert_not_called()
                capture.assert_called_once()

if __name__=='__main__':
    unittest.main()
