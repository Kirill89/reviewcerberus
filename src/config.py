import os

from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

# Model provider selection
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "bedrock")

# AWS Bedrock configuration (required only if MODEL_PROVIDER=bedrock)
# Note: boto3 expects strings, so we keep these as strings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "")

# Anthropic API configuration (required only if MODEL_PROVIDER=anthropic)
# Convert to SecretStr for secure handling
_anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_KEY = SecretStr(_anthropic_key)

# Ollama configuration (required only if MODEL_PROVIDER=ollama)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Moonshot configuration (required only if MODEL_PROVIDER=moonshot)
_moonshot_key = os.getenv("MOONSHOT_API_KEY", "")
MOONSHOT_API_KEY = SecretStr(_moonshot_key)
MOONSHOT_API_BASE = os.getenv("MOONSHOT_API_BASE", "https://api.moonshot.ai/v1")


# Model configuration
def _get_default_model() -> str:
    match MODEL_PROVIDER:
        case "bedrock":
            return "us.anthropic.claude-opus-4-5-20251101-v1:0"
        case "anthropic":
            return "claude-opus-4-5-20251101"
        case "moonshot":
            return "kimi-k2.5"
        case _:  # ollama
            return "deepseek-v3.1:671b-cloud"


MODEL_NAME = os.getenv("MODEL_NAME", _get_default_model())
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "10000"))
TOOL_CALL_LIMIT = int(os.getenv("TOOL_CALL_LIMIT", "100"))

# Verification model (optional, defaults to MODEL_NAME)
VERIFY_MODEL_NAME = os.getenv("VERIFY_MODEL_NAME", MODEL_NAME)

# Context management
CONTEXT_COMPACT_THRESHOLD = int(os.getenv("CONTEXT_COMPACT_THRESHOLD", "140000"))
MAX_DIFF_PER_FILE = int(os.getenv("MAX_DIFF_PER_FILE", "10000"))  # characters

# Validate required credentials based on provider
if MODEL_PROVIDER == "bedrock":
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME]):
        raise ValueError(
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION_NAME "
            "are required when MODEL_PROVIDER=bedrock"
        )
elif MODEL_PROVIDER == "anthropic":
    if not _anthropic_key:
        raise ValueError("ANTHROPIC_API_KEY is required when MODEL_PROVIDER=anthropic")
elif MODEL_PROVIDER == "ollama":
    # Ollama has no required credentials, base_url has default
    pass
elif MODEL_PROVIDER == "moonshot":
    if not _moonshot_key:
        raise ValueError("MOONSHOT_API_KEY is required when MODEL_PROVIDER=moonshot")
else:
    raise ValueError(
        f"Invalid MODEL_PROVIDER: {MODEL_PROVIDER}. "
        f"Must be 'bedrock', 'anthropic', 'ollama', or 'moonshot'"
    )
