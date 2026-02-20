from connectors.base import BaseConnector


class LinkedInStubConnector(BaseConnector):
    source = "linkedin_manual_only"

    def search(self, preferences: dict) -> list:
        return []
