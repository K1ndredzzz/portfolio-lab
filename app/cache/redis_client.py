import redis
import hashlib
import json
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


class RedisClient:
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )

    def build_key(self, dataset_version: str, model: str, as_of_date: str,
                  horizon_months: int, weights_hash: str) -> str:
        """Build versioned cache key."""
        return f"pl:v1:{dataset_version}:quote:{model}:{as_of_date}:{horizon_months}:{weights_hash}"

    def get(self, key: str) -> Optional[dict]:
        """Get cached value."""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"Redis get error: {e}")
        return None

    def set(self, key: str, value: dict, ttl: int = None) -> bool:
        """Set cached value with optional TTL."""
        try:
            ttl = ttl or settings.CACHE_DEFAULT_TTL_SECONDS
            self.client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return self.client.ping()
        except Exception:
            return False


def compute_weights_hash(weights: dict) -> str:
    """Compute deterministic hash for portfolio weights."""
    # Sort keys for deterministic hashing
    sorted_weights = {k: round(v, 6) for k, v in sorted(weights.items())}
    weights_str = json.dumps(sorted_weights, sort_keys=True)
    return hashlib.sha256(weights_str.encode()).hexdigest()


# Global Redis client instance
redis_client = RedisClient()
