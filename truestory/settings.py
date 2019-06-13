"""TrueStory default settings."""


import os


# Server environment and application settings.
DEBUG = not os.getenv("GAE_ENV", "").startswith("standard")
CONFIG = os.getenv("FLASK_CONFIG", "default")
DATASTORE_ENV = os.getenv("DATASTORE_ENV_YAML")
APP_NAME = "TrueStory"
PROJECT_ID = APP_NAME.lower()
LOCATION = "europe-west1"

# Miscellaneous.
TIMEOUT = 10  # seconds
ENCODING = "utf-8"
DEFAULT_MAIL = "hello@truestory.one"
PROJECT_NAME = PROJECT_ID

# Persistent logging (used while running outside Google Cloud).
LOGFILE = f"{PROJECT_NAME}.log"

# Article content display/retrieval settings on home, individual pages and API.
HOME_ARTICLE_MAX_SIZE = 256
FULL_ARTICLE_MAX_SIZE = 1024
AUTHORS_MAX_SIZE = 64
API_MAX_RELATED_ARTICLES = 3
