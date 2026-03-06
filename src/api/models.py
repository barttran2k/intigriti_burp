#!/usr/bin/env python

class Program(object):
    def __init__(self, data):
        self.id = data.get("id", "")
        self.handle = data.get("handle", "")
        self.name = data.get("name", "")
        self.status = data.get("status", {}).get("value", "Unknown")
        self.type = data.get("type", {}).get("value", "Unknown")
        try:
            self.min_bounty = "{} {}".format(data.get("minBounty", {}).get("value", 0), data.get("minBounty", {}).get("currency", "EUR"))
            self.max_bounty = "{} {}".format(data.get("maxBounty", {}).get("value", 0), data.get("maxBounty", {}).get("currency", "EUR"))
        except Exception:
            self.min_bounty = "N/A"
            self.max_bounty = "N/A"
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
    def __init__(self, data):
        super(ProgramDetails, self).__init__(data)
        
        self.rules_html = data.get("rulesOfEngagement", {}).get("content", {}).get("description", "")
        
        self.scopes = []
        domains = data.get("domains", {}).get("content", [])
        for domain in domains:
            tier_value = domain.get("tier", {}).get("value", "")
            # Filter out Out of scope tiers
            if tier_value and tier_value.lower() in ["out of scope", "oos"]:
                continue
            self.scopes.append(ScopeElement(domain))

