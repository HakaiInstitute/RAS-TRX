import os
from unittest.mock import patch

from ras_trx.utils import get_upgrade_version, resource_path


def test_resource_path_returns_absolute():
    assert os.path.isabs(resource_path("resources/icon.png"))


def test_resource_path_contains_relative_component():
    result = resource_path("resources/icon.png")
    assert result.endswith(os.path.join("resources", "icon.png"))


def test_get_upgrade_version_none_when_empty_releases():
    with patch("ras_trx.utils._get_available_versions", return_value=[]):
        assert get_upgrade_version("v1.0.0") is None


def test_get_upgrade_version_none_on_fetch_error():
    with patch("ras_trx.utils._get_available_versions", return_value=None):
        assert get_upgrade_version("v1.0.0") is None


def test_get_upgrade_version_returns_newer_stable():
    releases = [
        {"tag_name": "v2.0.0", "prerelease": False, "draft": False, "html_url": "..."},
        {"tag_name": "v1.0.0", "prerelease": False, "draft": False, "html_url": "..."},
    ]
    with patch("ras_trx.utils._get_available_versions", return_value=releases):
        result = get_upgrade_version("v1.0.0")
    assert result is not None
    assert result["tag_name"] == "v2.0.0"


def test_get_upgrade_version_skips_prerelease():
    releases = [
        {
            "tag_name": "v2.0.0-beta",
            "prerelease": True,
            "draft": False,
            "html_url": "...",
        },
        {"tag_name": "v1.0.0", "prerelease": False, "draft": False, "html_url": "..."},
    ]
    with patch("ras_trx.utils._get_available_versions", return_value=releases):
        assert get_upgrade_version("v1.0.0") is None


def test_get_upgrade_version_skips_draft():
    releases = [
        {"tag_name": "v2.0.0", "prerelease": False, "draft": True, "html_url": "..."},
        {"tag_name": "v1.0.0", "prerelease": False, "draft": False, "html_url": "..."},
    ]
    with patch("ras_trx.utils._get_available_versions", return_value=releases):
        assert get_upgrade_version("v1.0.0") is None
