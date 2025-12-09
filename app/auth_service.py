import requests
from typing import Dict, Optional
import logging

from common import TokenResponse


logger = logging.getLogger(f"uvicorn.{__name__}")


class AuthService:
    def __init__(self, token_endpoint, client_id, client_secret):
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.client_secret = client_secret

    def authenticate_user(
        self, username: str, password: str
    ) -> Optional[TokenResponse]:
        """Authenticate user using ROPC flow with IdP"""
        try:
            # Prepare the request data for ROPC flow
            data = {
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid profile email",
            }

            # Make request to IdP
            logger.debug(f"Authenticating user {username} via IdP")
            response = requests.post(
                self.token_endpoint,
                data=data,
                timeout=30,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()
            token_data = response.json()

            # Convert to our response model
            return TokenResponse(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data["expires_in"],
                scope=token_data.get("scope", "openid profile email"),
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
        except KeyError as e:
            logger.error(f"Invalid response from IdP: missing key {e}")
            return None

    def refresh_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """Refresh access token using refresh token"""
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid profile email",
            }

            response = requests.post(
                self.token_endpoint,
                data=data,
                timeout=30,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()
            token_data = response.json()

            return TokenResponse(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data["expires_in"],
                scope=token_data.get("scope", "openid profile email"),
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh failed: {e}")
            return None
