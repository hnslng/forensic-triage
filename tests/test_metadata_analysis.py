"""Synthetic Phase-2 acceptance references. No real case data or media."""
import csv
import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from forensic_triage.casefiles import CaseStore
from forensic_triage.period import period_input_warnings, validate_period_submission


def epoch(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()


def fixture(tmp_path, status='partial', period=None):
    store=CaseStore(tmp_path/'cases');store.start_case('SYNTH','TEST')
    root=store.scan_root('SYNTH','SICHT-001')/'2026-01-01T120000Z_SICHT-001';root.mkdir(parents=True)
    rows=[
        {'path':'wallet/a.txt','category':'Dokumente','atime':epoch('2024-06-01T12:00:00Z'),'crtime':epoch('2023-01-01T00:00:00Z'),'mtime':epoch('2025-01-01T00:00:00Z')},
        {'path':'wallet.txt','category':'Dokumente','crtime':epoch('2024-01-01T00:00:00Z'),'mtime':epoch('2024-12-31T23:59:59Z')},
        {'path':'box.zip','category':'Archive','mtime':epoch('2023-06-01T00:00:00Z')},
        {'path':'missing.txt','mtime':'nan','ctime':'1e100'},
        {'path':'wallet/wallet-zero.txt','crtime':0},
        {'path':'boundary.txt','mtime':epoch('2024-01-01T00:00:00Z')},
        {'path':'future.txt','atime':epoch('2027-01-01T00:00:00Z')},
        {'path':'Rechnung.txt','partition_slot':'001','category':'Dokumente','mtime':epoch('2024-03-01T00:00:00Z')},
        {'path':'Rechnung.txt','partition_slot':'002','category':'Dokumente','mtime':epoch('2024-03-01T00:00:00Z')},
    ]
    for r in rows:r.setdefault('partition_slot','001');r.setdefault('size',10);r.setdefault('category','Text/Logs')
    with (root/'files.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','partition_slot','size','category','crtime','mtime','ctime','atime']);w.writeheader();w.writerows(rows)
    (root/'summary.json').write_text(json.dumps({'file_count':9,'directory_count':2,'keyword_matches':6,'scan_status':status,'scan_mode':'fast','scan_started_utc':'2026-01-01T120000Z','case_period':period}))
    (root/'device.json').write_text('{"path":"/dev/SYNTHETIC-NOT-OPENED"}')
    (root/'partitions.json').write_text('[]')
    (root/'hits.json').write_text(json.dumps({'total_matches':6,'profile':{'version':'1.0','sha256':'historic','selected_keywords':['wallet','Rechnung','nothit'],'sources':[{'id':'default','version':'1.0','sha256':'historic'}]},'by_keyword':{
        'wallet':{'count':3,'paths':['wallet/a.txt','wallet.txt','wallet/wallet-zero.txt']},
        'Rechnung':{'count':3,'paths':['Rechnung.txt','Rechnung.txt','box.zip › Rechnung.pdf']},'nothit':{'count':0,'paths':[]}}}))
    (root/'container-index.json').write_text(json.dumps({'containers':[{'id':'001:box.zip','path':'box.zip','partition_slot':'001','format':'zip','entries':[{'kind':'file','path':'Rechnung.pdf','size':20,'category':'Dokumente','mtime':epoch('2024-01-01T00:00:00Z')}]}]}))
    media=store.record_scan('SYNTH','SICHT-001','TEST',{'path':'/dev/SYNTHETIC-NOT-OPENED'},root)['media']['id']
    return store,media,root


def evaluate(store, media, **kwargs):
    return store.create_period_evaluation('SYNTH',media,'TEST',kwargs.get('start','2024-01-01'),kwargs.get('end','2024-12-31'),kwargs.get('zone','UTC'))


