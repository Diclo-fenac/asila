from datetime import datetime, timedelta, timezone

import httpx
from jose import JWTError, jwt


class OIDCConfigurationError(RuntimeError):
    pass


class OIDCVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str | None = None,
        cache_ttl: timedelta = timedelta(hours=1),
    ):
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._jwks: dict | None = None
        self._jwks_expires_at: datetime | None = None

    async def _load_jwks(self) -> dict:
        if not self.issuer or not self.audience:
            raise OIDCConfigurationError("OIDC issuer and audience are required")
        now = datetime.now(timezone.utc)
        if self._jwks and self._jwks_expires_at and self._jwks_expires_at > now:
            return self._jwks

        jwks_url = self.jwks_url
        async with httpx.AsyncClient(timeout=10) as client:
            if not jwks_url:
                discovery = await client.get(
                    f"{self.issuer}/.well-known/openid-configuration"
                )
                discovery.raise_for_status()
                jwks_url = discovery.json().get("jwks_uri")
            if not jwks_url:
                raise OIDCConfigurationError("OIDC provider does not expose jwks_uri")
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()

        if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
            raise OIDCConfigurationError("OIDC JWKS response is invalid")
        self._jwks = jwks
        self._jwks_expires_at = now + self.cache_ttl
        return jwks

    async def verify(self, token: str) -> dict:
        if not token:
            raise JWTError("Token is required")
        try:
            if not self.issuer or not self.audience:
                raise OIDCConfigurationError("OIDC issuer and audience are required")
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            key_id = header.get("kid")
            if algorithm not in {"RS256", "ES256", "EdDSA"}:
                raise JWTError("Unsupported OIDC signing algorithm")
            jwks = await self._load_jwks()
            keys = jwks["keys"]
            if key_id:
                keys = [key for key in keys if key.get("kid") == key_id]
            if not keys:
                raise JWTError("OIDC signing key not found")
            return jwt.decode(
                token,
                {"keys": keys},
                algorithms=[algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"require_sub": True, "require_exp": True},
            )
        except (JWTError, httpx.HTTPError, ValueError) as exc:
            if isinstance(exc, OIDCConfigurationError):
                raise
            raise JWTError("OIDC token validation failed") from exc
