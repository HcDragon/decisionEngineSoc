"""
Tests for settings, paths, and YAML config file validation.
"""
import yaml
import csv
from soc.backend.app.config import settings


def test_config_paths_exist():
    assert settings.config_path.exists(), f"Config dir not found at {settings.config_path}"
    assert settings.assets_file.exists(), f"Assets file not found at {settings.assets_file}"
    assert settings.policies_file.exists(), f"Policies file not found at {settings.policies_file}"
    assert settings.allowlist_file.exists(), f"Allowlist file not found at {settings.allowlist_file}"
    assert settings.playbooks_dir.exists(), f"Playbooks dir not found at {settings.playbooks_dir}"
    assert settings.blocklist_file.exists(), f"Blocklist file not found at {settings.blocklist_file}"


def test_assets_yaml_valid():
    with open(settings.assets_file, "r") as f:
        data = yaml.safe_load(f)
    assert "assets" in data
    assert len(data["assets"]) > 0
    assert "attacker_pool" in data
    assert "default_criticality" in data

    # Check required asset fields
    first_asset = data["assets"][0]
    for key in ["ip", "name", "role", "criticality", "owner", "isolatable"]:
        assert key in first_asset


def test_policies_yaml_valid():
    with open(settings.policies_file, "r") as f:
        data = yaml.safe_load(f)
    assert "version" in data
    assert "scoring" in data
    assert "tiers" in data
    assert "attack_families" in data
    assert "rules" in data
    assert len(data["rules"]) > 0


def test_allowlist_yaml_valid():
    with open(settings.allowlist_file, "r") as f:
        data = yaml.safe_load(f)
    assert "allowlist" in data
    assert len(data["allowlist"]) > 0
    ips = [entry["ip"] for entry in data["allowlist"]]
    assert "127.0.0.1" in ips


def test_playbooks_yaml_valid():
    playbook_files = list(settings.playbooks_dir.glob("*.yaml"))
    assert len(playbook_files) >= 5
    for pb_file in playbook_files:
        with open(pb_file, "r") as f:
            pb = yaml.safe_load(f)
        assert "id" in pb
        assert "name" in pb
        assert "steps" in pb
        assert len(pb["steps"]) > 0


def test_blocklist_csv_valid():
    with open(settings.blocklist_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0
    assert "ip" in rows[0]
    assert "threat_score" in rows[0]
