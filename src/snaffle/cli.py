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
from snaffle.exclude import parse_exclusions
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


def _exclusions(env, cli_exclude) -> list[str]:
    """Combine SNAFFLE_EXCLUDE terms with any --exclude terms (lowercased)."""
    terms = parse_exclusions(env)
    terms.extend(t.strip().lower() for t in cli_exclude if t.strip())
    return list(dict.fromkeys(terms))


def _institutional_login(ctx, institution: str, logger):
    """Open a browser for manual institutional login, then wire the harvester.

    The user signs in and approves any push in the visible window; once the
    EZProxy session cookie appears, paywalled works are downloaded through it.
    """
    from snaffle.services.browser import BrowserService
    from snaffle.services.ezproxy import build_proxied_url
    from snaffle.services.institutional import InstitutionalHarvester

    cred = next(
        (c for c in ctx.credentials if c.institution.upper() == institution.upper()), None
    )
    if not cred or not cred.ezproxy_base:
        raise click.UsageError(
            f"No EZProxy base configured for institution '{institution}' "
            "(set SNAFFLE_CRED_<INST>_EZPROXY)."
        )
    import time

    service = BrowserService(headless=False)
    session = service.session()
    # Navigate to a proxied publisher so EZProxy sends the user to institutional login.
    session.get(build_proxied_url("https://www.jstor.org", cred.ezproxy_base))
    time.sleep(6)  # let the EZProxy -> IdP redirect settle
    click.echo(f"SSO login URL: {session.current_url}")
    logger.info(
        "A browser window has opened. Log into %s and approve any push; waiting…", institution
    )
    # EZProxy sets a session cookie named 'ezproxy...' once login completes.
    if not session.wait_for_cookie("ezproxy", timeout=300):
        logger.warning("did not detect a completed login within 5 minutes; continuing anyway")
    ctx.institutional = InstitutionalHarvester(session, ctx.http, cred.ezproxy_base)
    return service


def _run_activity(academic, output, only, disable, nuke, style, orcid, exclude,
                  do_search, do_download, institution=None):
    from snaffle import manifest, pipeline

    env = _environment()
    ctx = build_context(env, orcid_override=orcid)
    plugins = load_plugins(ctx, env, only, disable)
    logger = _configure_logging()
    out = Path(output)
    exclude_terms = _exclusions(env, exclude)

    browser_service = None
    if institution and do_download:
        browser_service = _institutional_login(ctx, institution, logger)

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
            logger=logger, style=style, exclude=exclude_terms,
        )
    elif do_search:
        report = pipeline.search_phase(
            academic, out, search_plugins(plugins), logger=logger, style=style,
            exclude=exclude_terms,
        )
    else:
        report = pipeline.download_phase(
            academic, out, download_plugins(plugins), saved, logger=logger
        )
        # Restore the manifest so the list survives a --nuke.
        manifest.write_manifest(out, academic, saved)

    if browser_service is not None:
        browser_service.close()

    logger.info(
        "done: %d found, %d downloaded, %d failed",
        len(report.found),
        len(report.downloaded),
        len(report.failed),
    )


_exclude_option = click.option(
    "--exclude",
    multiple=True,
    help="Drop works whose venue/publisher/URL matches (or 'unknown'). "
    "Adds to SNAFFLE_EXCLUDE.",
)


@main.command(help="Search for and download an academic's works (the full workflow).")
@_shared_options
@click.option("--style", default="chicago", help="Citation style for the bibliography.")
@click.option("--orcid", default=None, help="Override the discovered ORCID iD.")
@_exclude_option
@click.option("--institution", default=None,
              help="Log in to this institution in a browser to fetch paywalled PDFs.")
def run(academic, output, only, disable, nuke, style, orcid, exclude, institution):
    _run_activity(academic, output, only, disable, nuke, style, orcid, exclude,
                  do_search=True, do_download=True, institution=institution)


@main.command(help="Only build the publication list (writes the bibliography; no downloads).")
@_shared_options
@click.option("--style", default="chicago", help="Citation style for the bibliography.")
@click.option("--orcid", default=None, help="Override the discovered ORCID iD.")
@_exclude_option
def search(academic, output, only, disable, nuke, style, orcid, exclude):
    _run_activity(academic, output, only, disable, nuke, style, orcid, exclude,
                  do_search=True, do_download=False)


_institution_option = click.option(
    "--institution",
    default=None,
    help="Log in to this institution (by name) in a browser to fetch paywalled PDFs.",
)


@main.command(help="Only download full text for a list built earlier by 'search'.")
@_shared_options
@_institution_option
def download(academic, output, only, disable, nuke, institution):
    _run_activity(academic, output, only, disable, nuke, style="chicago", orcid=None,
                  exclude=(), do_search=False, do_download=True, institution=institution)


@main.command(help="Remove already-saved works matching the exclusions (files + manifest).")
@click.argument("academic")
@click.option("--output", "-o", default="output", help="Output directory.")
@_exclude_option
def prune(academic, output, exclude):
    from snaffle import pipeline

    env = _environment()
    logger = _configure_logging()
    terms = _exclusions(env, exclude)
    if not terms:
        raise click.UsageError(
            "No exclusions given. Set SNAFFLE_EXCLUDE or pass --exclude "
            '(e.g. --exclude "Front Matter" --exclude unknown).'
        )
    try:
        report = pipeline.prune(academic, Path(output), terms, logger=logger)
    except FileNotFoundError as exc:
        raise click.UsageError(str(exc)) from exc
    logger.info("pruned %d work(s); %d remain", len(report.removed), report.kept)


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
