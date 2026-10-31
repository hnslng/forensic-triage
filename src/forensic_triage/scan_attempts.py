"""Read-only reconstruction of reserved sightings without a registered inventory."""
from __future__ import annotations

import json
import re
from typing import Any

from .scan_quality import LABELS, NO_INVENTORY


def failure_message(error: str) -> str:
    text = error.casefold()
    if 'mmls' in text:
        return 'Die Partitionsanalyse konnte nicht abgeschlossen werden.'
    if any(word in text for word in ('timeout', 'zeitlimit', 'timed out')):
        return 'Die Sichtung wurde wegen eines Zeitlimits unterbrochen.'
    if any(word in text for word in ('umount', 'unmount', 'sicherer abschluss')):
        return 'Der sichere Abschluss des Gerätezugriffs ist nicht bestätigt.'
    if 'mount' in text:
        return 'Das Dateisystem konnte nicht sicher eingebunden werden.'
    return 'Die technische Sichtung konnte nicht erfolgreich abgeschlossen werden.'


def scan_attempts(audit, media) -> list[dict[str, Any]]:
    registered = {row['sighting_number'] for row in media}
    attempts = {}
    for event in audit:
        if event['event_type'] not in {'sighting_reserved', 'scan_failed'}:
            continue
        details = json.loads(event['details_json'])
        sighting = details.get('sighting_number')
        if not sighting or sighting in registered:
            continue
        attempt = attempts.setdefault(sighting, {
            'id': None, 'attempt_only': True, 'sighting_number': sighting, 'evidence_number': '',
            'scan_id': None, 'result_path': None, 'scanned_at': event['occurred_at'],
            'device_path': details.get('device_path', ''), 'vendor': '', 'model': '', 'serial': '',
            'size': None, 'file_count': None, 'directory_count': None, 'keyword_matches': None,
            'duration_seconds': None, 'decision': 'open', 'reason_code': None, 'reason_note': None,
            'decision_operator': None, 'decided_at': None, 'specialist_name': None,
            'period_date_from': None, 'period_date_to': None, 'period_timezone': None, 'period_file_count': None,
            'scan_status': 'unknown', 'scan_inventory_present': False, 'scan_error_count': None,
            'scan_affected_partitions': [], 'scan_quality_message': NO_INVENTORY,
            'scan_quality_action': 'Verbindung und Gerätestatus prüfen; laufende Sichtung abwarten oder erneut sichten.',
        })
        device = details.get('device') or {}
        for key in ('vendor', 'model', 'serial', 'size', 'media_identity'):
            if key in device:
                attempt[key] = device[key]
        if event['event_type'] == 'scan_failed':
            attempt.update(scan_status='failed', error_details=re.sub(r'/mnt/forensic-triage-[A-Za-z0-9_-]+', '[temporärer Mountpunkt]', details.get('error', '')), scan_error_count=1,
                           scan_quality_message=failure_message(details.get('error', '')) + ' ' + NO_INVENTORY)
        attempt['scan_quality_label'] = LABELS[attempt['scan_status']]
    return list(attempts.values())
