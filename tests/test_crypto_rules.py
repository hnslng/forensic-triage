"""Conservative shared metadata rules and persisted snapshots."""

import json

import pytest

from forensic_triage.crypto_rules import (
    bundled_rules, classify_app, classify_file, find_file_hints, load_rules, save_rules, seed_rules, snapshot,
)
from forensic_triage.settings import SettingsConflict


def test_bundled_app_categories_and_neutral_matches():
    rules = bundled_rules()
    assert classify_app({"name": "MetaMask", "bundle_id": "io.metamask.MetaMask"}, rules)[0]["category"] == "wallet"
    assert classify_app({"name": "Signal", "bundle_id": ""}, rules)[0]["relevance"] == "neutral"
    assert classify_app({"name": "WhatsApp", "bundle_id": ""}, rules)[0]["category"] == "messenger"
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
    path.write_text(json.dumps({"version": 2, "app_rules": [], "file_rules": [], "sha256": "wrong"}))
    with pytest.raises(ValueError):
        load_rules(path)


def test_neutral_categories_cannot_become_crypto_alerts():
    rules = bundled_rules()
    bad = {"app_rules": [dict(item) for item in rules["app_rules"]], "file_rules": rules["file_rules"]}
    neutral = next(item for item in bad["app_rules"] if item["category"] == "messenger")
    neutral["relevance"] = "high"
    with pytest.raises(ValueError):
        snapshot(bad)


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
    assert next(item for item in result["app_rules"] if item["id"] == "metamask")["bundle_ids"] == []
    assert next(item for item in result["app_rules"] if item["id"] == "own-wallet")["bundle_ids"] == ["org.example.own"]
    assert any(item["id"] == "own-export" for item in result["file_rules"])
