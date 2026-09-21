from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit, urlunsplit

from .errors import ControlPlaneError, FailureCode


_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost", ".home", ".lan")


@dataclass(slots=True)
class ValidatedURL:
    normalized: str
    scheme: str
    host: str
    port: int
    path: str


@dataclass(slots=True)
class URLPolicy:
    allowed_hosts: set[str] = field(default_factory=set)
    allowed_ports: set[int] = field(default_factory=lambda: {443})
    allow_http_loopback_for_tests: bool = False
    max_url_length: int = 4096

    def _host_allowed(self, host: str) -> bool:
        if not self.allowed_hosts:
            return False
        for pattern in self.allowed_hosts:
            p = pattern.lower().rstrip(".")
            if p.startswith("*."):
                suffix = p[1:]  # includes leading dot
                if host.endswith(suffix) and host != suffix[1:]:
                    return True
            elif host == p:
                return True
        return False


class URLGuard:
    def __init__(self, policy: URLPolicy) -> None:
        self.policy = policy

    @staticmethod
    def _normalize_host(host: str) -> str:
        try:
            return host.rstrip(".").encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ControlPlaneError(
                FailureCode.BLOCKED_UNSAFE_URL,
                "Host cannot be normalized safely",
                {"host": host},
            ) from exc

    @staticmethod
    def _reject_non_global_ip(host: str) -> None:
        try:
            ip = ipaddress.ip_address(host.split("%", 1)[0])
        except ValueError:
            return
        if not ip.is_global:
            raise ControlPlaneError(
                FailureCode.BLOCKED_SSRF_TARGET,
                "Literal IP is not globally routable",
                {"host": host},
            )

    def validate(self, raw_url: str) -> ValidatedURL:
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise ControlPlaneError(FailureCode.BLOCKED_UNSAFE_URL, "URL is required")
        if len(raw_url) > self.policy.max_url_length:
            raise ControlPlaneError(FailureCode.BLOCKED_UNSAFE_URL, "URL exceeds maximum length")
        if _CONTROL_CHAR_RE.search(raw_url) or _CONTROL_CHAR_RE.search(unquote(raw_url)):
            raise ControlPlaneError(FailureCode.BLOCKED_UNSAFE_URL, "URL contains control characters")

        parts = urlsplit(raw_url.strip())
        scheme = parts.scheme.lower()
        if scheme not in {"https", "http"}:
            raise ControlPlaneError(
                FailureCode.BLOCKED_UNSAFE_URL,
                "Only HTTPS is allowed in production",
                {"scheme": scheme},
            )
        if parts.username is not None or parts.password is not None:
            raise ControlPlaneError(
                FailureCode.BLOCKED_SECRET_EXPOSURE_RISK,
                "Credentials in URLs are prohibited",
            )
        if not parts.hostname:
            raise ControlPlaneError(FailureCode.BLOCKED_UNSAFE_URL, "URL has no hostname")

        host = self._normalize_host(parts.hostname)
        self._reject_non_global_ip(host)
        if host == "localhost" or host.endswith(_BLOCKED_HOST_SUFFIXES):
            if not (scheme == "http" and self.policy.allow_http_loopback_for_tests and host == "localhost"):
                raise ControlPlaneError(
                    FailureCode.BLOCKED_SSRF_TARGET,
                    "Local or internal hostname is prohibited",
                    {"host": host},
                )

        if scheme == "http" and not (
            self.policy.allow_http_loopback_for_tests and host == "localhost"
        ):
            raise ControlPlaneError(
                FailureCode.BLOCKED_UNSAFE_URL,
                "Plain HTTP is prohibited outside isolated tests",
            )

        try:
            port = parts.port or (443 if scheme == "https" else 80)
        except ValueError as exc:
            raise ControlPlaneError(FailureCode.BLOCKED_UNSAFE_URL, "Invalid port") from exc
        if port not in self.policy.allowed_ports and not (
            self.policy.allow_http_loopback_for_tests and host == "localhost" and port >= 1024
        ):
            raise ControlPlaneError(
                FailureCode.BLOCKED_UNSAFE_URL,
                "Port is not allowed",
                {"port": port},
            )
        if not self.policy._host_allowed(host) and not (
            self.policy.allow_http_loopback_for_tests and host == "localhost"
        ):
            raise ControlPlaneError(
                FailureCode.BLOCKED_DOMAIN_NOT_ALLOWED,
                "Host is not in the exact allowlist",
                {"host": host},
            )

        netloc = host
        default_port = 443 if scheme == "https" else 80
        if port != default_port:
            netloc = f"{host}:{port}"
        normalized = urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
        return ValidatedURL(normalized, scheme, host, port, parts.path or "/")

    def validate_redirect_chain(self, urls: list[str]) -> list[ValidatedURL]:
        if not urls:
            raise ControlPlaneError(FailureCode.BLOCKED_UNSAFE_URL, "Redirect chain is empty")
        validated: list[ValidatedURL] = []
        for index, url in enumerate(urls):
            try:
                validated.append(self.validate(url))
            except ControlPlaneError as exc:
                if index > 0 and exc.code in {
                    FailureCode.BLOCKED_DOMAIN_NOT_ALLOWED,
                    FailureCode.BLOCKED_SSRF_TARGET,
                    FailureCode.BLOCKED_UNSAFE_URL,
                }:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_REDIRECT_SCOPE_ESCAPE,
                        "Redirect left the authorized URL scope",
                        {"redirect_index": index, "cause": exc.to_dict()},
                    ) from exc
                raise
        return validated

    @staticmethod
    def validate_resolved_ips(ips: list[str]) -> None:
        if not ips:
            raise ControlPlaneError(
                FailureCode.BLOCKED_SSRF_TARGET,
                "DNS resolution returned no addresses",
            )
        for raw in ips:
            try:
                ip = ipaddress.ip_address(raw.split("%", 1)[0])
            except ValueError as exc:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_SSRF_TARGET,
                    "Resolved address is malformed",
                    {"address": raw},
                ) from exc
            if not ip.is_global:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_SSRF_TARGET,
                    "Resolved address is not globally routable",
                    {"address": raw},
                )
