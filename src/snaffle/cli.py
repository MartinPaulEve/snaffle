"""Click command-line interface for snaffle.

``snaffle "Name"`` runs the whole workflow. ``snaffle search "Name"`` builds the
publication list only; ``snaffle download "Name"`` fetches full text for a list
built earlier. ``--nuke`` wipes the academic's directory first.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import click
import httpx

from snaffle.banner import print_banner
from snaffle.config import load_env_file, openalex_excludes, parse_credentials, plugin_dirs
from snaffle.output import nuke_author_dir
from snaffle.registry import (
    discover_plugin_classes,
    download_plugins,
    instantiate_plugins,
    search_plugins,
)
from snaffle.secrets import SecretStore
from snaffle.services import ServiceContext
from snaffle.services.kagi import KagiClient
from snaffle.services.orcid_resolver import OrcidResolver

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 snaffle"
)


def build_context(env: dict, orcid_override: str | None = None) -> ServiceContext:
    """Assemble the ServiceContext shared by every plugin."""
    http = httpx.Client(
        headers={"User-Agent": DEFAULT_USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
    )
    secrets = SecretStore()
    logger = logging.getLogger("snaffle")

    kagi = None
    kagi_ref = env.get("SNAFFLE_KAGI_KEY", "")
    if kagi_ref:
        try:
            kagi = KagiClient(secrets.resolve(kagi_ref), http=http)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "could not resolve Kagi key (is 1Password signed in? try `op signin`); "
                "discovery disabled: %s",
                exc,
            )

    return ServiceContext(
        http=http,
        secrets=secrets,
        kagi=kagi,
        orcid_resolver=OrcidResolver(http, override=orcid_override or None),
        credentials=parse_credentials(env),
        config={
            "unpaywall_email": env.get("SNAFFLE_UNPAYWALL_EMAIL", ""),
            "crossref_mailto": env.get("SNAFFLE_CROSSREF_MAILTO", ""),
            "openalex_excludes": openalex_excludes(env),
        },
        logger=logger,
    )


def load_plugins(ctx: ServiceContext, env: dict, only, disable):
    classes = discover_plugin_classes(plugin_dirs(env))
    return instantiate_plugins(classes, ctx, only=list(only) or None, disable=list(disable))


def _environment() -> dict:
    """The process environment overlaid on values from a local ``.env`` file."""
    return {**load_env_file(".env"), **os.environ}


def _configure_logging():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
    logger = logging.getLogger("snaffle")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger


class DefaultGroup(click.Group):
    """A group that dispatches an unrecognised first argument to a default command.

    This is what lets ``snaffle "Martin Paul Eve"`` mean ``snaffle run
    "Martin Paul Eve"`` while ``snaffle search "..."`` still works.
    """

    default_command = "run"

    def parse_args(self, ctx, args):
        if args and args[0] not in self.commands and args[0] not in ("--help", "-h"):
            args = [self.default_command, *args]
        return super().parse_args(ctx, args)


@click.group(cls=DefaultGroup, invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Assemble an archive of an academic's published outputs."""
    print_banner(stream=sys.stderr)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _shared_options(func):
    func = click.argument("academic")(func)
    func = click.option("--output", "-o", default="output", help="Output directory.")(func)
    func = click.option("--only", multiple=True, help="Use only these plugins (by name).")(func)
    func = click.option("--disable", multiple=True, help="Disable these plugins (by name).")(func)
    func = click.option(
        "--nuke",
        is_flag=True,
        help="Delete the academic's existing output directory before starting.",
    )(func)
    return func


def _run_activity(academic, output, only, disable, nuke, style, orcid, do_search, do_download):
    from snaffle import manifest, pipeline

    env = _environment()
    ctx = build_context(env, orcid_override=orcid)
    plugins = load_plugins(ctx, env, only, disable)
    logger = _configure_logging()
    out = Path(output)

    # For download-only, read the saved list before any --nuke wipes it.
    saved = None
    if do_download and not do_search:
        saved = manifest.read_manifest(out, academic)
        if saved is None:
            raise click.UsageError(
                f"No saved publication list for '{academic}'. "
                f'Run: snaffle search "{academic}"'
            )

    if nuke:
        removed = nuke_author_dir(out, academic)
        logger.info("nuke: %s", "removed existing directory" if removed else "nothing to remove")

    if do_search and do_download:
        report = pipeline.run(
            academic, out, search_plugins(plugins), download_plugins(plugins),
            logger=logger, style=style,
        )
    elif do_search:
        report = pipeline.search_phase(
            academic, out, search_plugins(plugins), logger=logger, style=style
        )
    else:
        report = pipeline.download_phase(
            academic, out, download_plugins(plugins), saved, logger=logger
        )
        # Restore the manifest so the list survives a --nuke.
        manifest.write_manifest(out, academic, saved)

    logger.info(
        "done: %d found, %d downloaded, %d failed",
        len(report.found),
        len(report.downloaded),
        len(report.failed),
    )


@main.command(help="Search for and download an academic's works (the full workflow).")
@_shared_options
@click.option("--style", default="chicago", help="Citation style for the bibliography.")
@click.option("--orcid", default=None, help="Override the discovered ORCID iD.")
def run(academic, output, only, disable, nuke, style, orcid):
    _run_activity(academic, output, only, disable, nuke, style, orcid,
                  do_search=True, do_download=True)


@main.command(help="Only build the publication list (writes the bibliography; no downloads).")
@_shared_options
@click.option("--style", default="chicago", help="Citation style for the bibliography.")
@click.option("--orcid", default=None, help="Override the discovered ORCID iD.")
def search(academic, output, only, disable, nuke, style, orcid):
    _run_activity(academic, output, only, disable, nuke, style, orcid,
                  do_search=True, do_download=False)


@main.command(help="Only download full text for a list built earlier by 'search'.")
@_shared_options
def download(academic, output, only, disable, nuke):
    _run_activity(academic, output, only, disable, nuke, style="chicago", orcid=None,
                  do_search=False, do_download=True)


@main.command(name="list-plugins", help="List available plugins and exit.")
def list_plugins_cmd():
    from snaffle.plugins.base import is_download_plugin, is_search_plugin

    env = _environment()
    ctx = build_context(env)
    plugins = load_plugins(ctx, env, (), ())
    for p in sorted(plugins, key=lambda p: p.name):
        caps = []
        if is_search_plugin(p):
            caps.append("search")
        if is_download_plugin(p):
            caps.append("download")
        click.echo(f"{p.name:<16} [{', '.join(caps)}]  {p.description}")


if __name__ == "__main__":
    main()
