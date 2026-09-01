#!/usr/bin/env bash

# Deliberate, release-tag-only updater. It first builds and tests a detached
# worktree. The live release is changed only by an atomic symlink replacement.
set -euo pipefail

ACTION="${1:-}"
CONFIG_FILE="/etc/forensic-triage/triage.env"
LOCK_FILE="/run/forensic-triage-update.lock"

if [[ "$ACTION" != "check" && "$ACTION" != "install" ]]; then
  echo "Verwendung: $0 check|install" >&2
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

if [[ "$UPDATE_ENABLED" != "true" ]]; then
  write_status "disabled" "UPDATES SIND IN DER KONFIGURATION DEAKTIVIERT"
  exit 0
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  write_status "busy" "EINE UPDATE-AKTION LÄUFT BEREITS"
  exit 0
fi

CURRENT_ROOT="$(readlink -f "$RUNTIME_LINK" 2>/dev/null || true)"
if [[ -z "$CURRENT_ROOT" ]] || \
   ! git -C "$CURRENT_ROOT" rev-parse --is-inside-work-tree 2>/dev/null | grep -qx true; then
  write_status "error" "AKTUELLE INSTALLATION IST KEIN GIT-CHECKOUT"
  exit 1
fi
if [[ -n "$(git -C "$CURRENT_ROOT" status --porcelain --untracked-files=no)" ]]; then
  write_status "error" "LOKALE CODEÄNDERUNGEN VERHINDERN EIN SICHERES UPDATE"
  exit 1
fi

current_version="$("$CURRENT_ROOT/.venv/bin/forensic-triage-web" --version 2>/dev/null | awk '{print $NF}' || printf 'unbekannt')"
write_status "checking" "FREIGEGEBENE VERSION WIRD GEPRÜFT" "" "$current_version"
if ! git -C "$CURRENT_ROOT" fetch --prune --tags "$UPDATE_REMOTE"; then
  write_status "error" "GIT-REPOSITORY NICHT ERREICHBAR ODER NICHT BERECHTIGT" "" "$current_version"
  exit 1
fi

target="$(git -C "$CURRENT_ROOT" tag --list 'v[0-9]*' --sort=-version:refname | head -n 1)"
if [[ -z "$target" ]]; then
  write_status "error" "KEINE FREIGEGEBENE VERSION GEFUNDEN" "" "$current_version"
  exit 1
fi
current_tag="$(git -C "$CURRENT_ROOT" describe --tags --exact-match HEAD 2>/dev/null || true)"
if [[ "$ACTION" == "check" ]]; then
  if [[ "$target" == "$current_tag" ]]; then
    write_status "current" "AKTUELLE VERSION IST BEREITS INSTALLIERT" "$target" "$current_version"
  else
    write_status "available" "UPDATE IST BEREIT ZUR INSTALLATION" "$target" "$current_version"
  fi
  exit 0
fi

if systemctl is-active --quiet forensic-triage-web.service && \
   systemctl show -p ActiveState --value forensic-triage-web.service | grep -qx active; then
  : # The HTTP handler has already rejected active cases and scans.
fi
if [[ "$target" == "$current_tag" ]]; then
  write_status "current" "AKTUELLE VERSION IST BEREITS INSTALLIERT" "$target" "$current_version"
  exit 0
fi

safe_target="${target//[^A-Za-z0-9._-]/_}"
candidate="$RELEASES_ROOT/$safe_target"
install -d -m 0755 "$RELEASES_ROOT"
if [[ ! -e "$candidate" ]]; then
  write_status "installing" "NEUE VERSION WIRD GETRENNT VORBEREITET" "$target" "$current_version"
  git -C "$CURRENT_ROOT" worktree add --detach "$candidate" "$target"
fi
if [[ ! -x "$candidate/.venv/bin/python" ]]; then
  python3 -m venv "$candidate/.venv"
fi
"$candidate/.venv/bin/python" -m pip install --upgrade pip
"$candidate/.venv/bin/python" -m pip install -e "$candidate[test]"
"$candidate/.venv/bin/python" -m pytest "$candidate/tests" -q

# Apply deployment templates from the tested candidate before switching code.
# This lets later releases update nginx and systemd without touching case data.
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
rm -f "$temp_web_service" "$temp_update_service" "$temp_nginx"
if ! nginx -t; then
  if [[ -s "$nginx_backup" ]]; then
    install -o root -g root -m 0644 "$nginx_backup" "$nginx_site"
  fi
  rm -f "$nginx_backup"
  write_status "error" "SYSTEMKONFIGURATION DER NEUEN VERSION IST UNGÜLTIG" "$target" "$current_version"
  exit 1
fi
rm -f "$nginx_backup"
systemctl daemon-reload

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
  write_status "error" "NEUE VERSION KONNTE NICHT STARTEN — VORVERSION WIEDERHERGESTELLT" "$target" "$current_version"
  exit 1
fi
ln -sfn "$previous_root" "${RUNTIME_LINK}.previous"
write_status "installed" "UPDATE ERFOLGREICH INSTALLIERT" "$target" "$("$candidate/.venv/bin/forensic-triage-web" --version | awk '{print $NF}')"
