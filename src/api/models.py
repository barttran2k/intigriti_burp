#!/usr/bin/env python

MISSING = object()

try:
    NUMBER_TYPES = (int, long, float)
except NameError:  # pragma: no cover - Python 3 fallback for local checks
    NUMBER_TYPES = (int, float)


def _to_money(value, currency="EUR"):
    if value is None:
        return None
    if isinstance(value, NUMBER_TYPES):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return "{} {}".format(value, currency or "EUR")
    try:
        as_number = float(value)
        if as_number.is_integer():
            as_number = int(as_number)
        return "{} {}".format(as_number, currency or "EUR")
    except Exception:
        return None


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


class Program(object):
    def __init__(self, data, fallback_data=None):
        data = data or {}
        fallback_data = fallback_data or {}

        self.raw = data
        self.id = data.get("id", "")
        self.handle = data.get("handle", "")
        self.name = data.get("name", "")
        self.status = data.get("status", {}).get("value", "Unknown")
        self.type = data.get("type", {}).get("value", "Unknown")

        self.min_bounty = _extract_money(data, "minBounty")
        self.max_bounty = _extract_money(data, "maxBounty")
        if self.min_bounty is None:
            self.min_bounty = _extract_money(fallback_data, "minBounty")
        if self.max_bounty is None:
            self.max_bounty = _extract_money(fallback_data, "maxBounty")

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

