"""
Benchmark: Python configuration pattern cases
Contributor: Rishmina Sherin
Slice: 20 Python positive and negative cases covering
       environment variables, feature flags, and look-alike negatives

Cases:
  Positive (10): Real configuration patterns that ConfigReach should detect
  Negative (10): Look-alike patterns that ConfigReach should NOT detect

Label format per case:
  # label: POSITIVE / NEGATIVE
  # task: discovery / declaration / feature_flag / branch_inference / test_evidence
  # why: explanation of the labelling decision
"""
from __future__ import annotations

from configreach.engine import scan


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POSITIVE CASES — Real configuration ConfigReach must detect
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_positive_01_basic_env_var(tmp_path):
    """
    label: POSITIVE
    task: discovery
    why: DATABASE_URL is read from environment via os.getenv
         and used as runtime configuration.
         Uppercase name + os.getenv = canonical env var pattern.
    """
    (tmp_path / "db.py").write_text(
        "import os\n"
        "DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "DATABASE_URL" in report.keys
    assert report.keys["DATABASE_URL"].used


def test_positive_02_config_file_loading(tmp_path):
    """
    label: POSITIVE
    task: declaration
    why: MAX_RETRIES and TIMEOUT are loaded from a yaml config file
         and assigned to module-level constants.
         Config file loading is a primary configuration pattern.
    """
    (tmp_path / "config.py").write_text(
        "import yaml\n"
        "import os\n"
        "with open('config.yaml') as f:\n"
        "    config = yaml.safe_load(f)\n"
        "MAX_RETRIES = config.get('max_retries', 3)\n"
        "TIMEOUT = config.get('timeout', 30)\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "MAX_RETRIES" in report.keys or "max_retries" in report.keys


def test_positive_03_feature_flag_env_var(tmp_path):
    """
    label: POSITIVE
    task: feature_flag
    why: ENABLE_NEW_DASHBOARD is read from environment,
         coerced to boolean, and controls a code branch.
         This is the canonical feature flag pattern via env var.
    """
    (tmp_path / "dashboard.py").write_text(
        "import os\n"
        "ENABLE_NEW_DASHBOARD = os.getenv('ENABLE_NEW_DASHBOARD', 'false').lower() == 'true'\n"
        "if ENABLE_NEW_DASHBOARD:\n"
        "    print('new dashboard')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "ENABLE_NEW_DASHBOARD" in report.keys
    key = report.keys["ENABLE_NEW_DASHBOARD"]
    assert key.used


def test_positive_04_django_settings_pattern(tmp_path):
    """
    label: POSITIVE
    task: declaration
    why: DEBUG, ALLOWED_HOSTS, SECRET_KEY follow Django settings pattern.
         All read from environment variables at module level.
         These control core application behaviour.
    """
    (tmp_path / "settings.py").write_text(
        "import os\n"
        "DEBUG = os.environ.get('DEBUG', 'False') == 'True'\n"
        "SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret')\n"
        "ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "DEBUG" in report.keys
    assert "SECRET_KEY" in report.keys
    assert "ALLOWED_HOSTS" in report.keys


def test_positive_05_config_class_pattern(tmp_path):
    """
    label: POSITIVE
    task: declaration
    why: Config class holds runtime configuration values
         all sourced from environment variables.
         Class-based config is a widely recognised pattern.
    """
    (tmp_path / "config.py").write_text(
        "import os\n"
        "class Config:\n"
        "    MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', '10'))\n"
        "    CACHE_TTL = int(os.getenv('CACHE_TTL', '3600'))\n"
        "    API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.example.com')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "MAX_CONNECTIONS" in report.keys
    assert "CACHE_TTL" in report.keys
    assert "API_BASE_URL" in report.keys


def test_positive_06_pydantic_settings_pattern(tmp_path):
    """
    label: POSITIVE
    task: declaration
    why: Pydantic BaseSettings reads fields from environment automatically.
         database_url and debug are real runtime configuration fields.
         This is the modern Python configuration declaration pattern.
    """
    (tmp_path / "settings.py").write_text(
        "from pydantic_settings import BaseSettings\n"
        "class AppSettings(BaseSettings):\n"
        "    database_url: str = 'sqlite:///db.sqlite3'\n"
        "    debug: bool = False\n"
        "    max_connections: int = 10\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "DEBUG" in report.keys or "debug" in report.keys


def test_positive_07_os_environ_branch(tmp_path):
    """
    label: POSITIVE
    task: branch_inference
    why: APP_ENV is read from environment and compared in if/elif chain.
         The string comparisons reveal the finite domain: dev, staging, prod.
         This is a classic environment-mode branch pattern.
    """
    (tmp_path / "app.py").write_text(
        "import os\n"
        "APP_ENV = os.getenv('APP_ENV', 'dev')\n"
        "if APP_ENV == 'prod':\n"
        "    print('production mode')\n"
        "elif APP_ENV == 'staging':\n"
        "    print('staging mode')\n"
        "else:\n"
        "    print('dev mode')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "APP_ENV" in report.keys
    key = report.keys["APP_ENV"]
    assert "prod" in key.expected_values or "prod" in key.branch_values


def test_positive_08_env_var_with_type_cast(tmp_path):
    """
    label: POSITIVE
    task: discovery
    why: PORT and WORKERS are read from environment and cast to int.
         Type casting after os.getenv is a standard configuration pattern.
         These values control server behaviour at runtime.
    """
    (tmp_path / "server.py").write_text(
        "import os\n"
        "PORT = int(os.getenv('PORT', '8000'))\n"
        "WORKERS = int(os.getenv('WORKERS', '4'))\n"
        "LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "PORT" in report.keys
    assert "WORKERS" in report.keys
    assert "LOG_LEVEL" in report.keys


def test_positive_09_feature_flag_sdk_pattern(tmp_path):
    """
    label: POSITIVE
    task: feature_flag
    why: client.variation('new-checkout', False) is the canonical
         LaunchDarkly/feature flag SDK call pattern.
         'new-checkout' is a real feature flag key.
    """
    (tmp_path / "checkout.py").write_text(
        "def is_new_checkout_enabled(client, user):\n"
        "    return client.variation('new-checkout', False)\n"
        "def is_beta_enabled(client, user):\n"
        "    return client.variation('beta-feature', False)\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "new-checkout" in report.keys
    assert "beta-feature" in report.keys


def test_positive_10_dotenv_loading(tmp_path):
    """
    label: POSITIVE
    task: discovery
    why: python-dotenv load_dotenv() loads .env file into environment.
         Following os.getenv calls are real configuration reads.
         This is a standard local development configuration pattern.
    """
    (tmp_path / "app.py").write_text(
        "from dotenv import load_dotenv\n"
        "import os\n"
        "load_dotenv()\n"
        "REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')\n"
        "CELERY_BROKER = os.getenv('CELERY_BROKER', 'redis://localhost:6379/0')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "REDIS_URL" in report.keys
    assert "CELERY_BROKER" in report.keys


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NEGATIVE CASES — Look-alikes ConfigReach must NOT detect
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_negative_01_setup_py_metadata(tmp_path):
    """
    label: NEGATIVE
    task: discovery
    why: setup() arguments are package metadata fields.
         name, version, author do not control runtime behaviour.
         They are never read as environment variables or config values.
         Uppercase appearance is coincidental to config naming conventions.
    """
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\n"
        "setup(\n"
        "    name='mypackage',\n"
        "    version='1.0.0',\n"
        "    description='My package',\n"
        "    author='Rishmina',\n"
        "    python_requires='>=3.8',\n"
        ")\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "name" not in report.keys
    assert "version" not in report.keys
    assert "author" not in report.keys


def test_negative_02_statistical_variation_method(tmp_path):
    """
    label: NEGATIVE
    task: feature_flag
    why: stats.variation('coefficient-of-variation') is a SciPy/stats call.
         'variation' here is a mathematical function name not a feature flag SDK.
         'coefficient-of-variation' is a statistical metric name not a flag key.
         Should not be classified as feature_flag.
    """
    (tmp_path / "analytics.py").write_text(
        "from scipy import stats\n"
        "def calculate_cv(data):\n"
        "    return stats.variation(data)\n"
        "def calculate_named(data):\n"
        "    return stats.variation('coefficient-of-variation')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "coefficient-of-variation" not in report.keys


def test_negative_03_user_preferences_dict(tmp_path):
    """
    label: NEGATIVE
    task: discovery
    why: Dictionary returned per-user is not global application config.
         'theme', 'language', 'notifications' are user-level preferences.
         They are not read from environment or a config file.
         They vary per user — not per deployment.
    """
    (tmp_path / "preferences.py").write_text(
        "def get_user_preferences(user_id):\n"
        "    return {\n"
        "        'theme': 'dark',\n"
        "        'language': 'en',\n"
        "        'notifications': True,\n"
        "        'items_per_page': 20,\n"
        "    }\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "theme" not in report.keys
    assert "language" not in report.keys
    assert "notifications" not in report.keys


def test_negative_04_test_helper_hardcoded_url(tmp_path):
    """
    label: NEGATIVE
    task: test_evidence
    why: DATABASE_URL appears in test code as a hardcoded test string.
         It is not read from os.environ — it is a literal test fixture value.
         The string merely contains the word DATABASE_URL as a label.
         Should not be classified as a configuration discovery.
    """
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_db.py").write_text(
        "def test_database_connection():\n"
        "    test_url = 'postgresql://test:test@localhost/testdb'\n"
        "    assert is_valid_url(test_url)\n"
        "def test_url_format():\n"
        "    assert 'DATABASE_URL' in get_env_var_names()\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    if "DATABASE_URL" in report.keys:
        key = report.keys["DATABASE_URL"]
        assert not key.used


def test_negative_05_function_parameter_bool_defaults(tmp_path):
    """
    label: NEGATIVE
    task: branch_inference
    why: is_active=True and is_admin=False are function parameter defaults.
         They are not environment variables or configuration branches.
         They represent default argument values — not runtime configuration.
         Booleans as type defaults should not trigger branch_inference.
    """
    (tmp_path / "users.py").write_text(
        "def create_user(\n"
        "    username: str,\n"
        "    is_active: bool = True,\n"
        "    is_admin: bool = False,\n"
        "    max_items: int = 10,\n"
        ") -> dict:\n"
        "    return {'username': username, 'is_active': is_active}\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "is_active" not in report.keys
    assert "is_admin" not in report.keys
    assert "max_items" not in report.keys


def test_negative_06_error_message_keys(tmp_path):
    """
    label: NEGATIVE
    task: discovery
    why: ERROR_MESSAGES dict keys look like environment variable names
         (uppercase with underscores) but are error message identifiers.
         They are never read as environment variables.
         Uppercase naming convention is coincidental.
    """
    (tmp_path / "errors.py").write_text(
        "ERROR_MESSAGES = {\n"
        "    'DATABASE_URL_INVALID': 'Please check your database connection',\n"
        "    'API_KEY_MISSING': 'API key is required',\n"
        "    'MAX_RETRIES_EXCEEDED': 'Too many retry attempts',\n"
        "    'TIMEOUT_ERROR': 'Request timed out',\n"
        "}\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "DATABASE_URL_INVALID" not in report.keys
    assert "API_KEY_MISSING" not in report.keys
    assert "MAX_RETRIES_EXCEEDED" not in report.keys


def test_negative_07_jinja2_template_variables(tmp_path):
    """
    label: NEGATIVE
    task: discovery
    why: {{ deployment.environment }} is Jinja2 template syntax.
         It is a template rendering variable — not an env var or config read.
         The word 'environment' appears but is part of a template expression.
         Should not be classified as configuration discovery.
    """
    (tmp_path / "templates.py").write_text(
        "email_template = '''\n"
        "Dear {{ user.name }},\n"
        "Your account {{ account.status }} has been updated.\n"
        "Environment: {{ deployment.environment }}\n"
        "Region: {{ deployment.region }}\n"
        "'''\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "deployment.environment" not in report.keys
    assert "deployment.region" not in report.keys
    assert "account.status" not in report.keys


def test_negative_08_mathematical_constants(tmp_path):
    """
    label: NEGATIVE
    task: discovery
    why: PI, EULER_NUMBER, GOLDEN_RATIO are mathematical constants.
         They are hardcoded values that never change per deployment.
         Uppercase naming follows Python constants convention (PEP 8)
         but does not make them configuration values.
    """
    (tmp_path / "math_constants.py").write_text(
        "PI = 3.14159265358979\n"
        "EULER_NUMBER = 2.71828182845904\n"
        "GOLDEN_RATIO = 1.61803398874989\n"
        "MAX_INT_32 = 2147483647\n"
        "BYTES_PER_KB = 1024\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "PI" not in report.keys
    assert "EULER_NUMBER" not in report.keys
    assert "GOLDEN_RATIO" not in report.keys
    assert "BYTES_PER_KB" not in report.keys


def test_negative_09_dataclass_field_defaults(tmp_path):
    """
    label: NEGATIVE
    task: declaration
    why: Dataclass fields with defaults look like configuration declarations.
         max_items=10 and enable_notifications=True are instance field defaults.
         They are not read from environment and do not control app-wide behaviour.
         Per-instance defaults should not be classified as configuration.
    """
    (tmp_path / "models.py").write_text(
        "from dataclasses import dataclass\n"
        "from typing import Optional\n"
        "@dataclass\n"
        "class UserProfile:\n"
        "    name: str\n"
        "    email: str\n"
        "    max_items: int = 10\n"
        "    enable_notifications: bool = True\n"
        "    theme: Optional[str] = None\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "max_items" not in report.keys
    assert "enable_notifications" not in report.keys
    assert "theme" not in report.keys


def test_negative_10_logging_hardcoded_level(tmp_path):
    """
    label: NEGATIVE
    task: discovery
    why: logging.basicConfig uses configuration-like syntax but
         the level (DEBUG) and format are hardcoded literals.
         They are not read from environment variables.
         LOG_LEVEL string appears as a dict key label not an env var read.
         Hardcoded logging setup is not runtime configuration.
    """
    (tmp_path / "logger.py").write_text(
        "import logging\n"
        "LOG_LEVELS = {\n"
        "    'DEBUG': logging.DEBUG,\n"
        "    'INFO': logging.INFO,\n"
        "    'WARNING': logging.WARNING,\n"
        "}\n"
        "logging.basicConfig(\n"
        "    level=logging.DEBUG,\n"
        "    format='%(asctime)s %(levelname)s %(message)s',\n"
        ")\n"
        "logger = logging.getLogger(__name__)\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert "DEBUG" not in report.keys or not report.keys.get("DEBUG", {})
