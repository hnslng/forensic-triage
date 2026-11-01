"""Same-origin/anti-rebinding boundary for the new metadata analysis APIs.

This is not authentication. Existing legacy endpoints remain a separate audit
item; no CORS grants or relaxed legacy access checks are introduced here.
"""
from __future__ import annotations
import ipaddress
import os
import secrets
import socket
from urllib.parse import urlsplit


def hostname_authorized(host: str) -> bool:
    host = host.lower().rstrip('.')
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True  # IP literals cannot be DNS-rebound to a different host.
    except ValueError:
        name = socket.gethostname().lower().rstrip('.')
        allowed = {'localhost', name, name.split('.')[0] + '.local'}
        allowed.update(x.strip().lower().rstrip('.') for x in os.environ.get('FORENSIC_TRIAGE_ALLOWED_HOSTS','').split(',') if x.strip())
        return host in allowed


def validate_request(headers, token: str, *, mutation=False):
    host = headers.get('Host', '')
    if len(host)>255 or host.strip()!=host or any(c in host for c in '/\\,@#?\r\n'):
        raise ValueError('Nicht freigegebener Host.')
    try:
        parsed = urlsplit('http://' + host)
        _ = parsed.port
        if not hostname_authorized(parsed.hostname or '') or parsed.username or parsed.password:
            raise ValueError()
    except ValueError as exc:
        raise ValueError('Nicht freigegebener Host.') from exc
    origin = headers.get('Origin')
    if origin:
        try:
            source = urlsplit(origin)
            if source.scheme not in ('http','https') or source.netloc.lower() != host.lower() or source.path or source.query or source.fragment:
                raise ValueError()
        except ValueError as exc:
            raise ValueError('Fremder oder ungültiger Browser-Origin.') from exc
    if headers.get('Sec-Fetch-Site','') in ('cross-site','same-site'):
        raise ValueError('Browserzugriff muss same-origin sein.')
    if mutation:
        if headers.get('Content-Type','').split(';',1)[0].strip().lower()!='application/json':
            raise ValueError('Neue Auswertungen benötigen application/json.')
        supplied=headers.get('X-Triage-CSRF','')
        if not supplied or not supplied.isascii() or not secrets.compare_digest(supplied,token):
            raise ValueError('Auswertungsbestätigung abgelaufen oder fehlt. Ansicht erneut laden.')
