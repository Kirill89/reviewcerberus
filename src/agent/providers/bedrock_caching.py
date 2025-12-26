from typing import Any

MAX_CACHE_POINTS = 4
CACHE_POINT = {
    "cachePoint": {
        "type": "default",
    },
}


class CachingBedrockClient:
    def __init__(self, client: Any) -> None:
        self._client = client

    def converse(self, **kwargs: Any) -> Any:
        cache_points_used = 0

        if "system" in kwargs and kwargs["system"]:
            if cache_points_used < MAX_CACHE_POINTS:
                kwargs["system"].append(CACHE_POINT)
                cache_points_used += 1

        if "messages" in kwargs and len(kwargs["messages"]) > 0:
            for message in reversed(kwargs["messages"]):

                if cache_points_used >= MAX_CACHE_POINTS:
                    break

                if message.get("role", "") != "user":
                    continue

                if "content" not in message or not isinstance(message["content"], list):
                    continue

                message["content"].append(CACHE_POINT)
                cache_points_used += 1

        return self._client.converse(**kwargs)

    def converse_stream(self, **kwargs: Any) -> Any:
        return self._client.converse_stream(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
