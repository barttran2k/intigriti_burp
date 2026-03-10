#!/usr/bin/env python

import re
from json import dumps as json_dumps, loads as json_loads


try:
    basestring
except NameError:  # pragma: no cover - Python 3 fallback for local checks
    basestring = str


NON_WEB_TYPE_KEYWORDS = (
    "android",
    "ios",
    "mobile",
    "apk",
    "ipa",
    "desktop",
    "hardware",
)


DOMAIN_REGEX = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$",
    re.IGNORECASE,
)
IPV4_REGEX = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
ENDPOINT_REGEX = re.compile(
    r"^(?:(?P<scheme>https?)://)?(?P<hostport>[^/\s?#]+)(?P<path>/[^?#]*)?(?:\?[^#]*)?(?:#.*)?$",
    re.IGNORECASE,
)


class BurpScopeRule(object):
    def __init__(self, protocol, host_regex, port_regex, file_regex, raw_endpoint=""):
        self.protocol = (protocol or "any").strip().lower()
        self.host_regex = (host_regex or "").strip()
        self.port_regex = (port_regex or "").strip()
        self.file_regex = (file_regex or "").strip()
        self.raw_endpoint = raw_endpoint or ""

    @property
    def key(self):
        return (
            self.protocol,
            self.host_regex.lower(),
            self.port_regex.lower(),
            self.file_regex.lower(),
        )

    def to_dict(self):
        return {
            "enabled": True,
            "protocol": self.protocol,
            "host": self.host_regex,
            "port": self.port_regex,
            "file": self.file_regex,
        }


def _is_ipv4(host):
    if not IPV4_REGEX.match(host):
        return False
    try:
        parts = [int(x) for x in host.split(".")]
    except Exception:
        return False
    return all(0 <= p <= 255 for p in parts)


def _is_valid_domain(host):
    return bool(DOMAIN_REGEX.match(host))


def _is_non_web_scope(scope_type):
    s = (scope_type or "").strip().lower()
    return any(keyword in s for keyword in NON_WEB_TYPE_KEYWORDS)


def _split_host_and_port(hostport):
    host = hostport
    port = ""

    if host.startswith("[") or host.count(":") > 1:
        return None, None, "IPv6 endpoints are not supported"

    if ":" in host:
        maybe_host, maybe_port = host.rsplit(":", 1)
        if maybe_port.isdigit():
            host = maybe_host
            port = maybe_port
        else:
            return None, None, "Invalid port format"

    host = host.strip().lower().rstrip(".")
    if not host:
        return None, None, "Missing host"
    if port:
        try:
            port_int = int(port)
        except Exception:
            return None, None, "Invalid port"
        if port_int < 1 or port_int > 65535:
            return None, None, "Port out of range"
    return host, port, None


def _build_file_regex(path):
    if not path or path == "/":
        return ""

    normalized = "/" + path.lstrip("/")
    normalized = re.sub(r"/{2,}", "/", normalized)
    normalized = normalized.rstrip("/")
    if not normalized:
        return ""

    escaped = re.escape(normalized).replace(r"\*", ".*")
    return r"{}(?:/.*)?$".format(escaped)


def _build_host_regex(host):
    if host.startswith("*."):
        base_domain = host[2:]
        if not _is_valid_domain(base_domain):
            return None, "Invalid wildcard domain"
        return r"(?:.*\.){}$".format(re.escape(base_domain)), None

    if "*" in host:
        return None, "Wildcard is only supported as *.<domain>"

    if _is_ipv4(host):
        return r"{}$".format(re.escape(host)), None

    if _is_valid_domain(host):
        return r"{}$".format(re.escape(host)), None

    return None, "Host is neither valid domain nor IPv4"


def build_rule_from_scope(scope_element):
    endpoint = (getattr(scope_element, "endpoint", "") or "").strip()
    scope_type = (getattr(scope_element, "type", "") or "").strip()

    if not endpoint:
        return None, "Empty endpoint"
    if _is_non_web_scope(scope_type):
        return None, "Non-web scope type: {}".format(scope_type or "unknown")

    m = ENDPOINT_REGEX.match(endpoint)
    if not m:
        return None, "Unsupported endpoint format"

    scheme = (m.group("scheme") or "").lower()
    hostport = m.group("hostport") or ""
    path = m.group("path") or ""

    host, port, hostport_error = _split_host_and_port(hostport)
    if hostport_error:
        return None, hostport_error

    host_regex, host_error = _build_host_regex(host)
    if host_error:
        return None, host_error

    protocol = scheme if scheme in ("http", "https") else "any"
    port_regex = r"{}$".format(port) if port else ""
    file_regex = _build_file_regex(path)

    return (
        BurpScopeRule(
            protocol=protocol,
            host_regex=host_regex,
            port_regex=port_regex,
            file_regex=file_regex,
            raw_endpoint=endpoint,
        ),
        None,
    )


