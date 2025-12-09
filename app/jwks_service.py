import json
import time
from typing import Dict, List, Optional
import requests
from cachetools import TTLCache
import logging

logger = logging.getLogger(f"uvicorn.{__name__}")


class JWKSService:
    def __init__(self, jwks_uri):
        self.jwks_cache = TTLCache(maxsize=1, ttl=10000)
        self.jwks_uri = jwks_uri

    def get_jwks(self) -> Dict:
        """Get JWKS from cache or fetch from IdP"""
        try:
            # Try to get from cache
            jwks = self.jwks_cache.get("jwks")
            if jwks:
                return jwks

            # Fetch from IdP
            logger.info(f"Fetching JWKS from {self.jwks_uri}")
            response = requests.get(
                self.jwks_uri, timeout=10, headers={"Accept": "application/json"}
            )
            response.raise_for_status()

            jwks = response.json()
            # Cache the result
            self.jwks_cache["jwks"] = jwks

            logger.info("Successfully fetched and cached JWKS")
            return jwks

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise Exception("Unable to fetch JWKS from IdP")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from JWKS endpoint: {e}")
            raise Exception("Invalid JWKS response")

    def get_key_by_kid(self, kid: str) -> Optional[Dict]:
        """Get a specific key by key ID (kid)"""
        jwks = self.get_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None


