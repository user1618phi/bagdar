"""HTTP API: a real server on a free port, exercised with real requests."""

import http.client
import json
import threading
import unittest
import urllib.error
import urllib.request

from meje.server import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(port=0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read(), response.headers.get("Content-Type")
        except urllib.error.HTTPError as error:
            return error.code, error.read(), error.headers.get("Content-Type")

    def test_health_and_pack(self):
        status, body, _ = self.request("/health")
        self.assertEqual((status, json.loads(body)), (200, {"status": "ok"}))
        status, body, _ = self.request("/api/pack")
        pack = json.loads(body)
        self.assertEqual((status, len(pack["skills"]), pack["items"]), (200, 20, 80))

    def test_state_round_trip(self):
        status, body, _ = self.request("/api/state", {"targets": ["astar"], "history": []})
        state = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(state["current"]["action"], "practice")
        self.assertNotIn("answer", state["current"]["item"])
        item = state["current"]["item"]["id"]
        event = {"skill": state["current"]["skill"], "action": "practice", "item": item, "choice": 0, "sure": True}
        status, body, _ = self.request("/api/state", {"targets": ["astar"], "history": [event]})
        self.assertEqual(status, 200)
        self.assertIn("why", json.loads(body)["last"])

    def test_model_and_compare(self):
        status, body, _ = self.request("/api/model")
        self.assertEqual((status, json.loads(body)["policy"]), (200, ["explain", "practice", "advance"]))
        status, body, _ = self.request("/api/compare", {"targets": ["astar", "viterbi", "bellman"], "history": []})
        results = {r["algorithm"]: r for r in json.loads(body)["results"]}
        self.assertTrue(results["A*"]["optimal"])
        self.assertLessEqual(results["A*"]["expanded"], results["UCS"]["expanded"])

    def test_bad_requests_are_rejected_politely(self):
        self.assertEqual(self.request("/api/state", raw=b"{not json")[0], 400)
        self.assertEqual(self.request("/api/state", raw=b"[1, 2]")[0], 400)
        self.assertEqual(self.request("/api/nope")[0], 404)
        self.assertEqual(self.request("/api/nope", {})[0], 404)
        status, body, _ = self.request("/api/state", {"targets": "x", "history": {"a": 1}, "pin": 5})
        self.assertEqual(status, 200)

    def test_security_headers_are_sent(self):
        request = urllib.request.Request(self.base + "/")
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_oversized_request_is_rejected(self):
        """The server answers from the declared length alone, before any body is read."""
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        connection.putrequest("POST", "/api/state")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "50000000")
        connection.endheaders()
        self.assertEqual(connection.getresponse().status, 400)
        connection.close()

    def test_hostile_requests_get_a_plain_error(self):
        """Found in review: these used to escape as unhandled exceptions."""
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        connection.putrequest("POST", "/api/state")
        connection.putheader("Content-Length", "-1")
        connection.endheaders()
        self.assertEqual(connection.getresponse().status, 400)
        connection.close()
        self.assertEqual(self.request("/api/state", raw=b"[" * 200_000)[0], 400)
        self.assertEqual(self.request("/" + "a" * 3000)[0], 404)
        self.assertEqual(self.request("/a%00b")[0], 404)

    def test_static_files_and_path_traversal(self):
        status, body, content_type = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(b"Meje", body)
        self.assertEqual(self.request("/../meje/server.py")[0], 404)
        self.assertEqual(self.request("/missing.js")[0], 404)


if __name__ == "__main__":
    unittest.main()
