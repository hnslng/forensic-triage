"""Conservative shared metadata rules and persisted snapshots."""

import json

import pytest

from forensic_triage.crypto_rules import (
    bundled_rules, classify_app, classify_file, find_file_hints, load_rules, merge_rules, save_rules, seed_rules, snapshot,
)
from forensic_triage.settings import SettingsConflict


def test_bundled_app_categories_and_neutral_matches():
    rules = bundled_rules()
    assert classify_app({"name": "MetaMask", "bundle_id": "io.metamask.MetaMask"}, rules)[0]["category"] == "wallet"
    assert classify_app({"name": "Signal", "bundle_id": ""}, rules)[0]["relevance"] == "neutral"
    assert classify_app({"name": "WhatsApp", "bundle_id": ""}, rules)[0]["category"] == "messenger"
    assert classify_app({"name": "\u200eWhatsApp", "bundle_id": ""}, rules)[0]["category"] == "messenger"
    assert classify_app({"name": "Some MetaMask Guide", "bundle_id": ""}, rules) == []


def test_file_rules_need_name_or_context_and_do_not_read_contents():
    rules = bundled_rules()
    assert classify_file("wallet.dat", "dat", rules)[0]["id"] == "file-wallet-dat"
    assert classify_file("private_key.txt", "txt", rules)[0]["id"] == "file-seed-recovery"
    assert classify_file("misc/binance_transactions.csv", "csv", rules)[0]["id"] == "file-exchange-export"
    assert classify_file("misc/binance_logo.csv", "csv", rules) == []
    assert classify_file("not-wallet.exe", "exe", rules) == []
    files = [{"path": "wallet.dat", "extension": "dat", "source": "medium"},
             {"path": "holiday.jpg", "extension": "jpg", "source": "medium"}]
    hints = find_file_hints(files, rules)
    assert len(hints) == 1 and hints[0]["path"] == "wallet.dat"


def test_rule_version_and_conflict_preserve_prior_scan_snapshot(tmp_path):
    path = tmp_path / "crypto-rules.json"
    seed_rules(path)
    first = load_rules(path)
    changed = {"app_rules": [dict(item) for item in first["app_rules"]],
               "file_rules": [dict(item) for item in first["file_rules"]]}
    changed["app_rules"][0]["enabled"] = False
    second = save_rules(path, changed, first["sha256"])
    assert second["version"] == first["version"] + 1
    assert first["app_rules"][0]["enabled"] is True
    assert load_rules(path)["sha256"] == second["sha256"]
    with pytest.raises(SettingsConflict):
        save_rules(path, changed, first["sha256"])
    path.write_text(json.dumps({"version": 3, "app_rules": [], "file_rules": [], "backup_rules": [], "sha256": "wrong"}))
    with pytest.raises(ValueError):
        load_rules(path)


def test_neutral_categories_cannot_become_crypto_alerts():
    rules = bundled_rules()
    bad = {"app_rules": [dict(item) for item in rules["app_rules"]], "file_rules": rules["file_rules"]}
    neutral = next(item for item in bad["app_rules"] if item["category"] == "messenger")
    neutral["relevance"] = "high"
    with pytest.raises(ValueError):
        snapshot(bad)


def test_banking_apps_remain_neutral():
    rules = bundled_rules()
    revolut = classify_app({"name": "Revolut", "app_id": "com.revolut.revolut", "platform": "android"}, rules)
    assert revolut
    assert revolut[0]["category"] == "banking"
    assert revolut[0]["relevance"] == "neutral"
    trade = classify_app({"name": "Trade Republic", "app_id": "de.traderepublic.app", "platform": "android"}, rules)
    assert trade[0]["relevance"] == "neutral"


def test_ios_and_android_id_matching():
    rules = bundled_rules()
    ios = classify_app({"name": "MetaMask", "bundle_id": "io.metamask.ios", "platform": "ios"}, rules)
    android = classify_app({"name": "MetaMask", "app_id": "io.metamask", "platform": "android"}, rules)
    assert ios[0]["category"] == "wallet"
    assert android[0]["category"] == "wallet"


def test_alias_and_former_name_matching():
    rules = bundled_rules()
    xaman = classify_app({"name": "Xaman", "bundle_id": "", "platform": "ios"}, rules)
    assert xaman
    xumm = classify_app({"name": "Xumm", "bundle_id": "", "platform": "ios"}, rules)
    assert xumm
    assert xaman[0]["id"] == xumm[0]["id"]


def test_legacy_rule_matches_old_app_name():
    rules = bundled_rules()
    hit = classify_app({"name": "Credit Suisse", "bundle_id": "", "platform": "ios"}, rules)
    assert hit
    assert hit[0]["status"] == "legacy"


def test_unknown_crypto_candidate_is_low_relevance():
    rules = bundled_rules()
    hit = classify_app({"name": "My Bitcoin Wallet", "bundle_id": "", "platform": "android"}, rules)
    assert hit
    assert hit[0]["id"] == "unknown-crypto-candidate"
    assert hit[0]["relevance"] == "low"


def test_verified_ids_are_counted():
    rules = bundled_rules()
    verified = sum(1 for rule in rules["app_rules"] if rule.get("verified"))
    unverified = sum(1 for rule in rules["app_rules"] if not rule.get("verified"))
    assert verified >= 50
    assert unverified >= 0


def test_large_rule_set_scales_without_validation_error():
    rules = bundled_rules()
    base = rules["app_rules"][0]
    many = []
    for index in range(1500):
        many.append({
            **base,
            "id": f"scale-{index:04d}",
            "name": f"Scale App {index}",
            "ios_bundle_ids": [],
            "android_package_ids": [f"com.scale.app{index}"],
            "aliases": [],
            "former_names": [],
            "terms": [],
        })
    data = {"app_rules": many, "file_rules": rules["file_rules"], "backup_rules": rules["backup_rules"]}
    result = snapshot(data)
    assert result["sha256"]


