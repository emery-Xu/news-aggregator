"""Feed manager for interactive RSS feed configuration."""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import yaml
import asyncio
import feedparser
import httpx


class FeedValidator:
    """Validates RSS/Atom feeds."""

    @staticmethod
    async def validate_feed(url: str, timeout: int = 10) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validate an RSS/Atom feed.

        Args:
            url: Feed URL to validate
            timeout: Request timeout in seconds

        Returns:
            Tuple of (is_valid, article_count, error_message)
        """
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

            feed = feedparser.parse(response.text)

            if feed.bozo and not feed.entries:
                return False, 0, "Invalid feed format"

            return True, len(feed.entries), None

        except httpx.HTTPStatusError as e:
            return False, 0, f"HTTP {e.response.status_code}"
        except httpx.TimeoutException:
            return False, 0, "Timeout"
        except Exception as e:
            return False, 0, str(e)


class FeedManager:
    """Manages RSS feeds in configuration file."""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.validator = FeedValidator()

    def load_config(self) -> Dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            return {
                'topics': {},
                'news_sources': {},
                'alternative_sources': {
                    'arxiv': {'enabled': False, 'categories': ['cs.AI', 'cs.LG', 'cs.RO'], 'max_per_category': 5},
                    'hacker_news': {'enabled': False, 'min_score': 100, 'max_age_hours': 24, 'keywords': []},
                    'custom_scrapers': {'enabled': False}
                },
                'summarization': {
                    'beginner_prompt_path': 'config/prompts/beginner.txt',
                    'cs_student_prompt_path': 'config/prompts/cs_student.txt',
                    'max_tokens': 500,
                    'temperature': 0.3
                },
                'quality': {
                    'min_content_length': 200,
                    'dedup_title_threshold': 0.85,
                    'history_days': 30
                },
                'execution': {
                    'run_time': '08:00',
                    'max_articles_per_topic': 15
                }
            }

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Ensure required keys exist
        if 'topics' not in config:
            config['topics'] = {}
        if 'news_sources' not in config:
            config['news_sources'] = {}

        return config

    def save_config(self, config: Dict):
        """Save configuration to YAML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def list_topics(self) -> Dict[str, Dict]:
        """List all topics with their feed counts."""
        config = self.load_config()
        topics = config.get('topics', {}) or {}
        news_sources = config.get('news_sources', {}) or {}

        result = {}
        for topic_name, topic_config in topics.items():
            feed_count = len(news_sources.get(topic_name, []))
            result[topic_name] = {
                'config': topic_config or {},
                'feed_count': feed_count,
                'feeds': news_sources.get(topic_name, [])
            }

        return result

    def topic_exists(self, topic_name: str) -> bool:
        """Check if a topic exists."""
        config = self.load_config()
        return topic_name in config.get('topics', {})

    def create_topic(self, topic_name: str, audience_level: str = 'beginner',
                    include_context: bool = False, context_text: Optional[str] = None,
                    min_quality_score: float = 0.5, max_articles_per_day: int = 10,
                    trusted_sources: Optional[List[str]] = None):
        """Create a new topic."""
        config = self.load_config()

        if 'topics' not in config or config['topics'] is None:
            config['topics'] = {}

        config['topics'][topic_name] = {
            'audience_level': audience_level,
            'include_context': include_context,
            'context_text': context_text,
            'min_quality_score': min_quality_score,
            'max_articles_per_day': max_articles_per_day,
            'trusted_sources': trusted_sources or []
        }

        if 'news_sources' not in config or config['news_sources'] is None:
            config['news_sources'] = {}
        if topic_name not in config['news_sources']:
            config['news_sources'][topic_name] = []

        self.save_config(config)

    async def add_feeds(self, urls: List[str], topic_name: str, priority: str = 'medium',
                       enabled: bool = True) -> List[Tuple[str, bool, Optional[int], Optional[str]]]:
        """
        Add multiple feeds to a topic.

        Args:
            urls: List of feed URLs
            topic_name: Topic to add feeds to
            priority: Feed priority (high, medium, low)
            enabled: Whether feeds are enabled

        Returns:
            List of tuples: (url, is_valid, article_count, error)
        """
        results = []

        # Validate all feeds
        print("\nValidating feeds...")
        for url in urls:
            print(f"  Checking {url}...", end=" ", flush=True)
            is_valid, count, error = await self.validator.validate_feed(url)

            if is_valid:
                print(f"OK ({count} articles)")
            else:
                print(f"FAILED ({error})")

            results.append((url, is_valid, count, error))

        # Filter out invalid feeds
        valid_feeds = [(url, count) for url, is_valid, count, _ in results if is_valid]

        if not valid_feeds:
            print("\nNo valid feeds to add.")
            return results

        # Add to config
        config = self.load_config()

        if 'news_sources' not in config or config['news_sources'] is None:
            config['news_sources'] = {}

        if topic_name not in config['news_sources']:
            config['news_sources'][topic_name] = []

        for url, _ in valid_feeds:
            # Check if feed already exists
            existing = any(f.get('url') == url for f in config['news_sources'][topic_name])
            if not existing:
                config['news_sources'][topic_name].append({
                    'url': url,
                    'priority': priority,
                    'enabled': enabled
                })

        self.save_config(config)

        return results

    def remove_feed(self, topic_name: str, url: str) -> bool:
        """Remove a feed from a topic."""
        config = self.load_config()

        if topic_name not in config.get('news_sources', {}):
            return False

        feeds = config['news_sources'][topic_name]
        original_len = len(feeds)

        config['news_sources'][topic_name] = [f for f in feeds if f.get('url') != url]

        if len(config['news_sources'][topic_name]) < original_len:
            self.save_config(config)
            return True

        return False

    def get_topic_feeds(self, topic_name: str) -> List[Dict]:
        """Get all feeds for a topic."""
        config = self.load_config()
        return config.get('news_sources', {}).get(topic_name, [])