def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def test_exact_2024_statistics_and_immutable_versions(tmp_path,monkeypatch):
    store,media,root=fixture(tmp_path);before=hashes(root)
    import subprocess
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('No process, mount or device access allowed'))
    first=evaluate(store,media);stats=first['statistics']
    assert (stats['files_total'],stats['in_period'],stats['out_of_period'],stats['undetermined'])==(9,5,3,1)
    assert stats['without_timestamps']==1 and stats['multiple_matches']==1
    assert {k:v['matched'] for k,v in stats['by_type'].items()}=={'B':1,'M':4,'C':0,'A':1}
    assert {k:v['exclusive'] for k,v in stats['by_type'].items()}=={'B':0,'M':3,'C':0,'A':1}
    assert stats['by_type']['B']['zero_epoch']==1
    assert stats['by_type']['A']['after_scan']==1
    assert stats['by_type']['M']['invalid']==1 and stats['by_type']['C']['invalid']==1
    assert stats['source_scan_status']=='partial' and 'Weitere Dateien können vorhanden sein' in stats['scope_notice']
    second=evaluate(store,media,start='2025-01-01',end='2025-12-31')
    assert first['evaluation_id']!=second['evaluation_id']
    assert len(store.list_period_evaluations(media))==2
    assert store.period_analysis(media,first['evaluation_id'])['statistics']==first['statistics']
    assert hashes(root)==before
    events=[json.loads(x) for x in (store.case_path('SYNTH')/'audit.log').read_text().splitlines()]
    new=[x for x in events if x['event_type']=='period_evaluation_created'];assert len(new)==2
    assert new[0]['details']['source_csv_sha256']==before['files.csv']


def test_keyword_identity_sources_archives_and_combined_paging(tmp_path):
    store,media,_=fixture(tmp_path);ev=evaluate(store,media);kw=ev['keyword_statistics']
    assert kw['stored_total_matches']==kw['path_assignments']==6
    assert kw['unique_original_files']==3 and kw['unique_virtual_entries']==1
    assert kw['terms_with_hits']==2 and kw['unique_counts_are_lower_bounds']
    assert kw['sources']=={'folder':1,'filename':1,'both':1,'ambiguous':2,'virtual':1}
    assert [t['term'] for t in kw['terms']]==['wallet','Rechnung','nothit']
    assert kw['historical_profile']['version']=='1.0'
    result=store.file_inventory(media,evaluation_id=ev['evaluation_id'],period_filter='in',category='Dokumente',keyword='Rechnung',originals_only=True,limit=1,sort_by='path')
    assert result['total']==2 and result['has_more']
    next_page=store.file_inventory(media,evaluation_id=ev['evaluation_id'],period_filter='in',category='Dokumente',keyword='Rechnung',originals_only=True,limit=1,offset=1,sort_by='path')
    assert result['files'][0]['partition_slot']!=next_page['files'][0]['partition_slot']
    assert result['files'][0]['keyword_ambiguous']
    virtual=store.file_inventory(media,evaluation_id=ev['evaluation_id'],source_filter='virtual',period_filter='unknown')['files']
    assert len(virtual)==1 and virtual[0]['in_period'] is None and virtual[0]['mtime'] is None
    assert virtual[0]['period_notice']=='Zeitraum nicht eigenständig bestimmbar'
    assert store.file_inventory(media,evaluation_id=ev['evaluation_id'],timestamp_filter='exclusive:A')['total']==1
    assert store.file_inventory(media,evaluation_id=ev['evaluation_id'],timestamp_filter='multiple')['total']==1
    assert store.file_inventory(media,evaluation_id=ev['evaluation_id'],period_filter='out')['total']==3
    assert store.file_inventory(media,evaluation_id=ev['evaluation_id'],period_filter='unknown',originals_only=True)['total']==1


def test_original_without_period_and_tampered_snapshot(tmp_path):
    store,media,root=fixture(tmp_path)
    original=store.period_analysis(media)
    assert original['statistics']['undetermined']==9 and original['statistics']['in_period']==0
    ev=evaluate(store,media)
    data=(root/'device.json').read_bytes();(root/'device.json').write_bytes(data+b' ')
    with pytest.raises(ValueError,match='verändert'):store.period_analysis(media,ev['evaluation_id'])
    with pytest.raises(ValueError):store.file_inventory(media,evaluation_id='../outside')
    with pytest.raises(KeyError):store.create_period_evaluation('OTHER',media,'TEST','2024-01-01','2024-12-31','UTC')


