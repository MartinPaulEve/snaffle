from click.testing import CliRunner

from snaffle.banner import render_banner
from snaffle.cli import main


def test_render_banner_contains_name():
    plain = render_banner(color=False)
    assert "snaffle" in plain.lower() or "SNAFFLE" in plain
    # multi-line ASCII art
    assert plain.count("\n") >= 3


def test_render_banner_colour_includes_ansi():
    coloured = render_banner(color=True)
    assert "\x1b[" in coloured


def test_help_shows_usage():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "ACADEMIC" in result.output


def test_list_plugins_lists_known_plugins():
    result = CliRunner().invoke(main, ["--list-plugins"])
    assert result.exit_code == 0
    assert "crossref" in result.output
    assert "arxiv" in result.output


def test_banner_painted_to_stderr_not_stdout():
    # Banner goes to stderr so stdout (the plugin list) can be redirected cleanly.
    result = CliRunner().invoke(main, ["--list-plugins"])
    assert result.exit_code == 0
    assert "crossref" in result.stdout
    assert "snaffle" in result.stderr  # banner tagline on stderr
    assert "snaffle" not in result.stdout