def input_with_default(prompt: str, default: str = "") -> str:
    """Get input with a default value."""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


def select_option(prompt: str, options: List[str]) -> int:
    """Display options and get user selection."""
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}) {option}")

    while True:
        try:
            choice = input(f"\n请选择 [1-{len(options)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
            print(f"❌ 请输入 1-{len(options)} 之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")


async def interactive_add_feeds(config_path: str = "config/config.yaml"):
    """Interactive CLI for adding multiple feeds."""
    manager = FeedManager(config_path)

    print("\n" + "="*70)
    print("📰 批量添加 RSS 订阅源")
    print("="*70)

    # Step 1: Input URLs
    print("\n步骤 1/3: 输入RSS源URL")
    print("请输入RSS源URL（每行一个，输入空行结束）:\n")

    urls = []
    while True:
        url = input("> ").strip()
        if not url:
            break
        urls.append(url)

    if not urls:
        print("\n❌ 未输入任何URL")
        return

    print(f"\n总计: {len(urls)} 个RSS源")

    # Step 2: Select or create topic
    print("\n" + "─"*70)
    print("步骤 2/3: 选择或创建主题")

    topics = manager.list_topics()

    options = []
    if topics:
        print("\n现有主题:")
        for topic_name, info in topics.items():
            options.append(f"{topic_name} ({info['feed_count']}个源)")

    options.append("[创建新主题]")

    choice = select_option("", options)

    if choice < len(topics):
        # Existing topic
        topic_name = list(topics.keys())[choice]
        print(f"\n✓ 选择了主题: {topic_name}")
    else:
        # Create new topic
        topic_name = input("\n新主题名称: ").strip()
        if not topic_name:
            print("❌ 主题名称不能为空")
            return

        # Configure topic
        audience_options = ["beginner (初学者 - 简单解释)", "cs_student (计算机学生 - 技术深度)"]
        audience_choice = select_option("\n受众级别:", audience_options)
        audience_level = "beginner" if audience_choice == 0 else "cs_student"

        include_context = audience_level == "beginner"
        context_text = None
        if include_context:
            context_text = input("\n背景说明（可选，按回车跳过）: ").strip() or None

        max_articles = input_with_default("\n最大文章数/天", "10")
        try:
            max_articles = int(max_articles)
        except ValueError:
            max_articles = 10

        manager.create_topic(
            topic_name,
            audience_level=audience_level,
            include_context=include_context,
            context_text=context_text,
            max_articles_per_day=max_articles
        )

        print(f"\n✓ 主题 '{topic_name}' 创建成功")

    # Step 3: Configure feeds
    print("\n" + "─"*70)
    print("步骤 3/3: 配置订阅源设置")

    priority_options = ["high (高优先级)", "medium (中等优先级)", "low (低优先级)"]
    priority_choice = select_option("\n默认优先级:", priority_options)
    priority = ["high", "medium", "low"][priority_choice]

    # Summary
    print("\n" + "─"*70)
    print("\n✓ 配置摘要:")
    print(f"  主题: {topic_name}")
    print(f"  RSS源: {len(urls)} 个 (优先级: {priority})")

    confirm = input("\n确认添加? [Y/n]: ").strip().lower()
    if confirm and confirm != 'y':
        print("❌ 已取消")
        return

    # Add feeds
    results = await manager.add_feeds(urls, topic_name, priority=priority)

    valid_count = sum(1 for _, is_valid, _, _ in results if is_valid)

    print("\n" + "="*70)
    if valid_count > 0:
        print(f"✓ 已保存到 {config_path}")
        print(f"✓ {valid_count} 个RSS源添加完成")
        print(f"\n运行 'uv run news-aggregator --once' 测试配置")
    else:
        print("❌ 没有有效的RSS源被添加")
    print("="*70 + "\n")


async def interactive_list_topics(config_path: str = "config/config.yaml"):
    """List all topics interactively."""
    manager = FeedManager(config_path)
    topics = manager.list_topics()

    if not topics:
        print("\n没有配置任何主题")
        print("\n使用 'uv run news-aggregator --add-feeds' 添加主题和RSS源\n")
        return

    print("\n" + "="*70)
    print("已配置的主题")
    print("="*70 + "\n")

    for topic_name, info in topics.items():
        config = info['config']
        feed_count = info['feed_count']

        print(f"主题: {topic_name}")
        print(f"  受众级别: {config.get('audience_level', 'N/A')}")
        print(f"  RSS源数量: {feed_count}")
        print(f"  最大文章数/天: {config.get('max_articles_per_day', 'N/A')}")
        print(f"  质量阈值: {config.get('min_quality_score', 'N/A')}")

        if feed_count > 0:
            print(f"  RSS源:")
            for feed in info['feeds'][:5]:  # Show first 5
                status = "OK" if feed.get('enabled', True) else "DISABLED"
                print(f"    [{status}] {feed['url']} [{feed.get('priority', 'medium')}]")

            if feed_count > 5:
                print(f"    ... 还有 {feed_count - 5} 个源")

        print()

    print("="*70 + "\n")


async def interactive_remove_feed(config_path: str = "config/config.yaml"):
    """Remove feeds interactively."""
    manager = FeedManager(config_path)
    topics = manager.list_topics()

    if not topics:
        print("\n❌ 没有配置任何主题\n")
        return

    print("\n" + "="*70)
    print("🗑️  删除 RSS 订阅源")
    print("="*70)

    # Select topic
    topic_options = [f"{name} ({info['feed_count']}个源)" for name, info in topics.items()]
    topic_choice = select_option("\n选择主题:", topic_options)
    topic_name = list(topics.keys())[topic_choice]

    feeds = manager.get_topic_feeds(topic_name)

    if not feeds:
        print(f"\n❌ 主题 '{topic_name}' 没有RSS源\n")
        return

    # Select feed
    feed_options = [f"{feed['url']} [{feed.get('priority', 'medium')}]" for feed in feeds]
    feed_choice = select_option(f"\n选择要删除的RSS源:", feed_options)
    feed_url = feeds[feed_choice]['url']

    # Confirm
    print(f"\n将删除: {feed_url}")
    confirm = input("确认删除? [y/N]: ").strip().lower()

    if confirm == 'y':
        if manager.remove_feed(topic_name, feed_url):
            print(f"\n✓ 已从 '{topic_name}' 删除 RSS源\n")
        else:
            print(f"\n❌ 删除失败\n")
    else:
        print("\n❌ 已取消\n")
