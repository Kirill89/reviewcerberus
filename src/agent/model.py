from typing import Any

import boto3
from botocore.config import Config
from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

from ..config import (
    ANTHROPIC_API_KEY,
    AWS_ACCESS_KEY_ID,
    AWS_REGION_NAME,
    AWS_SECRET_ACCESS_KEY,
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    MODEL_PROVIDER,
)
from .caching_bedrock_client import CachingBedrockClient

model: Any

if MODEL_PROVIDER == "bedrock":
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION_NAME,
        endpoint_url=f"https://bedrock-runtime.{AWS_REGION_NAME}.amazonaws.com",
        config=Config(
            read_timeout=180.0,
            retries={
                "max_attempts": 3,
            },
        ),
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    caching_bedrock_client = CachingBedrockClient(bedrock_client)

    model = init_chat_model(
        MODEL_NAME,
        client=caching_bedrock_client,
        model_provider="bedrock_converse",
        temperature=0.0,
        max_tokens=MAX_OUTPUT_TOKENS,
    )

elif MODEL_PROVIDER == "anthropic":
    # Prompt caching is handled automatically by the Anthropic SDK
    # ANTHROPIC_API_KEY is guaranteed to be non-None here (validated in config.py)
    # Using type: ignore because langchain-anthropic has complex typing requirements
    model = ChatAnthropic(
        model_name=MODEL_NAME,
        api_key=ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens_to_sample=MAX_OUTPUT_TOKENS,
        timeout=180.0,
        stop=[],
    )

else:
    raise ValueError(f"Unsupported MODEL_PROVIDER: {MODEL_PROVIDER}")
