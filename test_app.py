"""API integration tests using separate SQLite files, never the user's database."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import database
from app import create_app


SAMPLE = {
    "name": "John Doe", "email": "john.doe@example.com", "phone": "067765434567",
    "address": "John Doe Street, Innsbruck", "country": "Austria",
}


class UserApiTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).parent / ".qa" / f"test-{uuid4().hex}.db"
        self.path.parent.mkdir(exist_ok=True)
        self.database_patch = patch.object(database, "DATABASE_PATH", self.path)
        self.database_patch.start()
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.database_patch.stop()
        self.path.unlink(missing_ok=True)

    def add_user(self, user=None):
        response = self.client.post("/api/users/add", json=user or SAMPLE)
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_complete_crud_and_persistence(self):
        self.assertEqual(self.client.get("/api/users").get_json(), [])
        user = self.add_user()
        self.assertEqual({k: v for k, v in user.items() if k != "user_id"}, SAMPLE)
        user_id = user["user_id"]
        self.assertEqual(self.client.get(f"/api/users/{user_id}").get_json(), user)
        self.assertEqual(self.client.get("/api/users").get_json(), [user])
        # A fresh application instance reads the same persisted database.
        self.assertEqual(create_app().test_client().get("/api/users").get_json(), [user])
        updated = {**user, "name": "John Updated", "country": "Lebanon"}
        response = self.client.put("/api/users/update", json=updated)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), updated)
        self.assertEqual(self.client.get(f"/api/users/{user_id}").get_json(), updated)
        response = self.client.delete(f"/api/users/delete/{user_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "User deleted successfully"})
        self.assertEqual(self.client.get(f"/api/users/{user_id}").status_code, 404)
        self.assertEqual(self.client.get("/api/users").get_json(), [])

    def test_missing_users(self):
        for method, url, payload in [
            ("GET", "/api/users/999", None),
            ("PUT", "/api/users/update", {**SAMPLE, "user_id": 999}),
            ("DELETE", "/api/users/delete/999", None),
        ]:
            with self.subTest(method=method):
                response = self.client.open(url, method=method, json=payload)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.get_json(), {"error": "User not found"})

    def test_invalid_bodies_do_not_write(self):
        for payload in [{}, [], None, {**SAMPLE, "phone": 123}, {**SAMPLE, "name": "  "}]:
            with self.subTest(payload=payload):
                response = self.client.post("/api/users/add", data=json.dumps(payload),
                                            content_type="application/json")
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/users").get_json(), [])

    def test_invalid_update_ids(self):
        for user_id in [None, 0, -1, "1", True, 1.5]:
            with self.subTest(user_id=user_id):
                response = self.client.put("/api/users/update", json={**SAMPLE, "user_id": user_id})
                self.assertEqual(response.status_code, 400)

    def test_malformed_json_and_wrong_content_type(self):
        self.assertEqual(self.client.post("/api/users/add", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/users/add", data="name=John").status_code, 415)

    def test_parameterized_sql_and_multiple_users(self):
        malicious = {**SAMPLE, "name": "Robert'); DROP TABLE users;--"}
        first = self.add_user(malicious)
        second = self.add_user()
        self.assertNotEqual(first["user_id"], second["user_id"])
        self.assertEqual(self.client.get("/api/users").get_json(), [first, second])

    def test_cors_and_json_errors(self):
        response = self.client.options("/api/users/add", headers={
            "Origin": "https://example.com", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "https://example.com")
        response = self.client.post("/api/users", json=SAMPLE)
        self.assertEqual(response.status_code, 405)
        self.assertIn("GET", response.headers["Allow"])
        self.assertTrue(response.is_json)


if __name__ == "__main__":
    unittest.main(verbosity=2)
