from typing import Any

import boto3
from botocore.config import Config
from langchain.chat_models import init_chat_model

from ...config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION_NAME,
    AWS_SECRET_ACCESS_KEY,
)
from .bedrock_caching import CachingBedrockClient


def create_bedrock_model(model_name: str, max_tokens: int) -> Any:
    """Create a Bedrock model with caching support.

    Args:
        model_name: The Bedrock model identifier
        max_tokens: Maximum tokens for model output

    Returns:
        Configured Bedrock model with caching wrapper
    """
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

    return init_chat_model(
        model_name,
        client=caching_bedrock_client,
        model_provider="bedrock_converse",
        temperature=0.0,
        max_tokens=max_tokens,
    )
