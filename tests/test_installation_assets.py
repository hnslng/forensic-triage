import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", [
    "scripts/install_debian.sh",
    "scripts/bootstrap_pi.sh",
    "scripts/configure_pi_network.sh",
    "scripts/apply_pi_firewall.sh",
])
def test_installation_shell_scripts_have_valid_syntax(script: str) -> None:
    subprocess.run(["bash", "-n", str(ROOT / script)], check=True)


def test_pi_network_template_uses_documented_development_values() -> None:
    template = (ROOT / "deploy/pi-network.env.example").read_text(encoding="utf-8")
    assert "TRIAGEBOX_WIFI_SSID=TRIAGEBOX" in template
    assert "TRIAGEBOX_WIFI_PASSWORD=triagebox123" in template
    assert "DEVELOPMENT PASSWORD ONLY" in template


def test_wifi_password_is_not_passed_to_web_service() -> None:
    web_environment = (ROOT / "deploy/triage.env.example").read_text(encoding="utf-8")
    web_service = (ROOT / "deploy/forensic-triage-web.service.in").read_text(encoding="utf-8")
    assert "TRIAGEBOX_WIFI_PASSWORD" not in web_environment
    assert "pi-network.env" not in web_service


def test_public_bootstrap_targets_expected_repository() -> None:
    bootstrap = (ROOT / "scripts/bootstrap_pi.sh").read_text(encoding="utf-8")
    assert "https://github.com/hnslng/forensic-triage.git" in bootstrap
    assert 'exec "$INSTALL_ROOT/scripts/install_debian.sh" --pi' in bootstrap


def test_debian_installer_includes_archive_directory_tool() -> None:
    installer = (ROOT / "scripts/install_debian.sh").read_text(encoding="utf-8")
    assert "7zip nginx" in installer


def test_install_and_update_enable_bounded_persistent_journal() -> None:
    installer = (ROOT / "scripts/install_debian.sh").read_text(encoding="utf-8")
    updater = (ROOT / "scripts/update_triagebox.sh").read_text(encoding="utf-8")
    journal = (ROOT / "deploy/forensic-triage-journald.conf").read_text(encoding="utf-8")
    assert "Storage=persistent" in journal
    assert "SystemMaxUse=64M" in journal
    assert "MaxRetentionSec=14day" in journal
    assert "forensic-triage-journald.conf" in installer
    assert "forensic-triage-journald.conf" in updater
    assert "journalctl --flush" in installer
    assert "journalctl --flush" in updater


def test_manual_install_switches_runtime_link_to_tested_checkout() -> None:
    installer = (ROOT / "scripts/install_debian.sh").read_text(encoding="utf-8")
    assert 'ln -sfn "$PROJECT_ROOT" "$RUNTIME_LINK"' in installer
    assert '[[ -e "$RUNTIME_LINK" && ! -L "$RUNTIME_LINK" ]]' in installer


def test_pi_installer_configures_port_free_local_url() -> None:
    installer = (ROOT / "scripts/install_debian.sh").read_text(encoding="utf-8")
    network_script = (ROOT / "scripts/configure_pi_network.sh").read_text(encoding="utf-8")
    nginx_template = (ROOT / "deploy/forensic-triage-nginx.conf.in").read_text(encoding="utf-8")
    assert "nginx.service" in installer
    assert "http://${TRIAGEBOX_HOSTNAME:-triagebox}.local/" in installer
    assert "FORENSIC_TRIAGE_WEB_HOST=127.0.0.1" in network_script
    assert "proxy_pass http://127.0.0.1:@WEB_PORT@" in nginx_template
    assert "allow 10.0.0.0/8" in nginx_template
    assert "allow 172.16.0.0/12" in nginx_template
    assert "allow 192.168.0.0/16" in nginx_template
    assert "listen [::]" not in nginx_template


def test_deliberate_update_uses_release_tags_and_atomic_runtime_link() -> None:
    updater_path = ROOT / "scripts/update_triagebox.sh"
    updater = updater_path.read_text(encoding="utf-8")
    assert updater_path.stat().st_mode & 0o111
    assert "tag --list 'v[0-9]*'" in updater
    assert "git -C \"$CURRENT_ROOT\" worktree add --detach" in updater
    assert 'mv -Tf "${RUNTIME_LINK}.next" "$RUNTIME_LINK"' in updater
    assert "VORVERSION WIEDERHERGESTELLT" in updater
    assert "forensic-triage-nginx.conf.in" in updater
    assert "systemctl daemon-reload" in updater


def test_deliberate_update_accepts_linked_git_worktree_releases() -> None:
    updater = (ROOT / "scripts/update_triagebox.sh").read_text(encoding="utf-8")
    assert "rev-parse --is-inside-work-tree" in updater
    assert '! -d "$CURRENT_ROOT/.git"' not in updater


def test_update_timer_checks_only_and_never_installs() -> None:
    timer = (ROOT / "deploy/forensic-triage-update-check.timer").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=1d" in timer
    assert "forensic-triage-update@check.service" in timer
    assert "forensic-triage-update@install.service" not in timer
