import unittest
from datetime import datetime,timezone
from scripts.audit_leagues import build_audit,REQUIRED

class LeagueAudit(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,3,tzinfo=timezone.utc)
        self.config={'leagues':[{'id':i,'name':c} for i,c in REQUIRED.items()]}
        self.catalog=[{'league':{'id':i,'name':str(i),'type':'Cup' if i in {2,3,848} else 'League'},
            'country':{'name':c},'seasons':[{'year':2026,'coverage':{}}]} for i,c in REQUIRED.items()]
    def test_paraguay_both_top_division_tournaments_required(self):
        self.config['leagues']=[l for l in self.config['leagues'] if l['id']!=252]
        with self.assertRaisesRegex(ValueError,'252'):build_audit(self.config,self.catalog,self.now)
    def test_paraguay_second_division_not_required(self):
        self.assertNotIn(251,REQUIRED)
        self.assertNotIn(270,REQUIRED)
        self.assertEqual(build_audit(self.config,self.catalog,self.now)['total'],49)
    def test_conference_league_is_required_as_a_cup(self):
        self.assertEqual(REQUIRED[848],'World')
        self.config['leagues']=[l for l in self.config['leagues'] if l['id']!=848]
        with self.assertRaisesRegex(ValueError,'848'):build_audit(self.config,self.catalog,self.now)
    def test_wrong_country_is_blocked(self):
        self.catalog[0]['country']['name']='Other'
        with self.assertRaises(ValueError):build_audit(self.config,self.catalog,self.now)
    def test_missing_current_season_is_blocked(self):
        self.catalog[0]['seasons']=[{'year':2025}]
        with self.assertRaises(ValueError):build_audit(self.config,self.catalog,self.now)
    def test_duplicate_league_is_blocked(self):
        self.config['leagues'].append(self.config['leagues'][0])
        with self.assertRaises(ValueError):build_audit(self.config,self.catalog,self.now)

if __name__=='__main__':unittest.main()
