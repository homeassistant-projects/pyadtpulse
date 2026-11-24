"""ADT Pulse multi-factor authentication (MFA) challenge."""

import re
from dataclasses import dataclass

# The MFA page (mfa/mfaSignIn.jsp) runs a React app configured by a
# window.g.mfa object in an inline script. The app talks to Pulse through a
# proxy servlet, authenticated by the pre-auth token and "sat" id in that
# object.
_G_MFA_FIELDS = {
    "pre_auth_token": r"xPreAuthToken:\s*['\"]([^'\"]+)['\"]",
    "login": r"xLogin:\s*['\"]([^'\"]+)['\"]",
    "sat": r"\bsat:\s*['\"]([^'\"]+)['\"]",
    "proxy_uri": r"proxyServletUrl:\s*['\"]([^'\"]+)['\"]",
    "client_type": r"xClientType:\s*['\"]([^'\"]+)['\"]",
}

# REST path that returns the MFA state and the commands the server offers,
# each with the REST path to call it.
ADT_MFA_STATE_HREF = "rest/icontrol/ui/client/multiFactorAuth"
ADT_MFA_DEFAULT_PROXY_URI = "/nga/serv/RunRRAProxy"
ADT_POST_SIGNIN_URI = "/access/PostSigninProcessServ"
ADT_MFA_API_VERSION = "7.0"


@dataclass(frozen=True)
class PulseMFAChallenge:
    """The MFA challenge Pulse issued for one sign-in."""

    pre_auth_token: str
    login: str
    sat: str
    proxy_uri: str = ADT_MFA_DEFAULT_PROXY_URI
    client_type: str = "web"

    @classmethod
    def from_page(cls, page: str | None) -> "PulseMFAChallenge | None":
        """Parse the challenge from the MFA page, or None if it is not there."""
        if not page:
            return None
        values: dict[str, str] = {}
        for field, pattern in _G_MFA_FIELDS.items():
            m = re.search(pattern, page)
            if m is not None:
                values[field] = m.group(1)
        if not all(k in values for k in ("pre_auth_token", "login", "sat")):
            return None
        return cls(**values)

    def __repr__(self) -> str:
        """Keep the pre-auth token out of logs."""
        return (
            f"PulseMFAChallenge(login={self.login!r}, sat={self.sat!r}, "
            f"proxy_uri={self.proxy_uri!r})"
        )

    def proxy_url(self, href: str) -> str:
        """Return the proxy URI, relative to the API version, for a REST path."""
        return f"{self.proxy_uri}?href={href}&sat={self.sat}"

    def headers(self, x_token: str | None = None) -> dict[str, str]:
        """Return the headers the MFA REST calls need."""
        headers = {
            "Accept": "application/json",
            "X-format": "json",
            "X-locale": "en-US",
            "X-version": ADT_MFA_API_VERSION,
            "X-clientType": self.client_type,
            "X-login": self.login,
        }
        if x_token:
            headers["X-token"] = x_token
        else:
            headers["X-preAuthToken"] = self.pre_auth_token
        return headers
