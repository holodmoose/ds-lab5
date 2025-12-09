from typing import Dict, Optional
from jose import jwt
from datetime import datetime
import time
import logging
from common import *

logger = logging.getLogger(f"uvicorn.{__name__}")


class JWTService:
    def __init__(self, jwks_service):
        self.algorithm = "RS256"
        self.jwks_service = jwks_service

    def validate_token(self, token: str) -> bool:
        """Validate JWT token using cached JWKS"""
        try:
            # 1. Decode header without validation to get KID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            if not kid:
                logger.error("JWT token missing 'kid' in header")
                return False

            # 2. Get the public key by KID
            key = self.jwks_service.get_key_by_kid(kid)
            if not key:
                logger.error(f"No key found for KID: {kid}")
                return False

            # 3. Verify the token
            options = {
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": False,
                "require_exp": True,
            }

            # Decode with validation
            payload = jwt.decode(
                token,
                key,
                algorithms=[self.algorithm],
                options=options,
            )

            # 4. Additional validation for OpenID Connect
            if not self._validate_oidc_claims(payload):
                return False

            logger.debug(f"Token validated for user: {payload.get('sub')}")
            return True

        except jwt.JWTError as e:
            logger.error(f"JWT validation error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            return False

    def _validate_oidc_claims(self, payload: Dict) -> bool:
        """Validate OpenID Connect specific claims"""
        # Check for required scope
        scope = payload.get("scope", "")
        if "openid" not in scope.split():
            logger.error("Missing 'openid' scope in token")
            return False

        # Check expiration
        exp = payload.get("exp")
        if not exp:
            logger.error("Missing 'exp' claim")
            return False

        if exp < time.time():
            logger.error("Token expired (exp claim)")
            return False

        return True

    def extract_user_info(self, token: str) -> Optional[UserInfo]:
        """Extract user information from JWT token"""
        try:
            # Decode without validation (we've already validated)
            payload = jwt.get_unverified_claims(token)
            print("payload", payload)
            return UserInfo(
                sub=payload.get("sub"),
                name=payload.get("preferred_username"),
            )
        except Exception as e:
            logger.error(f"Failed to extract user info: {e}")
            return None

    def get_claims(self, token: str) -> Optional[JWTClaims]:
        """Get JWT claims"""
        try:
            payload = jwt.get_unverified_claims(token)

            return JWTClaims(
                sub=payload.get("sub"),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                scope=payload.get("scope"),
                email=payload.get("email"),
                name=payload.get("name"),
            )
        except Exception as e:
            logger.error(f"Failed to get claims: {e}")
            return None
