from click.testing import CliRunner

from snaffle.banner import render_banner
from snaffle.cli import main


def test_render_banner_contains_name():
    plain = render_banner(color=False)
    assert "snaffle" in plain.lower() or "SNAFFLE" in plain
    # multi-line ASCII art
    assert plain.count("\n") >= 3


def test_render_banner_is_solid_block_wordmark():
    # Old-school solid block-pixel letters, like refchecker's wordmark.
    plain = render_banner(color=False)
    assert "█" in plain
    # The wordmark is 5 rows tall.
    block_rows = [line for line in plain.splitlines() if "█" in line]
    assert len(block_rows) >= 5


def test_render_banner_colour_includes_ansi():
    coloured = render_banner(color=True)
    assert "\x1b[" in coloured


def test_render_banner_uses_truecolor_gradient():
    # A cyan→green vertical gradient means several distinct 24-bit colours.
    coloured = render_banner(color=True)
    truecolor_codes = {
        seg.split("m")[0]
        for seg in coloured.split("\x1b[38;2;")[1:]
    }
    assert len(truecolor_codes) >= 3


def test_render_banner_no_color_is_plain():
    assert "\x1b[" not in render_banner(color=False)


def test_group_help_lists_the_activities():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "search" in result.output
    assert "download" in result.output


def test_run_help_shows_academic_argument():
    result = CliRunner().invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "ACADEMIC" in result.output


def test_list_plugins_lists_known_plugins():
    result = CliRunner().invoke(main, ["list-plugins"])
    assert result.exit_code == 0
    assert "crossref" in result.output
    assert "arxiv" in result.output


def test_banner_painted_to_stderr_not_stdout():
    # Banner goes to stderr so stdout (the plugin list) can be redirected cleanly.
    result = CliRunner().invoke(main, ["list-plugins"])
    assert result.exit_code == 0
    assert "crossref" in result.stdout
    assert "snaffle" in result.stderr  # banner tagline on stderr
    assert "snaffle" not in result.stdout
