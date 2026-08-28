#!/usr/bin/env bash

set -euo pipefail

REPOSITORY_URL="${TRIAGEBOX_REPOSITORY_URL:-https://github.com/hnslng/forensic-triage.git}"
INSTALL_ROOT="${TRIAGEBOX_INSTALL_ROOT:-/opt/triagebox}"
INSTALL_REF="${TRIAGEBOX_INSTALL_REF:-main}"

if [[ $EUID -ne 0 ]]; then
  echo "Bitte als root ausführen: sudo bash $0" >&2
  exit 1
fi
if [[ ! -r /etc/os-release ]]; then
  echo "Nicht unterstütztes System: /etc/os-release fehlt." >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID_LIKE:-} ${ID:-}" != *debian* ]]; then
  echo "Der Bootstrap unterstützt nur Raspberry Pi OS/Debian." >&2
  exit 1
fi
if [[ ! -r /proc/device-tree/model ]] || ! tr -d '\0' </proc/device-tree/model | grep -qi "Raspberry Pi"; then
  echo "Dieses System wurde nicht als Raspberry Pi erkannt." >&2
  exit 1
fi
if [[ ! "$INSTALL_ROOT" =~ ^/[A-Za-z0-9._/-]+$ || "$INSTALL_ROOT" == "/" ]]; then
  echo "Ungeeigneter Installationspfad: $INSTALL_ROOT" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates git

if ! git ls-remote "$REPOSITORY_URL" HEAD >/dev/null 2>&1; then
  echo "Repository ist nicht erreichbar." >&2
  echo "Für diesen einfachen Bootstrap muss es während der Installation öffentlich sein." >&2
  exit 1
fi

if [[ -d "$INSTALL_ROOT/.git" ]]; then
  if [[ -n "$(git -C "$INSTALL_ROOT" status --porcelain --untracked-files=no)" ]]; then
    echo "Installation enthält lokale Codeänderungen und wird nicht überschrieben: $INSTALL_ROOT" >&2
    exit 1
  fi
  git -C "$INSTALL_ROOT" remote set-url origin "$REPOSITORY_URL"
  git -C "$INSTALL_ROOT" fetch --prune --tags origin
else
  if [[ -e "$INSTALL_ROOT" && -n "$(find "$INSTALL_ROOT" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    echo "Installationspfad ist bereits belegt: $INSTALL_ROOT" >&2
    exit 1
  fi
  install -d -o root -g root -m 0755 "$(dirname "$INSTALL_ROOT")"
  git clone "$REPOSITORY_URL" "$INSTALL_ROOT"
fi

if [[ "$INSTALL_REF" == "main" ]]; then
  git -C "$INSTALL_ROOT" checkout -B main origin/main
else
  git -C "$INSTALL_ROOT" checkout --detach "$INSTALL_REF"
fi

echo
echo "TRIAGE//BOX-Quellcode bereit: $INSTALL_ROOT ($INSTALL_REF)"
exec "$INSTALL_ROOT/scripts/install_debian.sh" --pi