def _coerce_existing_rule(raw_entry):
    if isinstance(raw_entry, dict):
        host_regex = (raw_entry.get("host", "") or "").strip()
        if not host_regex:
            return None
        protocol = (raw_entry.get("protocol", "any") or "any").strip().lower()
        return BurpScopeRule(
            protocol=protocol,
            host_regex=host_regex,
            port_regex=(raw_entry.get("port", "") or "").strip(),
            file_regex=(raw_entry.get("file", "") or "").strip(),
            raw_endpoint="existing_rule",
        )

    if isinstance(raw_entry, basestring):
        class ScopeWrapper(object):
            pass

        scope_wrapper = ScopeWrapper()
        scope_wrapper.endpoint = raw_entry
        scope_wrapper.type = "url"
        rule, _ = build_rule_from_scope(scope_wrapper)
        return rule

    return None


def merge_scope_rules(existing_rules, new_rules):
    merged = list(existing_rules)
    keys = set(rule.key for rule in existing_rules)
    added = 0
    duplicates = 0

    for rule in new_rules:
        if rule.key in keys:
            duplicates += 1
            continue
        merged.append(rule)
        keys.add(rule.key)
        added += 1

    return merged, {"added": added, "duplicates": duplicates}


def _extract_target_scope(config):
    if not isinstance(config, dict):
        return {"advanced_mode": False, "include": [], "exclude": []}

    if "target" in config and isinstance(config.get("target"), dict):
        return config["target"].get(
            "scope", {"advanced_mode": False, "include": [], "exclude": []}
        )

    if "scope" in config and isinstance(config.get("scope"), dict):
        return config["scope"]

    if "advanced_mode" in config and "include" in config:
        return config

    return {"advanced_mode": False, "include": [], "exclude": []}


class TargetScopeImporter(object):
    def __init__(self, callbacks):
        self.callbacks = callbacks

    def _load_target_scope(self):
        for path in ("target.scope", ""):
            try:
                raw = self.callbacks.saveConfigAsJson(path)
            except Exception:
                continue
            try:
                data = json_loads(raw)
            except Exception:
                continue
            scope = _extract_target_scope(data)
            if scope:
                return scope
        return {"advanced_mode": False, "include": [], "exclude": []}

    def _apply_target_scope(self, include_rules, exclude_rules):
        payload = {
            "target": {
                "scope": {
                    "advanced_mode": True,
                    "include": include_rules,
                    "exclude": exclude_rules,
                }
            }
        }
        self.callbacks.loadConfigFromJson(json_dumps(payload))

    def import_scopes(self, scopes):
        scopes = scopes or []
        candidate_rules = []
        skipped = []

        for scope in scopes:
            rule, reason = build_rule_from_scope(scope)
            if reason:
                skipped.append(
                    {
                        "endpoint": (getattr(scope, "endpoint", "") or "").strip(),
                        "reason": reason,
                    }
                )
                continue
            candidate_rules.append(rule)

        try:
            current_scope = self._load_target_scope()
            include_entries = current_scope.get("include", []) or []
            exclude_entries = current_scope.get("exclude", []) or []

            existing_rules = []
            for item in include_entries:
                coerced = _coerce_existing_rule(item)
                if coerced:
                    existing_rules.append(coerced)

            merged_rules, merge_stats = merge_scope_rules(existing_rules, candidate_rules)
            include_payload = [rule.to_dict() for rule in merged_rules]
            self._apply_target_scope(include_payload, exclude_entries)
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "added": 0,
                "duplicates": 0,
                "skipped": len(skipped),
                "skipped_details": skipped,
                "message": "Import failed: {}".format(e),
            }

        added = merge_stats["added"]
        duplicates = merge_stats["duplicates"]
        skipped_count = len(skipped)

        return {
            "ok": True,
            "added": added,
            "duplicates": duplicates,
            "skipped": skipped_count,
            "skipped_details": skipped,
            "message": "Added {}, Duplicates {}, Skipped {}".format(
                added, duplicates, skipped_count
            ),
        }
