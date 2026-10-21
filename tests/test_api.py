from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ibiki_key.engines.api_server import LocalApiServer


class ApiTests(unittest.TestCase):
    def test_auth_and_variable_update(self) -> None:
        variables: dict[str, object] = {}
        server = LocalApiServer(
            lambda: {"ok": True},
            lambda profile, reason: None,
            lambda macro, source: None,
            lambda: variables,
            lambda name, value: variables.__setitem__(name, value),
        )
        server.start(0, "secret")
        assert server.server is not None
        port = server.server.server_address[1]
        try:
            with self.assertRaises(HTTPError) as failure:
                urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            self.assertEqual(failure.exception.code, 401)

            request = Request(
                f"http://127.0.0.1:{port}/v1/status",
                headers={"Authorization": "Bearer secret"},
            )
            with urlopen(request, timeout=2) as response:
                self.assertTrue(json.load(response)["ok"])

            request = Request(
                f"http://127.0.0.1:{port}/v1/status",
                method="OPTIONS",
                headers={"Origin": "http://localhost:3000"},
            )
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 204)
                self.assertEqual(
                    response.headers["Access-Control-Allow-Origin"],
                    "http://localhost:3000",
                )

            request = Request(
                f"http://127.0.0.1:{port}/v1/variables/test",
                data=json.dumps({"value": 42}).encode(),
                method="POST",
                headers={
                    "Authorization": "Bearer secret",
                    "Content-Type": "application/json",
                },
            )
            with urlopen(request, timeout=2) as response:
                self.assertTrue(json.load(response)["ok"])
            self.assertEqual(variables["test"], 42)
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
