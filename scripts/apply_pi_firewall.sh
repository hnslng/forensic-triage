#!/usr/bin/env bash

set -euo pipefail

NETWORK_CONFIG="${1:-/etc/forensic-triage/pi-network.env}"
if [[ ! -r "$NETWORK_CONFIG" ]]; then
  echo "Netzwerkkonfiguration fehlt: $NETWORK_CONFIG" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$NETWORK_CONFIG"
: "${TRIAGEBOX_WIFI_INTERFACE:=wlan0}"

# NetworkManager's shared mode supplies DHCP. This dedicated table prevents
# hotspot clients from being routed onwards through Ethernet or another uplink.
/usr/sbin/nft list table inet triagebox >/dev/null 2>&1 && \
  /usr/sbin/nft delete table inet triagebox
/usr/sbin/nft add table inet triagebox
/usr/sbin/nft 'add chain inet triagebox forward { type filter hook forward priority -10; policy accept; }'
/usr/sbin/nft add rule inet triagebox forward iifname "$TRIAGEBOX_WIFI_INTERFACE" counter drop
/usr/sbin/nft add rule inet triagebox forward oifname "$TRIAGEBOX_WIFI_INTERFACE" counter drop
