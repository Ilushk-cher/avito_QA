import json
import ssl
from time import perf_counter
from urllib import error, request


class ApiResponse(object):
    def __init__(self, status_code, body, headers, elapsed_seconds, text):
        self.status_code = status_code
        self.body = body
        self.headers = headers
        self.elapsed_seconds = elapsed_seconds
        self.text = text

    def json(self):
        if isinstance(self.body, (dict, list)):
            return self.body
        raise TypeError("Response body is not JSON")


class ApiClient(object):
    def __init__(self, base_url, timeout=20, verify_ssl=False):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.ssl_context = self._build_ssl_context(verify_ssl)

    def create_item(self, payload):
        return self._request(
            "POST",
            "/api/1/item",
            payload=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    def get_item(self, item_id):
        return self._request("GET", "/api/1/item/{0}".format(item_id))

    def get_seller_items(self, seller_id):
        return self._request("GET", "/api/1/{0}/item".format(seller_id))

    def get_statistics(self, item_id):
        return self._request("GET", "/api/1/statistic/{0}".format(item_id))

    def delete_item_v2(self, item_id):
        return self._request("DELETE", "/api/2/item/{0}".format(item_id))

    def _request(self, method, path, payload=None, headers=None):
        url = "{0}{1}".format(self.base_url, path)
        body_bytes = None
        request_headers = dict(headers or {})

        if payload is not None:
            body_bytes = json.dumps(payload).encode("utf-8")

        req = request.Request(url=url, data=body_bytes, method=method, headers=request_headers)
        started_at = perf_counter()

        try:
            with request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as response:
                raw_body = response.read()
                elapsed = perf_counter() - started_at
                return self._build_response(
                    status_code=response.getcode(),
                    raw_body=raw_body,
                    headers=dict(response.headers.items()),
                    elapsed_seconds=elapsed,
                )
        except error.HTTPError as exc:
            raw_body = exc.read()
            elapsed = perf_counter() - started_at
            return self._build_response(
                status_code=exc.code,
                raw_body=raw_body,
                headers=dict(exc.headers.items()),
                elapsed_seconds=elapsed,
            )

    @staticmethod
    def _build_response(status_code, raw_body, headers, elapsed_seconds):
        text = raw_body.decode("utf-8") if raw_body else ""
        parsed_body = text

        if text:
            try:
                parsed_body = json.loads(text)
            except ValueError:
                parsed_body = text

        return ApiResponse(
            status_code=status_code,
            body=parsed_body,
            headers=headers,
            elapsed_seconds=elapsed_seconds,
            text=text,
        )

    @staticmethod
    def _build_ssl_context(verify_ssl):
        if verify_ssl:
            return ssl.create_default_context()
        return ssl._create_unverified_context()
