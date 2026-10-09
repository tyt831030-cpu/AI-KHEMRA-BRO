"""Command line interface: ``cddl``."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from typing import Iterable, Optional, Sequence

from . import __version__
from .extractors import ExtractorError, list_extractors
from .http import HttpError
from .job import Options, Plan, build_session, make_plan, run_plan
from .downloader import DownloaderError
from .hls import MasterPlaylist
from .muxer import MuxError
from .utils import (
    human_bytes,
    human_time,
    load_cookie_file,
    parse_cookie_string,
    parse_int_set,
    parse_kv_header,
)

EPILOG = """
examples:
  # one episode, best quality
  cddl "https://cdn.example.com/series/ep01/ep01.m3u8" -n "斗罗大陆" -s 1 -e 1

  # 1080p, 16 parallel segment workers, custom referer (from the player page)
  cddl "https://cdn.example.com/ep07.m3u8" -q 1080 -j 16 --referer "https://example.com/watch/7"

  # inspect every rendition without downloading
  cddl "https://cdn.example.com/master.m3u8" --list-formats

  # a whole season straight from a URL pattern
  cddl --url-template "https://cdn.example.com/S01E{episode:02d}.m3u8" --episodes 1-24 \\
       -n "我的剧集" -s 1

  # a mixed batch described in a file
  cddl --batch episodes.txt -n "我的剧集"

Notes:
  * Supply the stream URL / manifest yourself. cddl does not bypass DRM, logins or
    a site's private API -- only download media you are entitled to keep.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cddl",
        description="Download HLS / MP4 video sources into a tidy series library.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("urls", nargs="*", metavar="URL", help="stream or manifest URL(s)")
    parser.add_argument("--version", action="version", version=f"cddl {__version__}")

    out = parser.add_argument_group("output layout")
    out.add_argument("-o", "--output", default="downloads", metavar="DIR", help="output directory (default: downloads)")
    out.add_argument("-n", "--name", dest="show", metavar="SHOW", help="series name used as the folder")
    out.add_argument("-t", "--template", metavar="TPL", help="output path template, e.g. '{show}/第{episode:03d}集.mp4'")
    out.add_argument("-s", "--season", type=int, metavar="N", help="season number")
    out.add_argument("-e", "--episode", type=int, metavar="N", help="episode number")
    out.add_argument("--title", metavar="TEXT", help="episode title appended to the filename")
    out.add_argument("-f", "--force", "--overwrite", dest="overwrite", action="store_true", help="re-download even if the file exists")
    out.add_argument("--dry-run", action="store_true", help="print the plan and exit without downloading")

    qual = parser.add_argument_group("stream selection")
    qual.add_argument("-q", "--quality", default="best", metavar="SEL", help="best | worst | height (e.g. 1080)")
    qual.add_argument("--list-formats", action="store_true", help="list renditions for each URL and exit")
    qual.add_argument("--list-extractors", action="store_true", help="show the URL handlers this build knows")
    qual.add_argument("--container", choices=("mp4", "mkv", "ts"), default="mp4", help="final container (default: mp4)")
    qual.add_argument("--no-remux", dest="remux_video", action="store_false", help="keep the raw concatenated transport stream")

    perf = parser.add_argument_group("performance and politeness")
    perf.add_argument("-j", "--workers", type=int, default=12, metavar="N", help="parallel segment workers (default: 12)")
    perf.add_argument("--retries", type=int, default=5, metavar="N", help="HTTP retries per request (default: 5)")
    perf.add_argument("--segment-retries", type=int, default=3, metavar="N", help="retries per segment (default: 3)")
    perf.add_argument("--timeout", type=float, default=30.0, metavar="SEC", help="per-request timeout (default: 30)")
    perf.add_argument("--politeness", type=float, default=0.0, metavar="SEC", help="delay before each segment request")

    net = parser.add_argument_group("request identity (bring your own authorised access)")
    net.add_argument("--referer", metavar="URL", help="Referer header sent with every request")
    net.add_argument("--user-agent", metavar="UA", help="override the User-Agent")
    net.add_argument("--header", action="append", default=[], metavar="'Name: value'", help="extra header (repeatable)")
    net.add_argument("--cookie", metavar="'k=v; k2=v2'", help="cookie string")
    net.add_argument("--cookies-file", metavar="FILE", help="JSON / Netscape / k=v cookie file")
    net.add_argument("--proxy", metavar="URL", help="HTTP(S) proxy")
    net.add_argument("-k", "--insecure", action="store_true", help="do not verify TLS certificates")
    net.add_argument("--config", metavar="FILE", help="JSON profile with defaults (headers, cookies, workers, ...)")

    subs = parser.add_argument_group("subtitles")
    subs.add_argument("--no-subtitles", dest="subtitles", action="store_false", help="do not fetch subtitle renditions")
    subs.add_argument("--sub-langs", metavar="LIST", help="comma list of wanted subtitle languages, e.g. zh,en")
    subs.add_argument("--embed-subtitles", action="store_true", help="mux subtitles into mkv output")

    batch = parser.add_argument_group("batch input")
    batch.add_argument("--batch", metavar="FILE", help="file of URLs (plain lines, 'n | url', or JSON list)")
    batch.add_argument("--url-template", metavar="TPL", help="URL pattern with {episode}/{season}, e.g. '.../E{episode:02d}.m3u8'")
    batch.add_argument("--episodes", metavar="SPEC", help="episode numbers for --url-template, e.g. 1-24 or 1,3,5-8")
    batch.add_argument("--episode-start", type=int, default=1, metavar="N", help="first episode number for plain batch lines")

    misc = parser.add_argument_group("misc")
    misc.add_argument("--temp", dest="temp_dir", metavar="DIR", help="staging directory for partial downloads")
    misc.add_argument("--keep-segments", action="store_true", help="do not delete staged segments (resume/debug)")
    misc.add_argument("--no-metadata", dest="write_metadata", action="store_false", help="skip the .json sidecar")
    misc.add_argument("--no-http2", action="store_true", help=argparse.SUPPRESS)
    verbosity = misc.add_mutually_exclusive_group()
    verbosity.add_argument("--quiet", action="store_true", help="suppress progress output")
    verbosity.add_argument("-v", "--verbose", action="store_true", help="print the plan for every URL")
    return parser


