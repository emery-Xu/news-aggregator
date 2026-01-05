"""Configuration management for the News Aggregator."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv


@dataclass
class TopicConfig:
    """Configuration for a specific topic."""
    audience_level: str  # "beginner" or "cs_student"
    include_context: bool
    context_text: Optional[str]
    min_quality_score: float
    max_articles_per_day: int
    trusted_sources: List[str] = field(default_factory=list)


@dataclass
class FeedConfig:
    """Configuration for a single RSS feed."""
    url: str
    priority: str = "medium"  # "high", "medium", "low"
    enabled: bool = True


@dataclass
class ArxivConfig:
    """Configuration for arXiv integration."""
    enabled: bool = False
    categories: List[str] = field(default_factory=list)
    max_per_category: int = 5


@dataclass
class HackerNewsConfig:
    """Configuration for Hacker News integration."""
    enabled: bool = False
    min_score: int = 50
    max_age_hours: int = 48
    keywords: List[str] = field(default_factory=list)


@dataclass
class SummarizationConfig:
    """Configuration for summarization."""
    beginner_prompt_path: str
    cs_student_prompt_path: str
    max_tokens: int = 500
    temperature: float = 0.3


@dataclass
class QualityConfig:
    """Configuration for quality filtering."""
    min_content_length: int = 200
    dedup_title_threshold: float = 0.85
    history_days: int = 30


@dataclass
class SMTPConfig:
    """SMTP server configuration."""
    host: str
    port: int
    username: str
    password: str
    from_email: str
    use_tls: bool = True


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    provider_id: str  # e.g., "anthropic_primary", "openai_fallback"
    provider_type: str  # "anthropic" or "openai"
    api_key: str
    model: str  # e.g., "claude-sonnet-4-5", "gpt-4-turbo"
    enabled: bool = True
    priority: int = 10  # Lower = higher priority (0-100)
    base_url: Optional[str] = None
    timeout: int = 30
    max_tokens: int = 500
    temperature: float = 0.3
    input_cost_per_1M_tokens: float = 0.0  # For cost tracking
    output_cost_per_1M_tokens: float = 0.0

    def estimated_cost_per_request(self, avg_input_tokens: int = 1500, avg_output_tokens: int = 200) -> float:
        """Estimate cost per request based on average token usage."""
        input_cost = (avg_input_tokens / 1_000_000) * self.input_cost_per_1M_tokens
        output_cost = (avg_output_tokens / 1_000_000) * self.output_cost_per_1M_tokens
        return input_cost + output_cost


@dataclass
class Config:
    """Main application configuration."""
    # Required fields (no defaults) must come first
    # Topic configurations
    topics: Dict[str, TopicConfig]

    # News sources
    news_sources: Dict[str, List[FeedConfig]]

    # Alternative sources
    arxiv: ArxivConfig
    hacker_news: HackerNewsConfig
    custom_scrapers_enabled: bool

    # Summarization
    summarization: SummarizationConfig

    # Quality filtering
    quality: QualityConfig

    # Email
    smtp: SMTPConfig
    recipient_email: str

    # Multi-provider configuration (NEW)
    providers: List[ProviderConfig] = field(default_factory=list)
    provider_strategy: str = "priority"  # "priority", "cost", or "performance"

    # Legacy Claude API fields (maintained for backward compatibility)
    claude_api_key: Optional[str] = None
    claude_api_base_url: Optional[str] = None
    claude_model: str = "claude-sonnet-4-5"
    max_tokens_per_summary: int = 500

    # Optional fields (with defaults)
    run_time: str = "08:00"
    max_articles_per_topic: int = 15
    history_file: Path = field(default_factory=lambda: Path("data/sent_articles.json"))
    log_file: Path = field(default_factory=lambda: Path("logs/news_aggregator.log"))
    execution_history_file: Path = field(default_factory=lambda: Path("data/execution_history.json"))


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def load_config(config_path: str = "config/config.yaml") -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to the configuration YAML file

    Returns:
        Config object with all settings

    Raises:
        ConfigError: If configuration is invalid or missing required fields
    """
    # Load environment variables
    load_dotenv("config/.env")
    load_dotenv()  # Also load from project root .env if exists

    # Check if config file exists
    if not os.path.exists(config_path):
        raise ConfigError(f"Configuration file not found: {config_path}")

    # Load YAML config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
    except Exception as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}")

    # Validate required sections
    if not yaml_config:
        raise ConfigError("Configuration file is empty")

    required_sections = ['topics', 'news_sources', 'email', 'claude', 'summarization']
    for section in required_sections:
        if section not in yaml_config:
            raise ConfigError(f"Missing required configuration section: {section}")

    # Load topic configurations
    topics = {}
    topics_config = yaml_config.get('topics', {})
    required_topics = ['polymarket', 'ai', 'robotics']

    for topic in required_topics:
        if topic not in topics_config:
            raise ConfigError(f"Missing configuration for required topic: {topic}")

        topic_data = topics_config[topic]
        try:
            topics[topic] = TopicConfig(
                audience_level=topic_data.get('audience_level', 'beginner'),
                include_context=topic_data.get('include_context', False),
                context_text=topic_data.get('context_text'),
                min_quality_score=topic_data.get('min_quality_score', 0.5),
                max_articles_per_day=topic_data.get('max_articles_per_day', 10),
                trusted_sources=topic_data.get('trusted_sources', [])
            )
        except Exception as e:
            raise ConfigError(f"Invalid configuration for topic '{topic}': {e}")

    # Load news sources
    news_sources = {}
    news_sources_config = yaml_config.get('news_sources', {})

    for topic in required_topics:
        if topic not in news_sources_config:
            raise ConfigError(f"No news sources configured for topic: {topic}")

        feeds = []
        for feed_data in news_sources_config[topic]:
            if isinstance(feed_data, str):
                # Legacy format: just URL string
                feeds.append(FeedConfig(url=feed_data))
            elif isinstance(feed_data, dict):
                # New format: dict with url, priority, enabled
                try:
                    feeds.append(FeedConfig(
                        url=feed_data['url'],
                        priority=feed_data.get('priority', 'medium'),
                        enabled=feed_data.get('enabled', True)
                    ))
                except KeyError:
                    raise ConfigError(f"Feed configuration missing 'url' for topic '{topic}'")
            else:
                raise ConfigError(f"Invalid feed format for topic '{topic}'")

        if not feeds:
            raise ConfigError(f"No feeds configured for topic: {topic}")

        news_sources[topic] = feeds

    # Load alternative sources
    alt_sources = yaml_config.get('alternative_sources', {})

    arxiv_config_data = alt_sources.get('arxiv', {})
    arxiv = ArxivConfig(
        enabled=arxiv_config_data.get('enabled', False),
        categories=arxiv_config_data.get('categories', []),
        max_per_category=arxiv_config_data.get('max_per_category', 5)
    )

    hn_config_data = alt_sources.get('hacker_news', {})
    hacker_news = HackerNewsConfig(
        enabled=hn_config_data.get('enabled', False),
        min_score=hn_config_data.get('min_score', 50),
        max_age_hours=hn_config_data.get('max_age_hours', 48),
        keywords=hn_config_data.get('keywords', [])
    )

    custom_scrapers_enabled = alt_sources.get('custom_scrapers', {}).get('enabled', False)

    # Load summarization config
    summ_config = yaml_config.get('summarization', {})
    try:
        summarization = SummarizationConfig(
            beginner_prompt_path=summ_config['beginner_prompt_path'],
            cs_student_prompt_path=summ_config['cs_student_prompt_path'],
            max_tokens=summ_config.get('max_tokens', 500),
            temperature=summ_config.get('temperature', 0.3)
        )
    except KeyError as e:
        raise ConfigError(f"Missing required summarization config field: {e}")

    # Load quality config
    quality_config = yaml_config.get('quality', {})
    quality = QualityConfig(
        min_content_length=quality_config.get('min_content_length', 200),
        dedup_title_threshold=quality_config.get('dedup_title_threshold', 0.85),
        history_days=quality_config.get('history_days', 30)
    )

    # Load Claude API settings (legacy support)
    claude_config = yaml_config.get('claude', {})
    claude_api_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')

    # Load custom API base URL (optional)
    claude_api_base_url = os.getenv('CLAUDE_API_BASE_URL') or claude_config.get('api_base_url')

    # NEW: Load multi-provider configuration
    providers_config = yaml_config.get('providers', [])
    provider_strategy = yaml_config.get('provider_strategy', 'priority')

    providers = []
    logger = None  # Will be initialized later if needed

    if providers_config:
        # New multi-provider configuration format
        for prov_data in providers_config:
            try:
                # Get API key from env var or config
                api_key_env_var = None
                if prov_data['provider_type'] == 'anthropic':
                    api_key_env_var = 'ANTHROPIC_API_KEY'
                elif prov_data['provider_type'] == 'openai':
                    api_key_env_var = 'OPENAI_API_KEY'

                api_key = None
                if api_key_env_var:
                    api_key = os.getenv(api_key_env_var)

                if not api_key:
                    api_key = prov_data.get('api_key', '')

                if not api_key:
                    raise ConfigError(
                        f"No API key found for provider {prov_data.get('provider_id')}. "
                        f"Set {api_key_env_var} environment variable or api_key in config."
                    )

                provider = ProviderConfig(
                    provider_id=prov_data['provider_id'],
                    provider_type=prov_data['provider_type'],
                    api_key=api_key,
                    model=prov_data['model'],
                    enabled=prov_data.get('enabled', True),
                    priority=prov_data.get('priority', 10),
                    base_url=prov_data.get('base_url'),
                    timeout=prov_data.get('timeout', 30),
                    max_tokens=prov_data.get('max_tokens', 500),
                    temperature=prov_data.get('temperature', 0.3),
                    input_cost_per_1M_tokens=prov_data.get('input_cost_per_1M_tokens', 0.0),
                    output_cost_per_1M_tokens=prov_data.get('output_cost_per_1M_tokens', 0.0)
                )
                providers.append(provider)
            except KeyError as e:
                raise ConfigError(f"Missing required provider config field: {e}")
    else:
        # Legacy configuration - auto-migrate from claude settings
        if not claude_api_key:
            raise ConfigError(
                "No API key found. Set CLAUDE_API_KEY or ANTHROPIC_API_KEY environment variable, "
                "or configure providers array in config.yaml"
            )

        # Create a single Anthropic provider from legacy config
        provider = ProviderConfig(
            provider_id="anthropic_legacy",
            provider_type="anthropic",
            api_key=claude_api_key,
            model=claude_config.get('model', 'claude-sonnet-4-5'),
            enabled=True,
            priority=1,
            base_url=claude_api_base_url,
            timeout=30,
            max_tokens=claude_config.get('max_tokens_per_summary', 500),
            temperature=0.3,
            input_cost_per_1M_tokens=3.0,  # Default Claude pricing
            output_cost_per_1M_tokens=15.0
        )
        providers.append(provider)

        # Log migration message
        try:
            from .logger import get_logger
            logger = get_logger()
            logger.info(
                "Using legacy Claude API configuration. "
                "Consider migrating to multi-provider format in config.yaml"
            )
        except:
            pass  # Logger might not be initialized yet

    # Load email settings
    email_config = yaml_config.get('email', {})
    smtp_password = os.getenv('SMTP_PASSWORD')
    if not smtp_password:
        raise ConfigError(
            "SMTP_PASSWORD environment variable not set. "
            "Please set it in config/.env file."
        )

    recipient_email = os.getenv('RECIPIENT_EMAIL') or email_config.get('recipient_email')
    if not recipient_email:
        raise ConfigError(
            "RECIPIENT_EMAIL not configured. "
            "Set it in config.yaml or as environment variable."
        )

    # Build SMTP config
    try:
        smtp = SMTPConfig(
            host=email_config.get('smtp_host', 'smtp.gmail.com'),
            port=email_config.get('smtp_port', 587),
            username=email_config.get('smtp_username', ''),
            password=smtp_password,
            from_email=email_config.get('from_email', ''),
            use_tls=email_config.get('use_tls', True)
        )
    except Exception as e:
        raise ConfigError(f"Invalid email configuration: {e}")

    # Load execution settings
    execution_config = yaml_config.get('execution', {})

    # Load paths
    paths_config = yaml_config.get('paths', {})

    # Create Config object
    try:
        config = Config(
            topics=topics,
            news_sources=news_sources,
            arxiv=arxiv,
            hacker_news=hacker_news,
            custom_scrapers_enabled=custom_scrapers_enabled,
            summarization=summarization,
            quality=quality,
            providers=providers,
            provider_strategy=provider_strategy,
            claude_api_key=claude_api_key,
            claude_api_base_url=claude_api_base_url,
            claude_model=claude_config.get('model', 'claude-sonnet-4-5'),
            max_tokens_per_summary=claude_config.get('max_tokens_per_summary', 500),
            smtp=smtp,
            recipient_email=recipient_email,
            run_time=execution_config.get('run_time', '08:00'),
            max_articles_per_topic=execution_config.get('max_articles_per_topic', 15),
            history_file=Path(paths_config.get('history_file', 'data/sent_articles.json')),
            log_file=Path(paths_config.get('log_file', 'logs/news_aggregator.log')),
            execution_history_file=Path(paths_config.get('execution_history_file', 'data/execution_history.json'))
        )
    except Exception as e:
        raise ConfigError(f"Failed to create configuration object: {e}")

    return config


