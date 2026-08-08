import pytest
from click.testing import CliRunner

from snaffle import pipeline
from snaffle.cli import main
from snaffle.models import Publication


@pytest.fixture
def offline(monkeypatch):
    """Replace network-touching layers so CLI dispatch can be tested offline."""
    calls = []
    monkeypatch.setattr("snaffle.cli.build_context", lambda env, orcid_override=None: object())
    monkeypatch.setattr("snaffle.cli.load_plugins", lambda ctx, env, only, disable: [])

    def recorder(name):
        def _f(academic, *args, **kwargs):
            calls.append(name)
            return pipeline.RunReport(academic)

        return _f

    monkeypatch.setattr(pipeline, "run", recorder("run"))
    monkeypatch.setattr(pipeline, "search_phase", recorder("search"))
    monkeypatch.setattr(pipeline, "download_phase", recorder("download"))
    return calls


def test_bare_invocation_runs_full_workflow(offline):
    result = CliRunner().invoke(main, ["Martin Paul Eve"])
    assert result.exit_code == 0, result.output
    assert offline == ["run"]


def test_run_subcommand_runs_full_workflow(offline):
    result = CliRunner().invoke(main, ["run", "Martin Paul Eve"])
    assert result.exit_code == 0, result.output
    assert offline == ["run"]


def test_search_subcommand_runs_search_only(offline):
    result = CliRunner().invoke(main, ["search", "Martin Paul Eve"])
    assert result.exit_code == 0, result.output
    assert offline == ["search"]


def test_download_subcommand_runs_download_only(offline, monkeypatch):
    monkeypatch.setattr("snaffle.manifest.read_manifest", lambda out, a: [Publication(title="X")])
    monkeypatch.setattr("snaffle.manifest.write_manifest", lambda out, a, pubs: None)
    result = CliRunner().invoke(main, ["download", "Martin Paul Eve"])
    assert result.exit_code == 0, result.output
    assert offline == ["download"]


def test_download_without_manifest_gives_clear_error(offline, monkeypatch):
    monkeypatch.setattr("snaffle.manifest.read_manifest", lambda out, a: None)
    result = CliRunner().invoke(main, ["download", "Never Searched"])
    assert result.exit_code != 0
    assert "search" in result.output.lower()


def test_nuke_deletes_directory_before_activity(offline, monkeypatch):
    seen = {}

    def fake_nuke(out, author):
        seen["author"] = author
        return True

    monkeypatch.setattr("snaffle.cli.nuke_author_dir", fake_nuke)
    result = CliRunner().invoke(main, ["search", "Ada Lovelace", "--nuke"])
    assert result.exit_code == 0, result.output
    assert seen["author"] == "Ada Lovelace"
    assert offline == ["search"]


def test_download_nuke_preserves_list_across_wipe(offline, monkeypatch):
    order = []
    monkeypatch.setattr(
        "snaffle.manifest.read_manifest",
        lambda out, a: order.append("read") or [Publication(title="X")],
    )
    monkeypatch.setattr("snaffle.manifest.write_manifest", lambda out, a, pubs: None)
    monkeypatch.setattr(
        "snaffle.cli.nuke_author_dir", lambda out, a: order.append("nuke") or True
    )
    result = CliRunner().invoke(main, ["download", "Ada Lovelace", "--nuke"])
    assert result.exit_code == 0, result.output
    # The saved list is read BEFORE the directory is wiped.
    assert order == ["read", "nuke"]
