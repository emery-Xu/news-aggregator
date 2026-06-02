"""CLI entry point for the News Aggregator."""

import argparse
import asyncio
import sys

from .config import ConfigError, load_config, validate_config
from .logger import get_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="news-aggregator",
        description="Daily AI News Aggregator - Fetch, summarize, and deliver news",
    )

    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--once", action="store_true", help="Run the pipeline once and exit"
    )
    group.add_argument(
        "--serve",
        action="store_true",
        help="Start the web server to browse collected articles",
    )
    group.add_argument(
        "--add-feeds",
        action="store_true",
        help="Interactively add topics and RSS feeds",
    )
    group.add_argument(
        "--list-topics", action="store_true", help="List all configured topics"
    )
    group.add_argument(
        "--discover-feeds", metavar="DOMAIN", help="Discover RSS feeds on a domain"
    )
    group.add_argument(
        "--score-feeds", action="store_true", help="Score configured feeds for quality"
    )
    group.add_argument(
        "--import-opml", metavar="FILE", help="Import feeds from an OPML file"
    )

    parser.add_argument(
        "--host", default=None, help="Web server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Web server port (default: 8000)"
    )

    return parser.parse_args()


def run_serve(config, host: str, port: int) -> None:
    import uvicorn

    from .web.app import create_app

    logger = get_logger()
    app = create_app(config)
    logger.info(f"Starting web server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


def run_once(config) -> None:
    from .orchestrator import PipelineOrchestrator

    logger = get_logger()
    pipeline = PipelineOrchestrator(config)
    result = asyncio.run(pipeline.run_pipeline())

    if result.success:
        logger.info("Pipeline completed successfully")
    else:
        logger.error(f"Pipeline failed: {result.errors}")
        sys.exit(1)


def run_add_feeds(config) -> None:
    from .tools.feed_manager import interactive_add_feeds

    asyncio.run(interactive_add_feeds())


def run_list_topics(config) -> None:
    from .tools.feed_manager import interactive_list_topics

    asyncio.run(interactive_list_topics())


def run_discover_feeds(domain: str) -> None:
    from .tools.feed_discovery import FeedDiscovery

    discovery = FeedDiscovery()
    results = asyncio.run(discovery.discover(domain))
    for feed in results:
        status = "OK" if feed.is_valid else "FAIL"
        count = f" ({feed.entry_count} entries)" if feed.entry_count else ""
        error = f" - {feed.error}" if feed.error else ""
        print(f"  [{status}] {feed.url}{count}{error}")


def run_score_feeds(config) -> None:
    from .tools.feed_scorer import FeedScorer

    scorer = FeedScorer()
    for _topic, feeds in config.news_sources.items():
        for feed_config in feeds:
            if feed_config.enabled:
                score = asyncio.run(scorer.score_feed(feed_config.url))
                print(
                    f"  {score.url}: {score.total_score:.2f} "
                    f"[{score.recommendation}]"
                )


def run_import_opml(file_path: str, config) -> None:
    from .tools.opml_importer import OPMLImporter

    importer = OPMLImporter()
    feeds = importer.parse(file_path)
    grouped = importer.group_by_category(feeds)
    total = sum(len(v) for v in grouped.values())
    print(f"Found {total} feeds in {file_path}")
    print("To import, use the feed manager to add them to your config.")


def main() -> None:
    args = parse_args()

    try:
        config = load_config(args.config)
        validate_config(config)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.once:
        run_once(config)
    elif args.serve:
        host = args.host or config.web_host
        port = args.port or config.web_port
        run_serve(config, host, port)
    elif args.add_feeds:
        run_add_feeds(config)
    elif args.list_topics:
        run_list_topics(config)
    elif args.discover_feeds:
        run_discover_feeds(args.discover_feeds)
    elif args.score_feeds:
        run_score_feeds(config)
    elif args.import_opml:
        run_import_opml(args.import_opml, config)
    else:
        from .orchestrator import PipelineOrchestrator
        from .scheduler import Scheduler

        pipeline = PipelineOrchestrator(config)
        scheduler = Scheduler(pipeline, run_time=config.run_time)
        scheduler.start()


if __name__ == "__main__":
    main()