def test_merge_rules_preserves_local_changes_and_adds_new_defaults(tmp_path):
    defaults = bundled_rules()
    local = snapshot({
        "app_rules": [
            {"id": "metamask", "name": "MetaMask", "category": "wallet", "relevance": "high", "enabled": False,
             "ios_bundle_ids": ["io.metamask.ios"], "android_package_ids": ["io.metamask"], "aliases": [], "former_names": [], "terms": [],
             "status": "active", "verified": True, "source": "", "last_verified": "", "regions": []},
            {"id": "own-wallet", "name": "Own Wallet", "category": "wallet", "relevance": "high", "enabled": True,
             "ios_bundle_ids": ["org.example.own"], "android_package_ids": [], "aliases": [], "former_names": [], "terms": [],
             "status": "active", "verified": False, "source": "", "last_verified": "", "regions": []},
        ],
        "file_rules": [],
        "backup_rules": [],
    }, 2)
    merged = merge_rules(local, defaults)
    assert any(rule["id"] == "own-wallet" for rule in merged["app_rules"])
    metamask = next(rule for rule in merged["app_rules"] if rule["id"] == "metamask")
    assert metamask["enabled"] is False  # local change preserved
    assert any(rule["id"] == "ledger-live" for rule in merged["app_rules"])
    assert len(merged["backup_rules"]) == len(defaults["backup_rules"])


def test_merge_rules_honors_deleted_default_tombstones(tmp_path):
    defaults = bundled_rules()
    local = snapshot({
        "app_rules": [],
        "file_rules": [],
        "backup_rules": [],
        "deleted_default_rule_ids": ["metamask"],
    }, 3)
    merged = merge_rules(local, defaults)
    assert not any(rule["id"] == "metamask" for rule in merged["app_rules"])
    assert any(rule["id"] == "ledger-live" for rule in merged["app_rules"])


def test_seed_rules_merges_new_defaults_into_existing_local_file(tmp_path):
    path = tmp_path / "crypto-rules.json"
    # Simulate an Alpha 61 local file: small set, no backup_rules, no tombstones.
    old_local = snapshot({
        "app_rules": [
            {"id": "metamask", "name": "MetaMask", "category": "wallet", "relevance": "high", "enabled": True,
             "ios_bundle_ids": ["io.metamask.ios"], "android_package_ids": ["io.metamask"], "aliases": [], "former_names": [], "terms": [],
             "status": "active", "verified": True, "source": "", "last_verified": "", "regions": []},
            {"id": "own-wallet", "name": "Own Wallet", "category": "wallet", "relevance": "high", "enabled": True,
             "ios_bundle_ids": ["org.example.own"], "android_package_ids": [], "aliases": [], "former_names": [], "terms": [],
             "status": "active", "verified": False, "source": "", "last_verified": "", "regions": []},
        ],
        "file_rules": [],
        "backup_rules": [],
    }, 2)
    path.write_text(json.dumps(old_local, ensure_ascii=False, indent=2))
    seed_rules(path)
    result = load_rules(path)
    assert len(result["app_rules"]) >= len(bundled_rules()["app_rules"]) + 1  # defaults + own-wallet
    assert len(result["backup_rules"]) == len(bundled_rules()["backup_rules"])
    assert any(rule["id"] == "own-wallet" for rule in result["app_rules"])
    assert result["version"] == old_local["version"] + 1


def test_save_rules_clears_tombstone_when_default_rule_is_recreated(tmp_path):
    defaults = bundled_rules()
    default_ids = frozenset(rule["id"] for kind in ("app_rules", "file_rules", "backup_rules") for rule in defaults[kind])
    path = tmp_path / "crypto-rules.json"
    current = snapshot({"app_rules": [], "file_rules": [], "backup_rules": [], "deleted_default_rule_ids": ["metamask"]}, 3)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2))
    payload = {
        "app_rules": [dict(item) for item in defaults["app_rules"] if item["id"] == "metamask"],
        "file_rules": [],
        "backup_rules": [],
        "deleted_default_rule_ids": ["metamask"],
    }
    updated = save_rules(path, payload, current["sha256"], default_rule_ids=default_ids)
    assert "metamask" not in updated.get("deleted_default_rule_ids", [])
    assert any(rule["id"] == "metamask" for rule in updated["app_rules"])


def test_legacy_operator_rules_migrate_without_unverified_bundled_ids(tmp_path):
    from importlib.resources import files

    old = json.loads(files("forensic_triage").joinpath("data/iphone-triage.json").read_text())
    old["app_rules"].append({"id": "own-wallet", "category": "Wallet", "bundle_ids": ["org.example.own"],
                             "name_contains": ["Own Wallet"]})
    old["file_rules"].append({"id": "own-export", "label": "Eigener Export", "path_contains": ["owncoin"],
                              "extensions": ["csv"]})
    legacy = tmp_path / "iphone-triage.json"
    legacy.write_text(json.dumps(old))
    target = tmp_path / "crypto-rules.json"
    seed_rules(target, legacy)
    result = load_rules(target)
    assert next(item for item in result["app_rules"] if item["id"] == "trezor-suite")["bundle_ids"] == []
    assert next(item for item in result["app_rules"] if item["id"] == "own-wallet")["bundle_ids"] == ["org.example.own"]
    assert any(item["id"] == "own-export" for item in result["file_rules"])
