#!/usr/bin/env bash

# Deliberate online or signed-offline updater. Every candidate is prepared and
# tested separately; the live release changes only through an atomic symlink.
set -euo pipefail

ACTION="${1:-}"
CONFIG_FILE="/etc/forensic-triage/triage.env"
LOCK_FILE="/run/forensic-triage-update.lock"

if [[ "$ACTION" != "check" && "$ACTION" != "install" && "$ACTION" != "offline" ]]; then
  echo "Verwendung: $0 check|install|offline" >&2
  exit 2
fi
if [[ -r "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi
RUNTIME_LINK="${FORENSIC_TRIAGE_RUNTIME_LINK:-/opt/triagebox-current}"
RELEASES_ROOT="${FORENSIC_TRIAGE_RELEASES_ROOT:-/opt/triagebox-releases}"
STATE_FILE="${FORENSIC_TRIAGE_UPDATE_STATE_FILE:-/var/lib/forensic-triage/update-status.env}"
UPDATE_ENABLED="${FORENSIC_TRIAGE_UPDATE_ENABLED:-true}"
UPDATE_REMOTE="${FORENSIC_TRIAGE_UPDATE_REMOTE:-origin}"
UPDATE_GIT_ROOT="${FORENSIC_TRIAGE_UPDATE_GIT_ROOT:-/opt/triagebox}"
OFFLINE_PACKAGE="${FORENSIC_TRIAGE_OFFLINE_UPDATE_FILE:-/var/lib/forensic-triage/offline-update.tbu}"
ALLOWED_SIGNERS="${FORENSIC_TRIAGE_OFFLINE_UPDATE_ALLOWED_SIGNERS:-/etc/forensic-triage/offline-update-allowed-signers}"
GUARD_FILE="${FORENSIC_TRIAGE_UPDATE_GUARD_FILE:-/run/forensic-triage-update-requested}"
target=""
current_version="unbekannt"
failure_message="UPDATE KONNTE NICHT SICHER ABGESCHLOSSEN WERDEN"
finished=false
guard_owned=false

write_status() {
  local state="$1" message="$2" available="${3:-}" current="${4:-}"
  install -d -m 0750 "$(dirname "$STATE_FILE")"
  umask 077
  {
    printf 'STATE=%q\n' "$state"
    printf 'MESSAGE=%q\n' "$message"
    printf 'AVAILABLE_VERSION=%q\n' "$available"
    printf 'CURRENT_VERSION=%q\n' "$current"
    printf 'UPDATED_AT=%q\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"${STATE_FILE}.new"
  mv -f "${STATE_FILE}.new" "$STATE_FILE"
}

on_exit() {
  local result=$?
  trap - EXIT
  if [[ "$ACTION" == "offline" ]]; then
    rm -f -- "$OFFLINE_PACKAGE"
  fi
  if [[ "$guard_owned" == "true" ]]; then
    rm -f -- "$GUARD_FILE"
  fi
  if (( result != 0 )) && [[ "$finished" != "true" ]]; then
    write_status "error" "$failure_message" "$target" "$current_version" || true
  fi
  exit "$result"
}
trap on_exit EXIT

if [[ "$UPDATE_ENABLED" != "true" ]]; then
  write_status "disabled" "UPDATES SIND IN DER KONFIGURATION DEAKTIVIERT"
  finished=true
  exit 0
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  write_status "busy" "EINE UPDATE-AKTION LÄUFT BEREITS"
  finished=true
  exit 0
fi
if [[ "$ACTION" == "install" || "$ACTION" == "offline" ]]; then
  umask 077
  printf '%s\n' "$$" >"$GUARD_FILE"
  guard_owned=true
fi

CURRENT_ROOT="$(readlink -f "$RUNTIME_LINK" 2>/dev/null || true)"
if [[ -z "$CURRENT_ROOT" || ! -x "$CURRENT_ROOT/.venv/bin/forensic-triage-web" ]]; then
  failure_message="AKTUELLE INSTALLATION IST NICHT VOLLSTÄNDIG"
  exit 1
fi
current_version="$("$CURRENT_ROOT/.venv/bin/forensic-triage-web" --version 2>/dev/null | awk '{print $NF}' || printf 'unbekannt')"
current_tag=""
if [[ -r "$CURRENT_ROOT/.triagebox-release" ]]; then
  current_tag="$(head -n 1 "$CURRENT_ROOT/.triagebox-release")"
elif git -C "$CURRENT_ROOT" rev-parse --is-inside-work-tree 2>/dev/null | grep -qx true; then
  current_tag="$(git -C "$CURRENT_ROOT" describe --tags --exact-match HEAD 2>/dev/null || true)"
fi

candidate=""
if [[ "$ACTION" == "offline" ]]; then
  write_status "installing" "OFFLINE-PAKET WIRD SIGNATURGEPRÜFT" "" "$current_version"
  if [[ ! -r "$ALLOWED_SIGNERS" && -r "$CURRENT_ROOT/deploy/offline-update-allowed-signers" ]]; then
    ALLOWED_SIGNERS="$CURRENT_ROOT/deploy/offline-update-allowed-signers"
  fi
  if [[ ! -r "$OFFLINE_PACKAGE" || ! -r "$ALLOWED_SIGNERS" ]]; then
    failure_message="OFFLINE-PAKET ODER ÖFFENTLICHER PRÜFSCHLÜSSEL FEHLT"
    exit 1
  fi
  failure_message="OFFLINE-PAKET IST UNGÜLTIG, NICHT FREIGEGEBEN ODER NICHT KOMPATIBEL"
  if ! target="$("$CURRENT_ROOT/.venv/bin/python" "$CURRENT_ROOT/scripts/prepare_offline_update.py" \
      "$OFFLINE_PACKAGE" "$RELEASES_ROOT" "$ALLOWED_SIGNERS" "$current_version" "$CURRENT_ROOT")"; then
    exit 1
  fi
  if [[ ! "$target" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$ ]]; then
    failure_message="OFFLINE-PAKET HAT EINE UNGÜLTIGE VERSION"
    exit 1
  fi
  candidate="$RELEASES_ROOT/$target"
  write_status "installing" "OFFLINE-RELEASE WIRD GETRENNT VORBEREITET" "$target" "$current_version"
  if [[ ! -x "$candidate/.venv/bin/python" ]]; then
    if [[ -e "$candidate/.venv" ]]; then
      mv "$candidate/.venv" "$candidate/.venv.unvollstaendig.$(date +%s)"
    fi
    if [[ -e "$candidate/.venv.new" ]]; then
      mv "$candidate/.venv.new" "$candidate/.venv.unvollstaendig.$(date +%s).new"
    fi
    cp -a "$CURRENT_ROOT/.venv" "$candidate/.venv.new"
    mv "$candidate/.venv.new" "$candidate/.venv"
  fi
  failure_message="OFFLINE-RELEASE KONNTE NICHT INSTALLIERT ODER GETESTET WERDEN"
  "$candidate/.venv/bin/python" -m pip install --no-index --no-deps --no-build-isolation -e "$candidate"
else
  if git -C "$CURRENT_ROOT" rev-parse --is-inside-work-tree 2>/dev/null | grep -qx true; then
    UPDATE_GIT_ROOT="$CURRENT_ROOT"
  elif ! git -C "$UPDATE_GIT_ROOT" rev-parse --is-inside-work-tree 2>/dev/null | grep -qx true; then
    failure_message="GIT-QUELLE FÜR ONLINE-UPDATES IST NICHT VERFÜGBAR"
    exit 1
  fi
  if [[ -n "$(git -C "$UPDATE_GIT_ROOT" status --porcelain --untracked-files=no)" ]]; then
    failure_message="LOKALE CODEÄNDERUNGEN VERHINDERN EIN SICHERES ONLINE-UPDATE"
    exit 1
  fi
  write_status "checking" "FREIGEGEBENE VERSION WIRD GEPRÜFT" "" "$current_version"
  failure_message="GIT-REPOSITORY NICHT ERREICHBAR ODER NICHT BERECHTIGT"
  git -C "$UPDATE_GIT_ROOT" fetch --prune --tags "$UPDATE_REMOTE"
  target="$(git -C "$UPDATE_GIT_ROOT" tag --list 'v[0-9]*' --sort=-version:refname | head -n 1)"
  if [[ -z "$target" ]]; then
    failure_message="KEINE FREIGEGEBENE VERSION GEFUNDEN"
    exit 1
  fi
  if [[ "$ACTION" == "check" ]]; then
    if [[ "$target" == "$current_tag" ]]; then
      write_status "current" "AKTUELLE VERSION IST BEREITS INSTALLIERT" "$target" "$current_version"
    else
      write_status "available" "UPDATE IST BEREIT ZUR INSTALLATION" "$target" "$current_version"
    fi
    finished=true
    exit 0
  fi
  if [[ "$target" == "$current_tag" ]]; then
    write_status "current" "AKTUELLE VERSION IST BEREITS INSTALLIERT" "$target" "$current_version"
    finished=true
    exit 0
  fi
  safe_target="${target//[^A-Za-z0-9._-]/_}"
  candidate="$RELEASES_ROOT/$safe_target"
  install -d -m 0755 "$RELEASES_ROOT"
  if [[ ! -e "$candidate" ]]; then
    write_status "installing" "NEUE VERSION WIRD GETRENNT VORBEREITET" "$target" "$current_version"
    failure_message="GIT-RELEASE KONNTE NICHT VORBEREITET WERDEN"
    git -C "$UPDATE_GIT_ROOT" worktree add --detach "$candidate" "$target"
  fi
  if [[ ! -x "$candidate/.venv/bin/python" ]]; then
    python3 -m venv "$candidate/.venv"
  fi
  failure_message="ONLINE-RELEASE KONNTE NICHT INSTALLIERT ODER GETESTET WERDEN"
  "$candidate/.venv/bin/python" -m pip install --upgrade pip
  "$candidate/.venv/bin/python" -m pip install -e "$candidate[test]"
fi

"$candidate/.venv/bin/python" -m pytest "$candidate/tests" -q
printf '%s\n' "$target" >"$candidate/.triagebox-release.new"
mv -f "$candidate/.triagebox-release.new" "$candidate/.triagebox-release"

# Preserve operator settings before the release path changes.
settings_root="${FORENSIC_TRIAGE_SETTINGS_ROOT:-$(dirname "${FORENSIC_TRIAGE_CASEFILES_ROOT:-$CURRENT_ROOT/casefiles}")/settings}"
profile_source="${FORENSIC_TRIAGE_PROFILE:-$CURRENT_ROOT/profiles/default.yaml}"
if [[ -f "$candidate/scripts/migrate_settings.py" ]]; then
  "$candidate/.venv/bin/python" "$candidate/scripts/migrate_settings.py" "$profile_source" "$settings_root"
fi

# Apply deployment templates from the tested candidate before switching code.
failure_message="SYSTEMKONFIGURATION DER NEUEN VERSION KONNTE NICHT INSTALLIERT WERDEN"
web_port="${FORENSIC_TRIAGE_WEB_PORT:-8787}"
nginx_site="/etc/nginx/sites-available/forensic-triage"
nginx_backup="$(mktemp)"
if [[ -f "$nginx_site" ]]; then
  cp "$nginx_site" "$nginx_backup"
fi
temp_web_service="$(mktemp)"
temp_update_service="$(mktemp)"
temp_nginx="$(mktemp)"
sed "s|@RUNTIME_ROOT@|$RUNTIME_LINK|g" "$candidate/deploy/forensic-triage-web.service.in" >"$temp_web_service"
sed "s|@RUNTIME_ROOT@|$RUNTIME_LINK|g" "$candidate/deploy/forensic-triage-update@.service.in" >"$temp_update_service"
sed "s|@WEB_PORT@|$web_port|g" "$candidate/deploy/forensic-triage-nginx.conf.in" >"$temp_nginx"
install -o root -g root -m 0644 "$temp_web_service" /etc/systemd/system/forensic-triage-web.service
install -o root -g root -m 0644 "$temp_update_service" /etc/systemd/system/forensic-triage-update@.service
install -o root -g root -m 0644 "$candidate/deploy/forensic-triage-update-check.timer" /etc/systemd/system/forensic-triage-update-check.timer
install -o root -g root -m 0644 "$temp_nginx" "$nginx_site"
install -d -o root -g root -m 0755 /etc/systemd/journald.conf.d
install -o root -g root -m 0644 "$candidate/deploy/forensic-triage-journald.conf" /etc/systemd/journald.conf.d/forensic-triage.conf
trusted_key_target="${FORENSIC_TRIAGE_OFFLINE_UPDATE_ALLOWED_SIGNERS:-/etc/forensic-triage/offline-update-allowed-signers}"
install -d -o root -g root -m 0750 "$(dirname "$trusted_key_target")"
install -o root -g root -m 0644 "$candidate/deploy/offline-update-allowed-signers" "$trusted_key_target"
install -d -o root -g systemd-journal -m 2755 /var/log/journal
rm -f "$temp_web_service" "$temp_update_service" "$temp_nginx"
if ! nginx -t; then
  if [[ -s "$nginx_backup" ]]; then
    install -o root -g root -m 0644 "$nginx_backup" "$nginx_site"
  fi
  rm -f "$nginx_backup"
  failure_message="SYSTEMKONFIGURATION DER NEUEN VERSION IST UNGÜLTIG"
  exit 1
fi
rm -f "$nginx_backup"
systemctl daemon-reload
systemctl restart systemd-journald.service
journalctl --flush

previous_root="$CURRENT_ROOT"
ln -s "$candidate" "${RUNTIME_LINK}.next"
mv -Tf "${RUNTIME_LINK}.next" "$RUNTIME_LINK"
systemctl restart forensic-triage-web.service
systemctl reload nginx.service
sleep 2
if ! systemctl is-active --quiet forensic-triage-web.service; then
  ln -s "$previous_root" "${RUNTIME_LINK}.rollback"
  mv -Tf "${RUNTIME_LINK}.rollback" "$RUNTIME_LINK"
  systemctl restart forensic-triage-web.service || true
  failure_message="NEUE VERSION KONNTE NICHT STARTEN — VORVERSION WIEDERHERGESTELLT"
  exit 1
fi
ln -sfn "$previous_root" "${RUNTIME_LINK}.previous"
write_status "installed" "UPDATE ERFOLGREICH INSTALLIERT" "$target" \
  "$("$candidate/.venv/bin/forensic-triage-web" --version | awk '{print $NF}')"
finished=true
