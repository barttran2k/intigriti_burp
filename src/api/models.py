#!/usr/bin/env python

MISSING = object()

try:
    NUMBER_TYPES = (int, long, float)
except NameError:  # pragma: no cover - Python 3 fallback for local checks
    NUMBER_TYPES = (int, float)


def _to_money(value, currency="EUR"):
    value = _to_number(value)
    if value is None:
        return None
    return "{} {}".format(value, currency or "EUR")


def _to_number(value):
    if value is None:
        return None
    if isinstance(value, NUMBER_TYPES):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    try:
        as_number = float(value)
    except Exception:
        return None
    if as_number.is_integer():
        return int(as_number)
    return as_number


def _extract_money(data, key):
    if not isinstance(data, dict):
        return None

    raw = data.get(key, MISSING)
    if raw is MISSING:
        return None

    if isinstance(raw, dict):
        value = raw.get("value", MISSING)
        if value is MISSING:
            return None
        return _to_money(value, raw.get("currency", "EUR"))

    return _to_money(raw, data.get("{}Currency".format(key), "EUR"))


def _extract_money_value(data, key):
    if not isinstance(data, dict):
        return None

    raw = data.get(key, MISSING)
    if raw is MISSING:
        return None

    if isinstance(raw, dict):
        value = raw.get("value", MISSING)
        if value is MISSING:
            return None
        return _to_number(value)

    return _to_number(raw)


class Program(object):
    def __init__(self, data, fallback_data=None):
        data = data or {}
        fallback_data = fallback_data or {}

        self.raw = data
        self.id = data.get("id", "")
        self.handle = data.get("handle", "")
        self.name = data.get("name", "")
        self.status = data.get("status", {}).get("value", "Unknown")
        self.api_type = data.get("type", {}).get("value", "Unknown")
        self.type = self.api_type

        self.min_bounty = _extract_money(data, "minBounty")
        self.max_bounty = _extract_money(data, "maxBounty")
        if self.min_bounty is None:
            self.min_bounty = _extract_money(fallback_data, "minBounty")
        if self.max_bounty is None:
            self.max_bounty = _extract_money(fallback_data, "maxBounty")

        self.min_bounty_value = _extract_money_value(data, "minBounty")
        self.max_bounty_value = _extract_money_value(data, "maxBounty")
        if self.min_bounty_value is None:
            self.min_bounty_value = _extract_money_value(fallback_data, "minBounty")
        if self.max_bounty_value is None:
            self.max_bounty_value = _extract_money_value(fallback_data, "maxBounty")

        self.min_bounty_value = self.min_bounty_value if self.min_bounty_value is not None else 0
        self.max_bounty_value = self.max_bounty_value if self.max_bounty_value is not None else 0
        self.program_category = "Bug bounty" if self.max_bounty_value > 0 else "VDP"

        self.min_bounty = self.min_bounty or "N/A"
        self.max_bounty = self.max_bounty or "N/A"
        self.industry = data.get("industry", "")
        
    @property
    def title(self):
        return self.name

class ScopeElement(object):
    def __init__(self, data):
        self.id = data.get("id", "")
        self.type = data.get("type", {}).get("value", "Unknown")
        self.endpoint = data.get("endpoint", "")
        self.tier = data.get("tier", {}).get("value", "")
        self.description = data.get("description", "")
        self.scope = self.endpoint

class ProgramDetails(Program):
    def __init__(self, data, fallback_data=None):
        super(ProgramDetails, self).__init__(data, fallback_data=fallback_data)
        
        self.rules_html = data.get("rulesOfEngagement", {}).get("content", {}).get("description", "")
        
        self.scopes = []
        domains = data.get("domains", {}).get("content", [])
        for domain in domains:
            tier_value = domain.get("tier", {}).get("value", "")
            # Filter out Out of scope tiers
            if tier_value and tier_value.lower() in ["out of scope", "oos"]:
                continue
            self.scopes.append(ScopeElement(domain))

