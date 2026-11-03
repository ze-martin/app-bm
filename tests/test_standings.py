import unittest
from datetime import datetime, timedelta, timezone
from scripts.standings import api_ranks, resolve_rank

class Standings(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,3,18,tzinfo=timezone.utc)
        self.fixture={'fixture':{'id':10},'league':{'id':281,'season':2026,'round':'Clausura - 15'}}
        self.check={'fixtureId':10,'teamId':42,'leagueId':281,'season':2026,'phase':'Clausura',
            'checkedAt':self.now.isoformat(),'sources':[
                {'url':'https://www.fotmob.com/leagues/131/table/liga-1','rank':13,'row':'13 Comerciantes Unidos 14 PJ 14 pts','method':'visual-scroll'},
                {'url':'https://www.futbolperuano.com/liga-1/clausura/tabla-de-posiciones','rank':13,'row':'13 Comerciantes Unidos 14 PJ 14 pts','method':'visual-scroll'}]}
    def resolve(self, check=None, rank=None):
        return resolve_rank(self.fixture,42,rank,[self.check if check is None else check],self.now)
    def test_phase_selected_instead_of_mixing_ranks(self):
        tables=[{'league':{'standings':[
            [{'team':{'id':42},'group':'Primera Division: Apertura','rank':9}],
            [{'team':{'id':42},'group':'Primera Division: Clausura','rank':13}]]}}]
        self.assertEqual(api_ranks(tables,self.fixture),{42:13})
        self.fixture['league']['round']='Unknown - 1'
        self.assertEqual(api_ranks(tables,self.fixture),{})
    def test_valid_evidence_supplies_missing_rank(self):
        rank, meta=self.resolve()
        self.assertEqual((rank,meta['status']),(13,'verified'))
    def test_single_annual_table_does_not_replace_clausura(self):
        tables=[{'league':{'standings':[[{'team':{'id':42},'group':'Tabla Anual','rank':13}]]}}]
        self.assertEqual(api_ranks(tables,self.fixture),{})
    def test_sources_disagree_never_qualify(self):
        self.check['sources'][1]['rank']=14
        self.assertEqual(self.resolve()[1]['status'],'conflict')
        self.assertIsNone(self.resolve()[0])
    def test_api_and_web_conflict(self):
        self.assertIsNone(self.resolve(rank=4)[0])
    def test_expired_does_not_supply_rank(self):
        self.check['checkedAt']=(self.now-timedelta(hours=25)).isoformat()
        self.assertEqual(self.resolve()[1]['status'],'expired')
        self.assertIsNone(self.resolve()[0])
    def test_wrong_phase_rejected(self):
        self.check['phase']='Apertura'
        self.assertEqual(self.resolve()[1]['status'],'invalid')
    def test_one_domain_is_not_two_sources(self):
        self.check['sources'][1]['url']='https://fotmob.com/another'
        self.assertEqual(self.resolve()[1]['status'],'invalid')
    def test_wrong_team_not_applied(self):
        self.check['teamId']=99
        self.assertIsNone(self.resolve()[0])
    def test_future_check_rejected(self):
        self.check['checkedAt']=(self.now+timedelta(hours=1)).isoformat()
        self.assertIsNone(self.resolve()[0])

if __name__=='__main__':
    unittest.main()
