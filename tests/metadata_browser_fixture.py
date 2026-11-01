"""Emit real backend responses for the offline browser suite (synthetic only)."""
import json
import tempfile
from pathlib import Path
from test_metadata_analysis import fixture, evaluate

with tempfile.TemporaryDirectory(prefix='triage-browser-reference-') as directory:
    store, medium, _ = fixture(Path(directory))
    first = evaluate(store, medium)
    second = evaluate(store, medium, start='2025-01-01', end='2025-12-31')
    result = {'original': store.period_analysis(medium), 'year24': store.period_analysis(medium, first['evaluation_id']),
              'year25': store.period_analysis(medium, second['evaluation_id']), 'record': store.media_detail(medium)}
    for name, identity in [('original',''),('year24',first['evaluation_id']),('year25',second['evaluation_id'])]:
        result[name]['files'] = store.file_inventory(medium, analysis_view=True, evaluation_id=identity, sort_by='path')['files']
    print(json.dumps(result))
