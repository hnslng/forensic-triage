"""Synthetic regressions for empty/failed/partial inventory and guarded decisions."""
import csv
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from forensic_triage import fast_inventory, scanner
from forensic_triage.casefiles import CaseStore, _scan_summary
from forensic_triage.scan_quality import InventoryErrors, apply_scan_quality, partition_status
from forensic_triage.web import TriageHandler


def result(store, status='partial', device='/dev/synthetic'):
    p = store.scan_root('SYNTH', 'SICHT-001') / '2026-01-01T120000Z_SICHT-001'
    p.mkdir(parents=True)
    (p / 'summary.json').write_text(json.dumps({'file_count': 47, 'directory_count': 38,
        'keyword_matches': 0, 'scan_status': status, 'scan_mode': 'fast', 'duration_seconds': 1}))
    (p / 'hits.json').write_text('{"by_keyword": {}}')
    (p / 'files.csv').write_text('path,size\nsynthetic.txt,1\n')
    (p / 'partitions.json').write_text(json.dumps([{'slot':'002', 'allocated':True,
        'scan_status':'partial' if status == 'partial' else 'ok',
        'read_error_count':26 if status == 'partial' else 0}]))
    return store.record_scan('SYNTH', 'SICHT-001', 'TEST', {'path':device}, p), p


@pytest.mark.parametrize('errors', [1, 26, 1000])
def test_bounded_file_errors_preserve_every_count_and_good_neighbors(tmp_path, monkeypatch, errors):
    (tmp_path / 'a-good.txt').touch(); (tmp_path / 'z-good.txt').touch()
    for i in range(errors): (tmp_path / f'broken-{i}.txt').touch()
    stat = fast_inventory._stat_metadata
    def metadata(p):
        if p.name.startswith('broken'): raise OSError(5, 'Input/output error', str(p))
        return stat(p)
    monkeypatch.setattr(fast_inventory, '_stat_metadata', metadata)
    counter = InventoryErrors()
    files, _ = fast_inventory.inventory_tree(tmp_path, '002', read_errors=counter)
    assert [f['path'] for f in files] == ['a-good.txt','z-good.txt']
    info=counter.snapshot()
    assert info['read_error_count'] == errors
    assert info['read_error_counts'] == {'file':errors,'directory':0,'other':0,'total':errors}
    assert len(info['read_errors']) == min(errors,50)
    assert info['read_errors_truncated'] is (errors>50)
    assert partition_status(info) == 'partial'
    summary={'file_count':2}
    apply_scan_quality(summary,[{'allocated':True,'scan_status':'partial',**info}])
    assert summary['scan_error_count']==errors
    assert len(summary['scan_warnings'][0]['read_errors'])==min(errors,50)
    assert all(not e['path'].startswith('/') for e in info['read_errors'])


def test_synthetic_s33_directory_errors_and_teildata(tmp_path, monkeypatch):
    for i in range(47): (tmp_path/f'good-{i}.txt').touch()
    for i in range(38): (tmp_path/f'directory-{i}').mkdir()
    real_walk=fast_inventory.os.walk
    def walk(root, **kwargs):
        yield next(real_walk(root))
        for i in range(26): kwargs['onerror'](OSError(5,'Input/output error',str(root/f'directory-{i}')))
        for i in range(26,38): yield str(root/f'directory-{i}'),[],[]
    monkeypatch.setattr(fast_inventory.os,'walk',walk)
    counter=InventoryErrors()
    files,directories=fast_inventory.inventory_tree(tmp_path,'002',read_errors=counter)
    assert len(files)==47 and len(directories)==38
    assert counter.snapshot()['read_error_counts']['directory']==26
    assert partition_status(counter.snapshot())=='partial'


@pytest.mark.parametrize('root_failure',[True,False])
def test_wholly_failed_inventory_is_not_empty_or_partial(tmp_path,monkeypatch,root_failure):
    def walk(root,**kwargs):
        if root_failure:
            kwargs['onerror'](OSError(5,'Input/output error',str(root)))
        else:
            yield str(root),[],['unreadable.txt']
    monkeypatch.setattr(fast_inventory.os,'walk',walk)
    monkeypatch.setattr(fast_inventory,'_stat_metadata',lambda p: (_ for _ in ()).throw(OSError(5,'Input/output error',str(p))))
    errors=InventoryErrors();files,dirs=fast_inventory.inventory_tree(tmp_path,'002',read_errors=errors)
    assert files==dirs==[]
    assert partition_status(errors.snapshot())=='failed'
    summary={'file_count':0}
    apply_scan_quality(summary,[{'allocated':True,'scan_status':'partial',**errors.snapshot()}])
    assert summary['scan_status']=='failed'


