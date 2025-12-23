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

# Model configuration
MODEL_NAME = os.getenv(
    "MODEL_NAME",
    (
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        if MODEL_PROVIDER == "bedrock"
        else "claude-sonnet-4-5-20250929"
    ),
)
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "200"))

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
else:
    raise ValueError(
        f"Invalid MODEL_PROVIDER: {MODEL_PROVIDER}. Must be 'bedrock' or 'anthropic'"
    )