# --------------------------------------------------------------------------
# option assembly
# --------------------------------------------------------------------------
def options_from_args(args: argparse.Namespace) -> Options:
    headers: dict[str, str] = {}
    for raw in args.header:
        name, value = parse_kv_header(raw)
        headers[name] = value

    cookies: dict[str, str] = {}
    if args.cookies_file:
        cookies.update(load_cookie_file(args.cookies_file))
    if args.cookie:
        cookies.update(parse_cookie_string(args.cookie))

    options = Options(
        out_dir=args.output,
        show=args.show,
        season=args.season,
        episode=args.episode,
        title=args.title,
        template=args.template,
        container=args.container,
        quality=_quality(args.quality),
        remux_video=args.remux_video,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        write_metadata=args.write_metadata,
        workers=args.workers,
        retries=args.retries,
        segment_retries=args.segment_retries,
        timeout=args.timeout,
        politeness_delay=args.politeness,
        proxy=args.proxy,
        insecure=args.insecure,
        user_agent=args.user_agent,
        referer=args.referer,
        headers=headers,
        cookies=cookies,
        subtitles=args.subtitles,
        subtitle_langs=_split_list(args.sub_langs),
        embed_subtitles=args.embed_subtitles,
        temp_dir=args.temp_dir,
        keep_segments=args.keep_segments,
        quiet=args.quiet,
    )

    if args.config:
        options = _apply_profile(options, args.config)
    return options


def _apply_profile(options: Options, path: str) -> Options:
    """Merge a JSON profile under the explicit CLI values."""
    with open(path, "r", encoding="utf-8-sig") as fh:
        profile = json.load(fh)
    if not isinstance(profile, dict):
        raise SystemExit(f"{path}: profile must be a JSON object")

    mapped = {
        "out_dir": profile.get("output"),
        "show": profile.get("show"),
        "season": profile.get("season"),
        "episode": profile.get("episode"),
        "template": profile.get("template"),
        "container": profile.get("container"),
        "quality": profile.get("quality"),
        "workers": profile.get("workers"),
        "retries": profile.get("retries"),
        "timeout": profile.get("timeout"),
        "politeness_delay": profile.get("politeness"),
        "proxy": profile.get("proxy"),
        "user_agent": profile.get("user_agent"),
        "referer": profile.get("referer"),
        "temp_dir": profile.get("temp_dir"),
        "keep_segments": profile.get("keep_segments"),
        "embed_subtitles": profile.get("embed_subtitles"),
        "subtitle_langs": _split_list(profile.get("sub_langs")),
    }
    defaults = {"out_dir": "downloads", "show": None, "season": None, "episode": None,
                "template": None, "container": "mp4", "quality": "best", "workers": 12,
                "retries": 5, "timeout": 30.0, "politeness_delay": 0.0, "proxy": None,
                "user_agent": None, "referer": None, "temp_dir": None, "keep_segments": False,
                "embed_subtitles": False, "subtitle_langs": None}

    updates = {
        key: value
        for key, value in mapped.items()
        if value is not None and options.__dict__.get(key) == defaults.get(key)
    }

    headers = dict(profile.get("headers") or {})
    headers.update(options.headers)
    cookies = dict(profile.get("cookies") or {})
    cookies.update(options.cookies)

    return replace(options, headers=headers, cookies=cookies, **updates)


def _quality(value: str):
    if value in ("best", "worst"):
        return value
    if value.isdigit():
        return int(value)
    raise SystemExit(f"--quality must be 'best', 'worst' or a height in pixels, got {value!r}")


def _split_list(value) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [part.strip() for part in str(value).split(",") if part.strip()]