def test_truly_empty_success_is_complete(tmp_path):
    errors=InventoryErrors()
    assert fast_inventory.inventory_tree(tmp_path,'002',read_errors=errors)==([],[])
    summary={'file_count':0}
    apply_scan_quality(summary,[{'allocated':True,'scan_status':partition_status(errors.snapshot()),**errors.snapshot()}])
    assert summary['scan_status']=='complete'
    assert summary['scan_error_count']==0


def test_unmount_failure_keeps_inventory_and_mountpoint(tmp_path,monkeypatch):
    mount=tmp_path/'mount';mount.mkdir();(mount/'good.txt').touch()
    monkeypatch.setattr(fast_inventory.os,'geteuid',lambda:0)
    monkeypatch.setattr(fast_inventory,'enforce_read_only',lambda p:None)
    monkeypatch.setattr(fast_inventory.tempfile,'mkdtemp',lambda **kw:str(mount))
    monkeypatch.setattr(fast_inventory,'index_containers',lambda *args:{'containers':[]})
    def command(args,**kwargs):
        if args[0]=='umount':raise subprocess.CalledProcessError(1,args)
        return SimpleNamespace(stdout=json.dumps({'filesystems':[{'options':'ro,nosuid,nodev,noexec'}]}))
    monkeypatch.setattr(fast_inventory,'run_command',command)
    with pytest.raises(fast_inventory.InventoryCleanupError) as exc:
        fast_inventory.readonly_mount_inventory(tmp_path/'fake-block','002')
    files,_,info,_=exc.value.result
    assert files[0]['path']=='good.txt'
    assert info['cleanup_failed'] is True
    assert mount.exists()


def test_scanner_stops_after_cleanup_failure_and_saves_captured_metadata(tmp_path,monkeypatch):
    monkeypatch.setattr(scanner,'inspect_device',lambda p:{})
    monkeypatch.setattr(scanner,'enforce_read_only',lambda p:None)
    monkeypatch.setattr(scanner,'_command',lambda args:'File System Type: NTFS')
    monkeypatch.setattr(scanner,'parse_mmls',lambda text:[{'allocated':True,'slot':s,'start_sector':i} for i,s in enumerate(['002','003'])])
    monkeypatch.setattr(scanner,'partition_path_for_start',lambda *args:tmp_path/'fake')
    calls=[]
    def inventory(*args):
        calls.append(args)
        data=([{'path':'kept.txt','size':1,'category':'Text/Logs','extension':'txt'}],[],
              {'cleanup_failed':True,'inventory_successful_entries':1},{'containers':[]})
        raise fast_inventory.InventoryCleanupError(data,OSError(5,'synthetic cleanup error'))
    monkeypatch.setattr(scanner,'readonly_mount_inventory',inventory)
    monkeypatch.setattr(scanner,'load_profile',lambda p:{'keywords':[],'version':'1','sha256':'synthetic'})
    p=scanner.scan(tmp_path/'fake',tmp_path/'profile','TEST',tmp_path/'results')
    s=json.loads((p/'summary.json').read_text())
    assert len(calls)==1 and s['file_count']==1
    assert s['scan_cleanup_failed'] and s['scan_status']=='partial'
    assert 'kept.txt' in (p/'files.csv').read_text()


@pytest.mark.parametrize('status',['partial','failed','unknown'])
def test_direct_decision_api_requires_explicit_quality_and_reason(tmp_path,status):
    store=CaseStore(tmp_path/'casefiles');record,_=result(store,status)
    media_id=record['media']['id'];responses=[]
    payload={'decision':'not_selected','reason_code':'technical','reason_note':'Observed inventory limitation.','operator':'TEST'}
    handler=SimpleNamespace(server=SimpleNamespace(case_store=store),_read_payload=lambda:payload,
                            _json=lambda status,data:responses.append((status,data)))
    TriageHandler._post_decision(handler,media_id)
    assert responses[-1][0]==400
    payload.update(quality_acknowledged='true',quality_status=status)
    TriageHandler._post_decision(handler,media_id)
    assert responses[-1][0]==400  # Strings are not a deliberate boolean acknowledgement.
    payload.update(quality_acknowledged=True,quality_status='complete')
    TriageHandler._post_decision(handler,media_id)
    assert responses[-1][0]==400
    payload.update(quality_status=status,reason_note='')
    TriageHandler._post_decision(handler,media_id)
    assert responses[-1][0]==400
    payload['reason_note']='Observed inventory limitation.'
    TriageHandler._post_decision(handler,media_id)
    assert responses[-1][0]==200
    event=json.loads((store.case_path('SYNTH')/'audit.log').read_text().splitlines()[-1])['details']
    assert event['quality_acknowledged'] is True and event['scan_status']==status
    assert event['scan_id']==record['media']['scan_id']


def test_phone_decision_stays_separate_from_usb_ack(tmp_path):
    store=CaseStore(tmp_path/'casefiles');record,_=result(store,'unknown','android:synthetic')
    out=store.record_decision(record['media']['id'],'specialist_not_consulted',None,'','TEST')
    assert out['media']['decision']=='specialist_not_consulted'


