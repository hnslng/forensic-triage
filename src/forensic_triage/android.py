"""Fast, app-only Android triage through an explicitly authorized ADB link."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .commands import run_command
from .container_inventory import empty_catalog
from .crypto_rules import CRYPTO_CATEGORIES, classify_app
from . import diagnostics as diag
from .keywords import load_profile
from .reporting import write_files_csv, write_json
from .settings import catalog_snapshot
from .statistics import summarize


ANDROID_USB_VENDORS = {
    "04e8": "Samsung", "18d1": "Google", "2717": "Xiaomi", "22b8": "Motorola",
    "2a70": "OnePlus", "22d9": "OPPO", "0fce": "Sony", "12d1": "Huawei",
    "2b6a": "Nothing", "1004": "LG", "0bb4": "HTC", "2d95": "vivo",
}

ANDROID_MANUFACTURER_MARKERS = (
    "samsung", "google", "pixel", "xiaomi", "redmi", "motorola", "oneplus",
    "oppo", "sony", "huawei", "honor", "nothing", "lg", "htc", "vivo",
    "tcl", "alcatel", "nokia", "hmd", "realme", "zte", "asus", "rog",
    "fairphone", "lenovo", "meizu", "tecno", "infinix", "itel", "blackview",
    "ulefone", "doogee", "cubot", "oukitel", "umidigi",
)
ANDROID_PRODUCT_MARKERS = (
    "android", "galaxy", "pixel", "phone", "smartphone", "oneplus", "oppo",
    "xiaomi", "redmi", "moto", "xperia", "huawei", "honor", "nothing", "vivo",
    "tcl", "alcatel", "nokia", "hmd", "realme", "zte", "asus", "rog",
    "fairphone", "lenovo", "meizu", "tecno", "infinix", "itel", "blackview",
    "ulefone", "doogee", "cubot", "oukitel", "umidigi",
)
CAMERA_MARKERS = (
    "camera", "digital camera", "dslr", "mirrorless", "nikon", "canon",
    "fujifilm", "olympus", "panasonic lumix", "leica",
)


def _run(args: list[str], *, timeout: float = 8, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run_command(args, check=check, capture_output=True, timeout=timeout)


def _sysfs_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()[:300]
    except OSError:
        return ""


def _usb_interfaces(root: Path, sysfs_name: str) -> list[dict[str, str]]:
    """Read USB interface descriptors belonging to one physical device."""
    interfaces: list[dict[str, str]] = []
    for interface in sorted(root.glob(f"{sysfs_name}:*"), key=lambda item: item.name):
        class_id = _sysfs_text(interface / "bInterfaceClass").casefold()
        if not class_id:
            continue
        interfaces.append({
            "name": interface.name,
            "class": class_id,
            "subclass": _sysfs_text(interface / "bInterfaceSubClass").casefold(),
            "protocol": _sysfs_text(interface / "bInterfaceProtocol").casefold(),
            "label": _sysfs_text(interface / "interface"),
        })
    return interfaces


def _interface_summary(interfaces: list[dict[str, str]]) -> str:
    return ",".join(
        f"{item['class']}/{item['subclass']}/{item['protocol']}"
        + (f":{item['label']}" if item.get("label") else "")
        for item in interfaces
    )


def _android_usb_evidence(
    *, vendor_id: str, manufacturer: str, product: str,
    device_class: str, interfaces: list[dict[str, str]],
) -> tuple[bool, str, str]:
    """Conservatively classify a pre-ADB USB device and explain the evidence."""
    description = f"{manufacturer} {product}".casefold()
    labels = " ".join(item.get("label", "") for item in interfaces).casefold()
    known_vendor = vendor_id in ANDROID_USB_VENDORS
    known_brand = any(
        re.search(rf"\b{re.escape(marker)}\b", description)
        for marker in ANDROID_MANUFACTURER_MARKERS
    )
    phone_product = any(
        re.search(rf"\b{re.escape(marker)}\b", description)
        for marker in ANDROID_PRODUCT_MARKERS
    )
    camera = any(marker in description for marker in CAMERA_MARKERS)
    adb_interface = any(
        item["class"] == "ff" and item["subclass"] == "42" and item["protocol"] in {"01", "1"}
        for item in interfaces
    ) or "adb" in labels
    imaging_interface = any(
        item["class"] == "06" and item["subclass"] in {"01", "1"}
        for item in interfaces
    ) or any(marker in labels for marker in ("mtp", "ptp"))
    composite_phone_interface = any(item["class"] in {"02", "03", "06", "ff"} for item in interfaces)
    phone_usb_evidence = imaging_interface or (
        device_class in {"00", "0", "ef"} and composite_phone_interface
    )

    if known_vendor:
        return True, "high", "known_android_vendor"
    if adb_interface:
        return True, "high", "adb_usb_interface"
    if known_brand and not camera and phone_usb_evidence:
        return True, "medium", "known_phone_brand_with_mtp_ptp"
    if phone_product and not camera and phone_usb_evidence:
        return True, "medium", "phone_identity_with_mtp_ptp_or_composite_usb"
    if imaging_interface and camera:
        return False, "rejected", "camera_ptp_without_android_evidence"
    if imaging_interface:
        return False, "rejected", "mtp_ptp_without_phone_evidence"
    return False, "rejected", "no_android_phone_evidence"


def _usb_candidates(root: Path = Path("/sys/bus/usb/devices")) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if not root.is_dir():
        diag.change(
            "android.sysfs.root", "ANDROID", "sysfs-Pfad nicht verfügbar",
            {"root": str(root)}, signature="missing", debug=True,
        )
        return candidates
    diag.change("android.sysfs.root", "ANDROID", "sysfs-Pfad verfügbar", signature="present", debug=True)
    entries = sorted(root.iterdir(), key=lambda item: item.name)
    for directory in entries:
        vendor_id = _sysfs_text(directory / "idVendor").casefold()
        if not vendor_id:  # Interface directories have no idVendor of their own.
            continue
        product_id = _sysfs_text(directory / "idProduct").casefold()
        manufacturer = _sysfs_text(directory / "manufacturer")
        product = _sysfs_text(directory / "product")
        device_class = _sysfs_text(directory / "bDeviceClass").casefold()
        interfaces = _usb_interfaces(root, directory.name)
        accepted, confidence, reason = _android_usb_evidence(
            vendor_id=vendor_id, manufacturer=manufacturer, product=product,
            device_class=device_class, interfaces=interfaces,
        )
        if not accepted:
            diag.change(
                f"android.usb.rejected.{directory.name}", "ANDROID",
                f"USB-Gerät nicht als Android klassifiziert: name={directory.name} reason={reason}",
                {
                    "idVendor": vendor_id, "idProduct": product_id,
                    "manufacturer": manufacturer, "product": product,
                    "device_class": device_class, "interfaces": _interface_summary(interfaces),
                },
                signature=f"{vendor_id}:{product_id}:{reason}:{_interface_summary(interfaces)}", debug=True,
            )
            continue
        serial = _sysfs_text(directory / "serial")
        candidates.append({
            "sysfs_name": directory.name, "vendor_id": vendor_id, "product_id": product_id,
            "vendor": manufacturer or ANDROID_USB_VENDORS.get(vendor_id, "Android"),
            "model": product or "Android-Gerät", "serial": serial,
            "device_class": device_class, "interfaces": interfaces,
            "confidence": confidence, "evidence": reason,
        })
    diag.change(
        "android.sysfs.summary", "ANDROID",
        f"sysfs geprüft: {len(entries)} Einträge, {len(candidates)} Android-Kandidaten",
        {"checked": len(entries), "candidates": len(candidates)},
        signature=f"{len(entries)}:{len(candidates)}:{'|'.join(sorted(c['sysfs_name'] for c in candidates))}",
        debug=True,
    )
    return candidates


def _adb_rows() -> list[dict[str, str]]:
    if not shutil.which("adb"):
        return []
    result = _run(["adb", "devices", "-l"], timeout=4)
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.strip().split()
        if len(fields) < 2:
            continue
        row = {"serial": fields[0], "adb_state": fields[1]}
        for field in fields[2:]:
            key, separator, value = field.partition(":")
            if separator:
                row[key] = value
        rows.append(row)
    return rows


def android_guidance(vendor: str) -> list[str]:
    normalized = vendor.casefold()
    if "samsung" in normalized:
        return [
            "Einstellungen öffnen", "Telefoninfo öffnen", "Softwareinformationen öffnen",
            "Siebenmal auf Buildnummer tippen und Gerätecode bestätigen",
            "Zu Einstellungen → Entwickleroptionen zurückgehen", "USB-Debugging aktivieren",
            "Die Abfrage ‚USB-Debugging zulassen?‘ bestätigen",
        ]
    if "google" in normalized or "pixel" in normalized:
        return [
            "Einstellungen öffnen", "Über das Telefon öffnen", "Siebenmal auf Build-Nummer tippen und Gerätecode bestätigen",
            "System → Entwickleroptionen öffnen", "USB-Debugging aktivieren",
            "Die Abfrage ‚USB-Debugging zulassen?‘ bestätigen",
        ]
    if "xiaomi" in normalized:
        return [
            "Einstellungen → Über das Telefon öffnen", "Mehrfach auf OS-/MIUI-Version tippen",
            "Weitere Einstellungen → Entwickleroptionen öffnen", "USB-Debugging aktivieren",
            "Die Verbindungsabfrage am Telefon bestätigen",
        ]
    if "oneplus" in normalized:
        return [
            "Einstellungen → Über das Gerät → Version öffnen", "Siebenmal auf Build-Nummer tippen",
            "Weitere Einstellungen → Entwickleroptionen öffnen", "USB-Debugging aktivieren",
            "Die Verbindungsabfrage am Telefon bestätigen",
        ]
    if "motorola" in normalized:
        return [
            "Einstellungen → Über das Telefon öffnen", "Siebenmal auf Build-Nummer tippen",
            "System → Entwickleroptionen öffnen", "USB-Debugging aktivieren",
            "Die Verbindungsabfrage am Telefon bestätigen",
        ]
    return [
        "Einstellungen → Über das Telefon öffnen", "Siebenmal auf Build-Nummer tippen",
        "Entwickleroptionen öffnen", "USB-Debugging aktivieren",
        "Die Verbindungsabfrage am Telefon bestätigen",
    ]


def _log_discovery_state(
    *, usb: list[dict[str, Any]], adb_available: bool, adb: list[dict[str, str]],
    devices: list[dict[str, Any]],
) -> None:
    """Debug-only, change-tracked insight into sysfs and ADB (Diagnose Alpha 70)."""
    diag.change(
        "android.adb.available", "ANDROID",
        f"ADB-Werkzeug {'vorhanden' if adb_available else 'nicht installiert'}",
        {"adb_binary": adb_available},
        signature="yes" if adb_available else "no",
    )
    for row in adb:
        diag.change(
            f"android.adb.{row['serial']}", "ANDROID",
            f"ADB-Zustand: serial={row['serial']} state={row['adb_state']}",
            {"adb_state": row["adb_state"]}, signature=row["adb_state"], debug=True,
        )
    for item in usb:
        diag.change(
            f"android.usb.{item['sysfs_name']}", "ANDROID",
            "USB-Kandidat: "
            f"vendor={item['vendor_id']} product={item['product_id']} "
            f"manufacturer={item['vendor']} name={item['sysfs_name']}",
            {
                "idVendor": item["vendor_id"], "idProduct": item["product_id"],
                "manufacturer": item["vendor"], "product": item["model"],
                "serial_present": bool(item["serial"]),
                "device_class": item.get("device_class", ""),
                "interfaces": _interface_summary(item.get("interfaces", [])),
                "confidence": item.get("confidence", ""),
                "reason": item.get("evidence", ""),
            },
            signature=(
                f"{item['vendor_id']}:{item['product_id']}:{bool(item['serial'])}:"
                f"{item.get('confidence', '')}:{item.get('evidence', '')}:"
                f"{_interface_summary(item.get('interfaces', []))}"
            ),
            debug=True,
        )
    for device in devices:
        diag.change(
            f"android.result.{device['path']}", "ANDROID",
            f"Android-Verbindungsstatus: {device['connection_state']}",
            {
                "connection_state": device["connection_state"],
                "scan_supported": bool(device["scan_supported"]),
                "identity_source": device.get("identity_source", ""),
            }, signature=f"{device['connection_state']}:{bool(device['scan_supported'])}", debug=True,
        )


def _match_usb_candidate(
    row: dict[str, str], usb: list[dict[str, Any]], used_sysfs: set[str],
) -> tuple[dict[str, Any], str]:
    serial = row.get("serial", "")
    for item in usb:
        if item["sysfs_name"] not in used_sysfs and item.get("serial") and item["serial"] == serial:
            return item, "usb_serial"
    topology = str(row.get("usb") or "").removeprefix("usb:")
    if topology:
        for item in usb:
            if item["sysfs_name"] not in used_sysfs and item["sysfs_name"] == topology:
                return item, "usb_topology"
    return {}, "adb_serial"


def discover_androids() -> list[dict[str, Any]]:
    usb = _usb_candidates()
    adb_available = bool(shutil.which("adb"))
    adb = _adb_rows()
    devices: list[dict[str, Any]] = []
    used_sysfs: set[str] = set()
    for row in adb:
        serial = row["serial"]
        physical, identity_source = _match_usb_candidate(row, usb, used_sysfs)
        if physical:
            used_sysfs.add(physical["sysfs_name"])
        state = row["adb_state"]
        vendor = str(physical.get("vendor") or row.get("product") or "Android")
        model = str(physical.get("model") or row.get("model", "")).replace("_", " ") or "Android-Gerät"
        connection_state = "authorized" if state == "device" else "authorization_required" if state == "unauthorized" else state
        reason = "" if state == "device" else (
            "Verbindungsabfrage am Telefon bestätigen." if state == "unauthorized" else
            "Telefon entsperren, Kabel prüfen und Verbindungsfreigabe bestätigen."
        )
        identity = str(physical.get("serial") or (f"usb-{physical['sysfs_name']}" if physical else serial))
        devices.append({
            "path": f"android:{identity}", "serial": str(physical.get("serial") or serial), "adb_serial": serial,
            "vendor": vendor, "model": model, "size": 0, "media_type": "android",
            "connection_state": connection_state, "scan_supported": state == "device",
            "mounted": False, "read_only": False, "unavailable_reason": reason,
            "guidance": android_guidance(vendor), "identity_source": identity_source,
        })
    for item in usb:
        if item["sysfs_name"] in used_sysfs:
            continue
        identity = item["serial"] or f"usb-{item['sysfs_name']}"
        connection_state = "debugging_required" if adb_available else "support_missing"
        unavailable_reason = (
            "Für die Krypto-App-Prüfung die Schritte am Telefon durchführen."
            if adb_available else
            "ANDROID-UNTERSTÜTZUNG UNVOLLSTÄNDIG INSTALLIERT: Systempaket adb installieren."
        )
        devices.append({
            "path": f"android:{identity}", "serial": item["serial"], "adb_serial": "",
            "vendor": item["vendor"], "model": item["model"], "size": 0,
            "media_type": "android", "connection_state": connection_state,
            "scan_supported": False, "mounted": False, "read_only": False,
            "unavailable_reason": unavailable_reason,
            "identity_source": "usb_serial" if item["serial"] else "usb_topology",
            "guidance": android_guidance(item["vendor"]) if adb_available else [
                "Pi einmal mit Internet verbinden",
                "sudo apt-get update && sudo apt-get install -y adb ausführen",
                "TRIAGE//BOX anschließend neu starten",
            ],
        })
    devices = sorted(devices, key=lambda item: (str(item["vendor"]).casefold(), str(item["model"]).casefold(), str(item["path"])))
    _log_discovery_state(usb=usb, adb_available=adb_available, adb=adb, devices=devices)
    return devices


def _adb(serial: str, *args: str, timeout: float = 12) -> subprocess.CompletedProcess[str]:
    return _run(["adb", "-s", serial, *args], timeout=timeout)


def _prop(serial: str, name: str) -> str:
    result = _adb(serial, "shell", "getprop", name, timeout=6)
    return result.stdout.strip()[:300] if result.returncode == 0 else ""


def _profiles(serial: str) -> list[dict[str, Any]]:
    result = _adb(serial, "shell", "pm", "list", "users", timeout=8)
    profiles: list[dict[str, Any]] = []
    for user_id, name, flags in re.findall(r"UserInfo\{(\d+):([^:}]*):([0-9a-fA-F]+)", result.stdout):
        profiles.append({
            "id": user_id, "name": name or ("Hauptprofil" if user_id == "0" else f"Profil {user_id}"),
            "flags": flags, "status": "pending", "app_count": 0,
            "protected": any(word in name.casefold() for word in ("secure", "knox", "geschützt")),
        })
    return profiles or [{"id": "0", "name": "Hauptprofil", "flags": "", "status": "pending", "app_count": 0, "protected": False}]


def _packages_for_user(serial: str, user_id: str) -> tuple[list[str], str]:
    commands = [
        ("shell", "cmd", "package", "list", "packages", "--user", user_id, "-3"),
        ("shell", "pm", "list", "packages", "--user", user_id, "-3"),
    ]
    errors: list[str] = []
    for command in commands:
        result = _adb(serial, *command, timeout=20)
        if result.returncode == 0 and "error:" not in result.stdout.casefold():
            packages = sorted({line.removeprefix("package:").strip() for line in result.stdout.splitlines() if line.startswith("package:")})
            return packages, "complete"
        errors.append((result.stderr or result.stdout).strip())
    return [], "unavailable: " + (errors[-1] if errors else "App-Liste nicht verfügbar")[:240]


def _matched_version(serial: str, package_id: str) -> str:
    result = _adb(serial, "shell", "dumpsys", "package", package_id, timeout=8)
    match = re.search(r"\bversionName=([^\s]+)", result.stdout)
    return match.group(1)[:100] if match else ""


def _profile_sources(request: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources = list(request.get("profile_sources") or [])
    if not sources:
        profile = load_profile(Path(request["profile_path"]))
        sources = [{key: profile[key] for key in ("id", "name", "version", "sha256")}]
    profile_meta = {
        "version": "combined" if len(sources) > 1 else sources[0]["version"],
        "sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
        "sources": sources, "selected_keywords": [],
    }
    return sources, profile_meta


def scan_android(request: dict[str, Any]) -> Path:
    started = time.monotonic()
    serial = str(request["adb_serial"])
    evidence = str(request["evidence"])
    result_root = Path(request["results_root"])
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    safe_evidence = "".join(char if char.isalnum() or char in "-_" else "_" for char in evidence)
    result_dir = result_root / f"{timestamp}_{safe_evidence}"
    (result_dir / "raw").mkdir(parents=True, exist_ok=False)
    logger = logging.getLogger(f"forensic-triage.android.{timestamp}.{safe_evidence}")
    handler = logging.FileHandler(result_dir / "scan.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    timings: dict[str, float] = {}
    try:
        phase = time.monotonic()
        state = _adb(serial, "get-state", timeout=6)
        if state.returncode or state.stdout.strip() != "device":
            raise RuntimeError("ANDROID-VERBINDUNG NICHT FREIGEGEBEN: Telefon entsperren und Verbindungsabfrage bestätigen.")
        device = {
            "path": f"android:{serial}", "serial": _prop(serial, "ro.serialno") or serial,
            "adb_serial": serial, "vendor": _prop(serial, "ro.product.manufacturer") or "Android",
            "model": _prop(serial, "ro.product.model") or "Android-Gerät",
            "android_version": _prop(serial, "ro.build.version.release"),
            "build_version": _prop(serial, "ro.build.display.id"), "media_type": "android",
            "connection_state": "authorized", "evidence": evidence, "scan_mode": "phone_crypto_quick",
            "access_mode": "adb_package_metadata", "write_operations_performed": False,
        }
        timings["device_information_seconds"] = round(time.monotonic() - phase, 3)
        rules = request["crypto_rules"]
        catalog = catalog_snapshot(request["filetype_catalog"]["categories"], request["filetype_catalog"]["version"])
        phase = time.monotonic()
        profiles = _profiles(serial)
        apps: list[dict[str, Any]] = []
        for profile in profiles:
            packages, status = _packages_for_user(serial, profile["id"])
            profile["status"] = status
            profile["app_count"] = len(packages)
            for package_id in packages:
                app = {"platform": "android", "app_id": package_id, "package_id": package_id, "bundle_id": "",
                       "name": package_id, "version": "", "profile_id": profile["id"], "profile_name": profile["name"]}
                app["matches"] = classify_app(app, rules)
                if app["matches"]:
                    app["name"] = app["matches"][0]["name"]
                    app["version"] = _matched_version(serial, package_id)
                apps.append(app)
        timings["application_inventory_seconds"] = round(time.monotonic() - phase, 3)
        phase = time.monotonic()
        app_hints = [
            {"name": app["name"], "package_id": app["package_id"], "version": app["version"],
             "profile_id": app["profile_id"], "profile_name": app["profile_name"], **match}
            for app in apps for match in app["matches"] if match.get("category") in CRYPTO_CATEGORIES
        ]
        apps_complete = all(profile["status"] == "complete" for profile in profiles)
        protected_visible = any(profile["protected"] for profile in profiles)
        coverage = [
            {"label": profile["name"], "status": "complete" if profile["status"] == "complete" else "unavailable",
             "message": f"{profile['app_count']} Benutzer-Apps erfasst" if profile["status"] == "complete" else profile["status"]}
            for profile in profiles
        ]
        coverage.append({
            "label": "Secure Folder / geschützter Bereich", "status": "complete" if protected_visible else "unknown",
            "message": "Als eigenes zugängliches Profil gemeldet." if protected_visible else "Nicht zuverlässig als zugängliches Profil feststellbar.",
        })
        assessment = "Relevante Krypto-Apps erkannt – Fachperson hinzuziehen" if app_hints else (
            "Keine Krypto-Apps in der erfassten Benutzer-App-Liste erkannt" if apps_complete else
            "App-Erfassung unvollständig – kein verlässlicher Negativbefund"
        )
        phone = {
            "platform": "android", "device": device, "apps": apps,
            "apps_status": "complete" if apps_complete else "incomplete", "apps_complete": apps_complete,
            "app_hints": app_hints, "profiles": profiles, "coverage": coverage, "complete": apps_complete,
            "assessment": assessment,
            "notice": "App-Treffer sind Triage-Hinweise. Wallet-Inhalte, Schlüssel, Seeds und App-Daten wurden nicht gelesen.",
        }
        timings["classification_and_persistence_seconds"] = round(time.monotonic() - phase, 3)
        _sources, profile_meta = _profile_sources(request)
        hits = {"total_matches": 0, "by_keyword": {}, "profile": profile_meta}
        containers = empty_catalog("not_opened_on_phone_quick_scan")
        summary = summarize([], [])
        summary.update({
            "evidence": evidence, "scan_started_utc": timestamp, "duration_seconds": round(time.monotonic() - started, 3),
            "scan_mode": "phone_crypto_quick", "phone_platform": "android", "timings": timings,
            "filetype_catalog": {"version": catalog["version"], "sha256": catalog["sha256"]}, "keyword_matches": 0,
            "archive_encryption": {"total": 0, "encrypted": 0, "unknown": 0},
            "container_index": {key: containers[key] for key in ("status", "duration_seconds", "containers_seen", "containers_indexed", "entries_indexed", "truncated")},
            "phone": {"platform": "android", "app_hint_count": len(app_hints), "apps_complete": apps_complete,
                      "assessment": assessment, "profile_count": len(profiles)},
            "crypto_rules": {"version": rules.get("version"), "sha256": rules.get("sha256")}, "crypto_file_hints": 0,
        })
        write_json(result_dir / "device.json", device)
        write_json(result_dir / "android.json", phone)
        write_json(result_dir / "phone.json", phone)
        write_json(result_dir / "apps.json", {"status": phone["apps_status"], "apps": apps, "profiles": profiles})
        write_json(result_dir / "crypto-hints.json", {"rules": summary["crypto_rules"], "app_hints": app_hints, "file_hints": []})
        write_json(result_dir / "crypto-rules.json", rules)
        write_json(result_dir / "filetype-catalog.json", catalog)
        write_json(result_dir / "partitions.json", [])
        write_json(result_dir / "container-index.json", containers)
        write_files_csv(result_dir / "files.csv", [])
        write_json(result_dir / "hits.json", hits)
        write_json(result_dir / "summary.json", summary)
        logger.info("Android quick scan complete profiles=%d apps=%d app_hints=%d complete=%s", len(profiles), len(apps), len(app_hints), apps_complete)
        return result_dir
    finally:
        logger.removeHandler(handler)
        handler.close()