# --------------------------------------------------------------------------
# input collection
# --------------------------------------------------------------------------
def collect_urls(args: argparse.Namespace) -> list[tuple[str, Optional[int], Optional[str]]]:
    """Return ``(url, episode, title)`` triples from every input source."""
    items: list[tuple[str, Optional[int], Optional[str]]] = []

    for url in args.urls:
        items.append((url, args.episode, args.title))

    if args.batch:
        items.extend(_read_batch(args.batch, args.episode_start))

    if args.url_template:
        if not args.episodes:
            raise SystemExit("--url-template requires --episodes (e.g. --episodes 1-24)")
        for number in parse_int_set(args.episodes):
            url = args.url_template.format(
                episode=number,
                ep=number,
                season=args.season if args.season is not None else 1,
                s=args.season if args.season is not None else 1,
            )
            items.append((url, number, None))

    return items


def _read_batch(path: str, episode_start: int) -> list[tuple[str, Optional[int], Optional[str]]]:
    with open(path, "r", encoding="utf-8-sig") as fh:
        text = fh.read()

    items: list[tuple[str, Optional[int], Optional[str]]] = []
    if path.lower().endswith(".json") or text.lstrip().startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise SystemExit(f"{path}: JSON batch must be a list")
        for entry in payload:
            if isinstance(entry, str):
                items.append((entry, None, None))
            elif isinstance(entry, dict):
                url = entry.get("url")
                if not url:
                    raise SystemExit(f"{path}: entry without a 'url' key: {entry!r}")
                items.append((url, entry.get("episode"), entry.get("title")))
            else:
                raise SystemExit(f"{path}: unsupported entry {entry!r}")
        return items

    counter = episode_start
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        episode: Optional[int] = None
        title: Optional[str] = None
        if "|" in line:
            head, _, url = line.rpartition("|")
            head, url = head.strip(), url.strip()
            if head.isdigit():
                episode = int(head)
            elif head:
                title = head
        else:
            url = line
        if not url.startswith(("http://", "https://")):
            raise SystemExit(f"{path}:{lineno}: not a URL: {url!r}")
        items.append((url, episode if episode is not None else counter, title))
        counter += 1
    return items


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_extractors:
        print("Known extractors (higher priority wins):")
        for info in list_extractors():
            print(f"  {info['name']:<18} priority={info['priority']:<4} {info['description']}")
        print("\nAdd your own by subclassing cddl.extractors.base.Extractor.")
        return 0

    options = options_from_args(args)
    items = collect_urls(args)
    if not items:
        parser.print_help()
        return 2

    session = build_session(options)
    failures = 0
    try:
        for index, (url, episode, title) in enumerate(items, start=1):
            per_url = replace(options, episode=episode, title=title)
            prefix = f"[{index}/{len(items)}]"
            if not options.quiet:
                print(f"{prefix} {url}")
            try:
                plan = make_plan(url, per_url, session)
                if args.list_formats:
                    _print_formats(plan)
                    continue
                if args.verbose:
                    print(plan.describe())
                result = run_plan(plan, per_url, session)
                print(f"{prefix} {result.summary()}")
                if result.audio_path:
                    print(f"{prefix}   audio    : {os.path.basename(result.audio_path)}")
                if result.subtitle_paths:
                    print(f"{prefix}   subtitles: {', '.join(os.path.basename(p) for p in result.subtitle_paths)}")
            except (ExtractorError, DownloaderError, HttpError, MuxError, ValueError) as exc:
                failures += 1
                print(f"{prefix} ERROR: {exc}", file=sys.stderr)
            except KeyboardInterrupt:
                print(f"{prefix} interrupted; re-run to resume from staged segments", file=sys.stderr)
                return 130
    finally:
        session.close()

    if failures:
        print(f"\n{failures} of {len(items)} URL(s) failed.", file=sys.stderr)
        return 1
    return 0


def _print_formats(plan: Plan) -> None:
    source = plan.source
    print(f"  extractor : {source.extractor}  ({source.kind})")
    if source.master is not None and isinstance(source.master, MasterPlaylist):
        print(f"  renditions ({len(source.master.variants)}):")
        for i, variant in enumerate(
            sorted(source.master.variants, key=lambda v: (v.height, v.effective_bandwidth)), start=1
        ):
            marker = "*" if variant is plan.variant else " "
            print(f"   {marker} {i:>2}. {variant.label}")
        for rendition in source.master.subtitle_renditions():
            print(f"      subtitle: {rendition.name} [{rendition.language or '??'}]")
        for rendition in source.master.audio_renditions():
            print(f"      audio   : {rendition.name} [{rendition.language or '??'}] group={rendition.group_id}")
    else:
        print("  single rendition (media playlist)")
    if plan.audio_label:
        print(f"  audio track: {plan.audio_label} ({len(plan.audio_media.segments) if plan.audio_media else 0} segments)")
    print(f"  segments  : {plan.segments}  (~{human_time(plan.duration)})")
    if plan.media and plan.media.encryption_methods:
        print(f"  encryption: {', '.join(sorted(plan.media.encryption_methods))}")
    print(f"  would save: {plan.output_path}")


def _fmt_bytes(value: int) -> str:
    return human_bytes(value)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