def test_failed_attempts_are_visible_once_without_fabricated_inventory(tmp_path):
    store=CaseStore(tmp_path/'casefiles')
    sight=store.allocate_sighting_number('SYNTH','TEST','/dev/fake',{'model':'Synthetic USB','serial':'TEST'})
    store.record_scan_failure('SYNTH',sight,'TEST','/dev/fake','mmls returned exit status 1')
    store.record_scan_failure('SYNTH',sight,'TEST','/dev/fake','duplicate callback')
    case=store.case_detail('SYNTH')
    assert case['media']==[] and len(case['scan_attempts'])==1
    attempt=case['scan_attempts'][0]
    assert attempt['file_count'] is None and attempt['keyword_matches'] is None
    assert attempt['model']=='Synthetic USB' and attempt['scan_status']=='failed'
    root=store.case_path('SYNTH')
    rows=list(csv.DictReader((root/'media-register.csv').open()))
    assert len(rows)==1 and rows[0]['file_count']=='' and rows[0]['scan_status']=='failed'
    assert 'Kein auswertbares Dateiinventar erstellt.' in (root/'case-report.txt').read_text()
    assert '0 Dateien' not in (root/'case-report.txt').read_text()
    assert (root/'audit.log').read_text().count('"event_type": "scan_failed"')==1
    with store._connect() as c:assert c.execute('select count(*) from media').fetchone()[0]==0


def test_completion_is_idempotent_and_cannot_acquire_failure_outcome(tmp_path):
    store=CaseStore(tmp_path/'casefiles');record,p=result(store,'complete')
    store.record_scan('SYNTH','SICHT-001','TEST',{'path':'/dev/fake'},p)
    store.record_scan_failure('SYNTH','SICHT-001','TEST','/dev/fake','response formatting error')
    text=(store.case_path('SYNTH')/'audit.log').read_text()
    assert text.count('"event_type": "scan_completed"')==1
    assert '"event_type": "scan_failed"' not in text
    e=json.loads(text.splitlines()[-1])['details']
    assert e['scan_status']=='complete' and e['inventory_complete'] is True


def test_legacy_quality_and_old_database_copy_preserve_artifacts_and_history(tmp_path):
    original=tmp_path/'old';store=CaseStore(original);record,p=result(store,'partial')
    store.record_decision(record['media']['id'],'secure',None,'','TEST','BM-TEST')
    before={f.name:f.read_bytes() for f in p.iterdir() if f.is_file()}
    with store._connect() as c:
        media=[tuple(x) for x in c.execute('select * from media')]
        audit=[tuple(x) for x in c.execute('select * from audit_events')]
        c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    copy=tmp_path/'old-copy';shutil.copytree(original,copy)
    reopened=CaseStore(copy)
    assert reopened.media_detail(record['media']['id'])['summary']['scan_status']=='partial'
    with reopened._connect() as c:
        assert [tuple(x) for x in c.execute('select * from media')]==media
        assert [tuple(x) for x in c.execute('select * from audit_events')]==audit
    assert {f.name:f.read_bytes() for f in p.iterdir() if f.is_file()}==before
    (p/'partitions.json').unlink()
    (p/'summary.json').write_text('{"file_count":0}')
    legacy=(p/'summary.json').read_bytes()
    assert _scan_summary(p)['scan_status']=='unknown'
    assert (p/'summary.json').read_bytes()==legacy


def test_lost_historical_inventory_cannot_become_a_zero_file_negative_result(tmp_path):
    store=CaseStore(tmp_path/'casefiles');record,p=result(store,'complete')
    (p/'files.csv').unlink()
    detail=store.media_detail(record['media']['id'])
    assert detail['summary']['scan_status']=='unknown'
    assert detail['summary']['scan_inventory_present'] is False
    assert detail['media']['file_count'] is None and detail['media']['keyword_matches'] is None
    store.refresh_exports('SYNTH')
    row=next(csv.DictReader((store.case_path('SYNTH')/'media-register.csv').open()))
    assert row['file_count']=='' and row['keyword_matches']==''


def test_cleanup_failure_does_not_turn_wholly_unreadable_directories_into_partial():
    summary={'file_count':0,'directory_count':38,'scan_cleanup_failed':True}
    apply_scan_quality(summary,[{'allocated':True,'scan_status':'failed','cleanup_failed':True,
        'inventory_root_read':True,'inventory_successful_entries':0,'read_error_count':38}])
    assert summary['scan_status']=='failed'


def test_historical_failed_status_is_not_upgraded_by_inconsistent_partition_metadata():
    summary={'scan_status':'failed','file_count':0}
    apply_scan_quality(summary,[{'allocated':True,'scan_status':'partial'}],historical=True)
    assert summary['scan_status']=='failed'
