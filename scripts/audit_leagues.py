"""Validate all requested senior men's top leagues against the provider catalog."""
import json
import argparse
from pathlib import Path
try:
    from .refresh import ROOT, TZ, API, load_env
except ImportError:
    from refresh import ROOT, TZ, API, load_env
from datetime import datetime

# Explicit scope. Championship and European cups were requested in addition to top divisions.
REQUIRED={281:'Peru',310:'Albania',78:'Germany',307:'Saudi-Arabia',128:'Argentina',218:'Austria',
    144:'Belgium',116:'Belarus',344:'Bolivia',315:'Bosnia',71:'Brazil',172:'Bulgaria',345:'Czech-Republic',
    265:'Chile',318:'Cyprus',239:'Colombia',162:'Costa-Rica',210:'Croatia',119:'Denmark',242:'Ecuador',
    140:'Spain',179:'Scotland',332:'Slovakia',373:'Slovenia',253:'USA',244:'Finland',197:'Greece',
    39:'England',40:'England',357:'Ireland',383:'Israel',135:'Italy',262:'Mexico',103:'Norway',88:'Netherlands',
    250:'Paraguay',252:'Paraguay',106:'Poland',94:'Portugal',283:'Romania',286:'Serbia',113:'Sweden',
    207:'Switzerland',203:'Turkey',333:'Ukraine',268:'Uruguay',2:'World',3:'World',848:'World'}

def build_audit(config,catalog,now):
    by_id={entry['league']['id']:entry for entry in catalog}
    configured={l['id'] for l in config['leagues']}
    if len(configured)!=len(config['leagues']):
        raise ValueError('Hay identificadores de liga duplicados.')
    missing=set(REQUIRED)-configured
    if missing:
        raise ValueError('Faltan competiciones del alcance solicitado: '+str(sorted(missing)))
    rows=[]
    for item in config['leagues']:
        actual=by_id.get(item['id'])
        if not actual or actual['country']['name']!=REQUIRED.get(item['id']):
            raise ValueError('Identidad o país no válido para '+str(item['id']))
        if actual['league']['type']!=('Cup' if item['id'] in {2,3,848} else 'League'):
            raise ValueError('Tipo de competición inesperado: '+str(item['id']))
        seasons=[s for s in actual['seasons'] if s['year']==now.year]
        if not seasons:
            raise ValueError('No hay temporada del año actual en catálogo para '+str(item['id']))
        season=seasons[0]
        note={250:'Apertura y Clausura usan IDs distintos: se incluyen 250 y 252.',
              252:'Clausura de la primera división; no confundir con División Intermedia (251).',
              268:'En 2026 incluye fases Apertura, Intermedio y Clausura bajo 268; no usar el antiguo 270 sin temporada actual.',
              40:'Segunda división inglesa añadida expresamente por el usuario.'}.get(item['id'],'')
        coverage=season.get('coverage',{})
        rows.append({**item,'country':actual['country']['name'],'officialName':actual['league']['name'],
            'season':season['year'],'status':'verified','providerType':actual['league']['type'],
            'standingsCoverage':coverage.get('standings'),
            'statisticsCoverage':coverage.get('fixtures',{}).get('statistics_fixtures'),
            'note':note})
    return {'checkedAt':now.isoformat(),'source':'API-Football /leagues','competitions':rows,
        'total':len(rows),'note':'Identidad y temporada verificadas. La cobertura declarada no garantiza datos completos para cada partido.'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--env',type=Path)
    args=p.parse_args()
    if args.env:load_env(args.env)
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    catalog=API().get('leagues')['response']
    result=build_audit(config,catalog,datetime.now(TZ))
    (ROOT/'data/league-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Auditoria completa: '+str(result['total'])+' competiciones verificadas.')

if __name__=='__main__':main()
