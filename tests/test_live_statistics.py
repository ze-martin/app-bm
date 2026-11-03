import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from scripts.live_statistics import normalize_stats, statistics_text, save_observation

class Statistics(unittest.TestCase):
    def setUp(self):
        self.f={'fixture':{'id':8,'status':{'elapsed':71}},'teams':{'home':{'id':1,'name':'Local'},'away':{'id':2,'name':'Visita'}},'goals':{'home':1,'away':0}}
        self.payload={'response':[
            {'team':{'id':2},'statistics':[{'type':'Ball Possession','value':'60%'},{'type':'Total Shots','value':9}],
                'statistics_2h':[{'type':'Ball Possession','value':'65%'},{'type':'Corner Kicks','value':0},{'type':'Shots on Goal','value':2}]},
            {'team':{'id':1},'statistics':[{'type':'Ball Possession','value':'40%'}],'statistics_2h':[]}]}
    def test_map_by_team_id_not_response_order(self):
        stats=normalize_stats(self.payload,self.f)
        self.assertEqual(stats['away']['total']['shots'],9)
        self.assertEqual(stats['home']['total']['possession'],40)
    def test_periods_are_not_mixed(self):
        stats=normalize_stats(self.payload,self.f)
        self.assertEqual(stats['away']['secondHalf']['possession'],65)
        self.assertIsNone(stats['home']['secondHalf']['possession'])
        self.assertIsNone(stats['away']['secondHalf']['shots'])
    def test_missing_and_zero_are_distinct(self):
        stats=normalize_stats(self.payload,self.f)
        self.assertEqual(stats['away']['secondHalf']['corners'],0)
        self.assertIsNone(stats['home']['secondHalf']['corners'])
        self.assertIn('N/D',statistics_text(stats,self.f))
    def test_invalid_numbers_are_missing(self):
        self.payload['response'][0]['statistics']=[{'type':'Ball Possession','value':'120%'},{'type':'Total Shots','value':-1}]
        stats=normalize_stats(self.payload,self.f)
        self.assertIsNone(stats['away']['total']['possession'])
        self.assertIsNone(stats['away']['total']['shots'])
    def test_capture_has_real_minute_and_is_not_duplicated(self):
        stats=normalize_stats(self.payload,self.f)
        now=datetime(2026,11,3,20,tzinfo=timezone.utc)
        selected=[{'teamId':2,'team':'Visita'}]
        with tempfile.TemporaryDirectory() as root:
            first,changed=save_observation(root,self.f,selected,stats,now)
            self.assertTrue(changed)
            self.assertEqual(first['observations'][0]['minute'],71)
            self.f['fixture']['status']['elapsed']=72
            second,changed=save_observation(root,self.f,selected,stats,now)
            self.assertFalse(changed)
            self.assertEqual(second['observations'][0]['minute'],71)
    def test_xg_decimal_and_accuracy(self):
        self.payload['response'][0]['statistics']=[{'type':'expected_goals','value':'1.37'},
            {'type':'Total Shots','value':8},{'type':'Shots on Goal','value':3},{'type':'Red Cards','value':1}]
        stats=normalize_stats(self.payload,self.f)
        self.assertEqual(stats['away']['total']['xG'],1.37)
        self.assertEqual(stats['away']['total']['accuracy'],37.5)
        self.assertIn('expulsiones',statistics_text(stats,self.f))
    def test_zero_shots_does_not_imply_zero_accuracy(self):
        self.payload['response'][0]['statistics']=[{'type':'Total Shots','value':0},{'type':'Shots on Goal','value':0}]
        self.assertIsNone(normalize_stats(self.payload,self.f)['away']['total']['accuracy'])
    def test_more_on_target_than_shots_is_not_valid_accuracy(self):
        self.payload['response'][0]['statistics']=[{'type':'Total Shots','value':1},{'type':'Shots on Goal','value':2}]
        self.assertIsNone(normalize_stats(self.payload,self.f)['away']['total']['accuracy'])

if __name__=='__main__':unittest.main()