@pytest.mark.parametrize('status',['partial','failed','unknown'])
def test_original_quality_survives_reevaluation(tmp_path,status):
    store,media,_=fixture(tmp_path,status)
    assert evaluate(store,media)['statistics']['source_scan_status']==status


def test_no_inventory_is_not_a_normal_empty_result(tmp_path):
    store,media,root=fixture(tmp_path);(root/'files.csv').unlink()
    with pytest.raises(ValueError,match='Kein auswertbares'):evaluate(store,media)
    assert store.list_period_evaluations(media)==[]


def test_symlinks_and_empty_or_invalid_zones_are_rejected(tmp_path):
    store,media,root=fixture(tmp_path)
    for zone in ('','local','../etc/passwd','not/a-zone'):
        with pytest.raises(ValueError):evaluate(store,media,zone=zone)
    (root/'linked').symlink_to(root/'files.csv')
    with pytest.raises(ValueError,match='Symlinks'):evaluate(store,media)


def test_unusual_dates_require_explicit_boolean_confirmation():
    assert period_input_warnings('0202-01-01','0202-12-31')
    for acknowledged in (False,'true',1):
        with pytest.raises(ValueError):validate_period_submission('0202-01-01','0202-12-31',acknowledged)
    assert validate_period_submission('0202-01-01','0202-12-31',True)==('0202-01-01','0202-12-31')
    assert validate_period_submission('2024-02-29','2024-02-29')
    for a,b in [('20240-01-01','20240-12-31'),('2023-02-29','2023-03-01'),('2024-01-01',''),('2025-01-01','2024-01-01')]:
        with pytest.raises(ValueError):validate_period_submission(a,b,True)


