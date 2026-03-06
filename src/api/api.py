#!/usr/bin/env python

class APIException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return "[{}] {}".format(self.code, self.message)


class IntigritiApi(object):
    def __init__(self, server, fetcher=None, token=""):
        self.useragent = "Intigriti Python client"
        self.server = server.rstrip("/")
        self.token = token

        if fetcher is None:
            try:
                import requests
                self.fetcher = requests
            except ImportError:
                raise ImportError(
                    "Request is not installed\nPlease run:\n  > pip install requests"
                )
        else:
            self.fetcher = fetcher

    @property
    def default_headers(self):
        default_headers = {"User-Agent": self.useragent}
        if self.token:
            default_headers["Authorization"] = "Bearer {}".format(self.token)
        return default_headers

    def handle_error(self, response):
        try:
            message = response.json().get("message", "Unknown API error")
        except Exception:
            message = "Unknown error"
        raise APIException(response.status_code, message)

    def get(self, path, params={}, headers={}):
        url = "{}/{}".format(self.server, path.lstrip("/"))
        headers_with_default = self.default_headers
        headers_with_default.update(headers)

        response = self.fetcher.get(url, params=params, headers=headers_with_default)
        if response.status_code != 200:
            self.handle_error(response)
        return response

    def authenticate(self):
        response = self.get("/programs", params={"limit": 1})
        if response.status_code == 200:
            return self.token
        self.handle_error(response)

    def get_programs(self):
        from .models import Program
        response = self.get("/programs", params={"limit": 500})
        records = response.json().get("records", [])
        return [Program(p) for p in records]

    def get_program_details(self, program_id):
        from .models import ProgramDetails
        response = self.get("/programs/{program_id}".format(program_id=program_id))
        return ProgramDetails(response.json())

    def change_server(self, url):
        self.server = url.rstrip("/")

    def change_token(self, token):
        self.token = token
