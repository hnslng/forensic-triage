import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", [
    "scripts/install_debian.sh",
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