def test_no_replace_on_identifier_collision_and_payload_tampering(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import forensic_triage.casefiles as cases
    store,media,_=fixture(tmp_path)
    monkeypatch.setattr(cases.uuid,'uuid4',lambda:SimpleNamespace(hex='a'*32))
    first=evaluate(store,media)
    saved=store._evaluation_root(store._analysis_context(media)[0])/('a'*32+'.sqlite3')
    before=saved.read_bytes()
    with pytest.raises(FileExistsError):evaluate(store,media,start='2025-01-01',end='2025-12-31')
    assert saved.read_bytes()==before and len(store.list_period_evaluations(media))==1
    saved.write_bytes(before+b'tampered')
    with pytest.raises(ValueError,match='Auswertung verändert'):store.period_analysis(media,first['evaluation_id'])


@pytest.mark.parametrize('zone,start,end,stamp,inside',[
    ('Europe/Vienna','2024-03-31','2024-03-31','2024-03-30T23:00:00Z',True),
    ('Europe/Vienna','2024-03-31','2024-03-31','2024-03-31T22:00:00Z',False),
    ('Europe/Vienna','2024-10-27','2024-10-27','2024-10-27T00:30:00Z',True),
    ('Europe/Vienna','2024-10-27','2024-10-27','2024-10-27T01:30:00Z',True),
    ('America/New_York','2024-01-01','2024-01-01','2024-01-02T04:59:59Z',True),
    ('Asia/Tokyo','2024-01-01','2024-01-01','2023-12-31T14:59:59Z',False),
])
def test_saved_evaluations_use_explicit_local_days_and_dst(tmp_path,zone,start,end,stamp,inside):
    store,media,root=fixture(tmp_path)
    (root/'files.csv').write_text('path,size,mtime\nboundary.txt,1,'+str(epoch(stamp))+'\n')
    result=evaluate(store,media,start=start,end=end,zone=zone)
    assert result['statistics']['files_total']==1
    assert result['statistics']['in_period']==int(inside)
    assert result['statistics']['out_of_period']==int(not inside)


def test_uncertain_historical_zone_uses_saved_assignments_only(tmp_path,monkeypatch):
    period={'date_from':'2024-01-01','date_to':'2024-12-31','timezone':'local','timezone_reproducible':False}
    store,media,root=fixture(tmp_path,period=period)
    (root/'files.csv').write_text('path,size,mtime,in_period,period_matches\nsaved.txt,1,1,True,M\n')
    monkeypatch.setenv('TZ','Asia/Tokyo')
    original=store.period_analysis(media)
    assert original['statistics']['timezone_uncertain']
    assert original['statistics']['in_period']==1
    new=evaluate(store,media)
    assert new['statistics']['out_of_period']==1 and new['period']['timezone']=='UTC'


def test_limits_leave_no_registered_or_staged_version(tmp_path,monkeypatch):
    import forensic_triage.metadata_analysis as analysis
    store,media,root=fixture(tmp_path);before=hashes(root)
    monkeypatch.setattr(analysis,'MAX_ROWS',2)
    with pytest.raises(ValueError,match='Limit|limit'):evaluate(store,media)
    assert store.list_period_evaluations(media)==[] and hashes(root)==before
    assert not list(store.case_path('SYNTH').rglob('*.tmp'))


def test_exports_keep_legacy_scan_records_and_exclude_uncommitted_versions(tmp_path):
    store,medium,root=fixture(tmp_path)
    case=store.case_path('SYNTH')
    record=next((case/'media'/'SICHT-001'/'records').glob('*.json'))
    record.write_text('{"legacy":"do not replace"}\n')
    before=record.read_bytes();original=hashes(root)
    result=evaluate(store,medium)
    base=store._evaluation_root(store._analysis_context(medium)[0])
    (base/'.evaluation-incomplete.tmp').write_text('not exported')
    (base/('f'*32+'.sqlite3')).write_text('uncommitted crash orphan')
    (base/'linked.sqlite3').symlink_to(root/'files.csv')
    store.refresh_exports('SYNTH')
    exported={str(p.relative_to(case)) for p in store.exportable_files(case)}
    assert any(result['evaluation_id'] in name for name in exported)
    assert not any('incomplete' in name or 'f'*32 in name or 'linked' in name for name in exported)
    manifest=(case/'manifest.sha256').read_text()
    assert result['evaluation_id'] in manifest and '.tmp' not in manifest
    assert record.read_bytes()==before and hashes(root)==original
    text=(case/'case-report.txt').read_text()
    assert 'NACHTRÄGLICHE ZEITRAUMAUSWERTUNGEN' in text and result['source_csv_sha256'] in text


@pytest.mark.parametrize('name,value',[('hits.json',[]),('hits.json',{'profile':[]}),('hits.json',{'by_keyword':{'bad':1}}),('summary.json',[]),('partitions.json',{})])
def test_invalid_metadata_shapes_fail_without_publishing(tmp_path,name,value):
    store,media,root=fixture(tmp_path)
    # Nonempty invalid profile tests the type boundary, not the empty fallback.
    if value=={'profile':[]}:value={'profile':['invalid']}
    (root/name).write_text(json.dumps(value));before=hashes(root)
    with pytest.raises(ValueError):evaluate(store,media)
    assert hashes(root)==before and store.list_period_evaluations(media)==[]


def test_new_profile_is_never_loaded_for_historical_keywords(tmp_path,monkeypatch):
    import forensic_triage.keywords as keywords
    store,media,source=fixture(tmp_path)
    current=tmp_path/'settings'/'profiles';current.mkdir(parents=True)
    (current/'default.yaml').write_text('version: "1.1"\nkeywords: [NEW_TERM]\n')
    monkeypatch.setattr(keywords,'load_profile',lambda *a,**k:pytest.fail('Current profile must not be read'))
    before=hashes(source);result=evaluate(store,media)
    assert result['keyword_statistics']['historical_profile']['version']=='1.0'
    assert [x['term'] for x in result['keyword_statistics']['terms']]==['wallet','Rechnung','nothit']
    assert hashes(source)==before


@pytest.mark.parametrize('year',['0202','2062','9999'])
def test_rare_years_remain_possible_with_confirmation(year):
    start,end=f'{year}-01-01',f'{year}-12-31'
    with pytest.raises(ValueError):validate_period_submission(start,end)
    assert validate_period_submission(start,end,True)==(start,end)
