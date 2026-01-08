import os

from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()

# Model provider selection
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "bedrock")  # "bedrock" or "anthropic"

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

# Model configuration
MODEL_NAME = os.getenv(
    "MODEL_NAME",
    (
        "us.anthropic.claude-opus-4-5-20251101-v1:0"
        if MODEL_PROVIDER == "bedrock"
        else (
            "claude-opus-4-5-20251101"
            if MODEL_PROVIDER == "anthropic"
            else "deepseek-v3.1:671b-cloud"
        )  # ollama default
    ),
)
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "10000"))
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "200"))

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
else:
    raise ValueError(
        f"Invalid MODEL_PROVIDER: {MODEL_PROVIDER}. "
        f"Must be 'bedrock', 'anthropic', or 'ollama'"
    )