def validate_config(config: Config) -> None:
    """
    Validate configuration object.

    Args:
        config: Configuration object to validate

    Raises:
        ConfigError: If configuration is invalid
    """
    # Validate email format (basic check)
    if '@' not in config.recipient_email:
        raise ConfigError(f"Invalid recipient email: {config.recipient_email}")

    # Validate run_time format
    try:
        hours, minutes = config.run_time.split(':')
        if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
            raise ValueError
    except:
        raise ConfigError(f"Invalid run_time format (use HH:MM): {config.run_time}")

    # Validate audience levels
    valid_audience_levels = {'beginner', 'cs_student'}
    for topic, topic_config in config.topics.items():
        if topic_config.audience_level not in valid_audience_levels:
            raise ConfigError(
                f"Invalid audience_level '{topic_config.audience_level}' for topic '{topic}'. "
                f"Must be one of: {valid_audience_levels}"
            )

    # Validate quality scores
    for topic, topic_config in config.topics.items():
        if not (0 <= topic_config.min_quality_score <= 1):
            raise ConfigError(
                f"Invalid min_quality_score for topic '{topic}': {topic_config.min_quality_score}. "
                "Must be between 0 and 1."
            )

    # Validate prompt template paths exist
    for prompt_name, prompt_path in [
        ('beginner', config.summarization.beginner_prompt_path),
        ('cs_student', config.summarization.cs_student_prompt_path)
    ]:
        if not os.path.exists(prompt_path):
            raise ConfigError(
                f"Prompt template file not found: {prompt_path}\n"
                f"Please create the {prompt_name} prompt template file."
            )

    # Validate paths
    for path in [config.history_file.parent, config.log_file.parent, config.execution_history_file.parent]:
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigError(f"Failed to create directory {path}: {e}")
