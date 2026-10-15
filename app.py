"""Run with .venv/Scripts/python.exe app.py, then use the Postman collection."""

import sqlite3

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from database import (
    USER_FIELDS, create_db_table, delete_user, get_user_by_id,
    get_users, insert_user, update_user,
)


def validate_user(require_id=False):
    if not request.is_json:
        return None, (jsonify(error="Content-Type must be application/json"), 415)
    user = request.get_json()
    if not isinstance(user, dict):
        return None, (jsonify(error="Request body must be a JSON object"), 400)
    invalid = [field for field in USER_FIELDS
               if not isinstance(user.get(field), str) or not user[field].strip()]
    if invalid:
        return None, (jsonify(error="Required nonempty string fields: " + ", ".join(invalid)), 400)
    if require_id and (type(user.get("user_id")) is not int or user["user_id"] <= 0):
        return None, (jsonify(error="user_id must be a positive integer"), 400)
    return user, None


def create_app():
    app = Flask(__name__)
    # The lab explicitly requests access from any origin.
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    create_db_table()

    @app.get("/api/users")
    def api_get_users():
        return jsonify(get_users())

    @app.get("/api/users/<int:user_id>")
    def api_get_user(user_id):
        user = get_user_by_id(user_id)
        if user is None:
            return jsonify(error="User not found"), 404
        return jsonify(user)

    @app.post("/api/users/add")
    def api_add_user():
        user, error = validate_user()
        if error is not None:
            return error
        return jsonify(insert_user(user)), 201

    @app.put("/api/users/update")
    def api_update_user():
        user, error = validate_user(require_id=True)
        if error is not None:
            return error
        updated = update_user(user)
        if updated is None:
            return jsonify(error="User not found"), 404
        return jsonify(updated)

    @app.delete("/api/users/delete/<int:user_id>")
    def api_delete_user(user_id):
        if not delete_user(user_id):
            return jsonify(error="User not found"), 404
        return jsonify(status="User deleted successfully")

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({"error": error.description})
        response.content_type = "application/json"
        return response

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        app.logger.exception("SQLite operation failed")
        return jsonify(error="Database operation failed"), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
