import unittest
from scripts.tracking_history import ingest

class TrackingHistory(unittest.TestCase):
    def snapshot(self,stamp):
        return {'updatedAt':stamp,'matches':[{'fixture':{'fixture':{'id':1,'date':'2026-11-03T20:00:00+00:00'},'teams':{'home':{'name':'A'},'away':{'name':'B'}}},'selections':[{'prequalified':True,'teamId':2,'team':'B'}]}]}

    def test_recovery_does_not_invent_notice_or_bet(self):
        data={'records':[]}
        ingest(data,self.snapshot('2026-11-03T19:00:00+00:00'))
        r=data['records'][0]
        self.assertTrue(r['pregameEvidence'])
        self.assertIsNone(r['notice'])
        self.assertEqual(r['bet'],'not_recorded')
        r['result']={'status':'settled'}
        ingest(data,self.snapshot('2026-11-04T19:00:00+00:00'))
        self.assertEqual(len(data['records']),1)
        self.assertEqual(r['result']['status'],'settled')

    def test_post_kickoff_snapshot_is_not_pregame_evidence(self):
        data={'records':[]}
        ingest(data,self.snapshot('2026-11-04T19:00:00+00:00'))
        self.assertFalse(data['records'][0]['pregameEvidence'])
        ingest(data,self.snapshot('2026-11-03T19:00:00+00:00'))
        self.assertTrue(data['records'][0]['pregameEvidence'])
