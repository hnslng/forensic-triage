"""Live loopback HTTP checks for the new route boundary; synthetic data only."""
import http.client
import json
import threading
from pathlib import Path

import pytest

from forensic_triage.web import TriageHTTPServer
from test_metadata_analysis import fixture


@pytest.fixture
def api(tmp_path,monkeypatch):
    store,medium,source=fixture(tmp_path)
    monkeypatch.setenv('FORENSIC_TRIAGE_SETTINGS_ROOT',str(tmp_path/'settings'))
    monkeypatch.setenv('FORENSIC_TRIAGE_RELEASES_ROOT',str(tmp_path/'none'))
    monkeypatch.setenv('FORENSIC_TRIAGE_UPDATE_GUARD_FILE',str(tmp_path/'guard'))
    import forensic_triage.web as web
    monkeypatch.setattr(web,'discover_media_devices',lambda:pytest.fail('Metadata routes must not discover/open devices'))
    repo=Path(__file__).resolve().parents[1]
    server=TriageHTTPServer(('127.0.0.1',0),repo/'web',tmp_path/'unused-results',repo/'profiles/default.yaml',store.root,180,15)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    host=f'127.0.0.1:{server.server_port}'
    def call(method,path,payload=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=15)
        values={'Host':host}
        if payload is not None:values['Content-Type']='application/json'
        values.update(headers or {})
        connection.request(method,path,body=None if payload is None else json.dumps(payload),headers=values)
        response=connection.getresponse();body=response.read();status=response.status;connection.close()
        try:return status,json.loads(body)
        except ValueError:return status,body
    yield call,medium,source,host
    server.shutdown();server.server_close();thread.join(5)


def test_live_metadata_flow_and_browser_boundary(api):
    call,medium,source,host=api
    code,context=call('GET','/api/evaluation-context');assert code==200
    headers={'X-Triage-CSRF':context['csrf_token'],'Origin':'http://'+host,'Sec-Fetch-Site':'same-origin'}
    route=f'/api/cases/SYNTH/media/{medium}/period-evaluations'
    payload={'operator':'TEST','date_from':'2024-01-01','date_to':'2024-12-31','timezone':'UTC'}
    for bad in ({},{'X-Triage-CSRF':'wrong'},{'X-Triage-CSRF':'ä'},{**headers,'Origin':'https://evil.invalid'}, {**headers,'Content-Type':'text/plain'}, {**headers,'Sec-Fetch-Site':'cross-site'},{**headers,'Host':'attacker.invalid'}):
        assert call('POST',route,payload,bad)[0]==403
    assert call('GET','/api/evaluation-context',headers={'Host':'attacker.invalid'})[0]==403
    assert call('GET',f'/api/media/{medium}/analysis',headers={'Origin':'null'})[0]==403
    assert call('POST',route,{**payload,'path':'/etc/passwd'},headers)[0]==400
    assert call('POST',route.replace('SYNTH','OTHER'),payload,headers)[0]==404
    assert call('POST',route,{**payload,'timezone':'local'},headers)[0]==400
    assert call('POST',route,{**payload,'date_from':'2024-02-30'},headers)[0]==400
    code,result=call('POST',route,payload,headers);assert code==201
    identity=result['evaluation_id']
    code,selected=call('GET',f'/api/media/{medium}/analysis?evaluation_id={identity}');assert code==200
    assert selected['statistics']['in_period']==5 and selected['statistics']['undetermined']==1
    code,listing=call('GET',route);assert code==200 and len(listing['evaluations'])==1
    code,files=call('GET',f'/api/media/{medium}/files?analysis_view=1&evaluation_id={identity}&period_filter=in&keyword=Rechnung&category=Dokumente&originals_only=1&limit=1');assert code==200
    assert files['total']==2 and len(files['files'])==1 and files['has_more']
    assert call('GET',f'/api/media/{medium}/analysis?evaluation_id=../../etc/passwd')[0]==400
    assert call('GET',f'/api/media/{medium}/files?analysis_view=1&source_filter=invalid')[0]==400
    (source/'files.csv').write_text('path,size\nchanged,1\n')
    assert call('GET',f'/api/media/{medium}/analysis?evaluation_id={identity}')[0]==400


def test_early_year_requires_real_confirmation(api):
    call,medium,_,_=api;_,context=call('GET','/api/evaluation-context');h={'X-Triage-CSRF':context['csrf_token']}
    path=f'/api/cases/SYNTH/media/{medium}/period-evaluations'
    p={'operator':'TEST','date_from':'0202-01-01','date_to':'0202-12-31','timezone':'UTC'}
    assert call('POST',path,p,h)[0]==400
    assert call('POST',path,{**p,'date_warning_acknowledged':'true'},h)[0]==400
    assert call('POST',path,{**p,'date_warning_acknowledged':True},h)[0]==201


def test_oversize_identifiers_are_cleanly_rejected(api):
    call,_,_,_=api
    huge='9'*80
    assert call('GET',f'/api/media/{huge}/analysis')[0]==400
    assert call('GET',f'/api/media/{huge}/files?analysis_view=1')[0]==400


def test_http_zip_contains_both_committed_versions_and_verified_originals(api):
    import hashlib
    import io
    import zipfile
    from test_metadata_analysis import hashes
    call,medium,source,_=api;before=hashes(source)
    _,context=call('GET','/api/evaluation-context');headers={'X-Triage-CSRF':context['csrf_token']}
    route=f'/api/cases/SYNTH/media/{medium}/period-evaluations'
    versions=[]
    for year in (2024,2025):
        code,result=call('POST',route,{'operator':'TEST','date_from':f'{year}-01-01','date_to':f'{year}-12-31','timezone':'UTC'},headers)
        assert code==201;versions.append(result)
    case=next(p for p in source.parents if p.name=='SYNTH');base=case/'period-evaluations'/str(medium)
    (base/'.evaluation-unfinished.tmp').write_text('unfinished')
    (base/('f'*32+'.sqlite3')).write_text('not committed')
    code,body=call('GET','/api/cases/SYNTH/export.zip');assert code==200
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        names=archive.namelist();assert not any('unfinished' in x or 'f'*32 in x for x in names)
        for result in versions:
            name=f'TRIAGE-SYNTH/period-evaluations/{medium}/{result["evaluation_id"]}.sqlite3'
            assert hashlib.sha256(archive.read(name)).hexdigest()==result['evaluation_sha256']
        for line in archive.read('TRIAGE-SYNTH/manifest.sha256').decode().splitlines():
            digest,name=line.split('  ',1)
            assert hashlib.sha256(archive.read('TRIAGE-SYNTH/'+name)).hexdigest()==digest
        text=archive.read('TRIAGE-SYNTH/case-report.txt').decode()
        assert 'NACHTRÄGLICHE ZEITRAUMAUSWERTUNGEN (ORIGINALSCAN UNVERÄNDERT)' in text
        assert all(result['evaluation_id'] in text for result in versions)
    code,pdf=call('GET','/api/cases/SYNTH/report.pdf');assert code==200 and pdf.startswith(b'%PDF-')
    assert hashes(source)==before
