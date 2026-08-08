"""Click command-line interface for snaffle."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import click
import httpx

from snaffle.banner import print_banner
from snaffle.config import openalex_excludes, parse_credentials, plugin_dirs
from snaffle.registry import (
    discover_plugin_classes,
    download_plugins,
    instantiate_plugins,
    search_plugins,
)
from snaffle.secrets import SecretStore
from snaffle.services import ServiceContext
from snaffle.services.kagi import KagiClient

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 snaffle"
)


def build_context(env: dict) -> ServiceContext:
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
            logger.warning("could not resolve Kagi key, discovery disabled: %s", exc)

    return ServiceContext(
        http=http,
        secrets=secrets,
        kagi=kagi,
        credentials=parse_credentials(env),
        config={
            "unpaywall_email": env.get("SNAFFLE_UNPAYWALL_EMAIL", ""),
            "crossref_mailto": env.get("SNAFFLE_CROSSREF_MAILTO", ""),
            "orcid": env.get("SNAFFLE_ORCID", ""),
            "openalex_excludes": openalex_excludes(env),
        },
        logger=logger,
    )


def load_plugins(ctx: ServiceContext, env: dict, only, disable):
    classes = discover_plugin_classes(plugin_dirs(env))
    return instantiate_plugins(classes, ctx, only=list(only) or None, disable=list(disable))


def _configure_logging():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
    logger = logging.getLogger("snaffle")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger


@click.command()
@click.argument("academic", required=False)
@click.option("--output", "-o", default="output", help="Output directory.")
@click.option("--only", multiple=True, help="Use only these plugins (by name).")
@click.option("--disable", multiple=True, help="Disable these plugins (by name).")
@click.option("--style", default="chicago", help="Citation style for the bibliography.")
@click.option("--orcid", default=None, help="Academic's ORCID iD, to disambiguate authors.")
@click.option("--list-plugins", is_flag=True, help="List available plugins and exit.")
@click.option("--no-download", is_flag=True, help="Search only; do not download.")
def main(academic, output, only, disable, style, orcid, list_plugins, no_download):
    """Assemble an archive of an ACADEMIC's published outputs."""
    print_banner(stream=sys.stderr)
    env = dict(os.environ)
    if orcid:
        env["SNAFFLE_ORCID"] = orcid
    ctx = build_context(env)
    plugins = load_plugins(ctx, env, only, disable)

    if list_plugins:
        for p in sorted(plugins, key=lambda p: p.name):
            caps = []
            from snaffle.plugins.base import is_download_plugin, is_search_plugin

            if is_search_plugin(p):
                caps.append("search")
            if is_download_plugin(p):
                caps.append("download")
            click.echo(f"{p.name:<16} [{', '.join(caps)}]  {p.description}")
        return

    if not academic:
        raise click.UsageError("Provide an ACADEMIC name, or use --list-plugins.")

    logger = _configure_logging()
    from snaffle.pipeline import run

    report = run(
        academic,
        Path(output),
        search_plugins(plugins),
        download_plugins(plugins),
        logger=logger,
        style=style,
        download=not no_download,
    )
    logger.info(
        "done: %d found, %d downloaded, %d failed",
        len(report.found),
        len(report.downloaded),
        len(report.failed),
    )


if __name__ == "__main__":
    main()
