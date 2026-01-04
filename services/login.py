from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import sqlite3
import bcrypt
import os
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "db/users_enter.db"

login_bp = Blueprint("login", __name__, url_prefix="/login")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                session_id TEXT
            )
        """)

init_db()

@login_bp.route("/", methods=["POST"])
@login_bp.route("", methods=["POST"])
def login_function():
    try:
        data = request.get_json()
        if data is None:
            data = request.form.to_dict()
            if not data:
                return jsonify({"error": "Request body must be JSON or form data"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        conn = get_db_connection()
        user = conn.execute("""
            SELECT id, username, email, password_hash, session_id 
            FROM users 
            WHERE username = ?
        """, (username,)).fetchone()
        conn.close()

        if not user:
            return jsonify({"error": "user_not_found"}), 404

        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({"error": "incorrect_password"}), 401

        session_id = user['session_id'] or str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute(
            "UPDATE users SET session_id = ? WHERE id = ?",
            (session_id, user['id'])
        )
        conn.commit()
        conn.close()

        access_token = create_access_token(identity=user['id'], fresh=True)
        refresh_token = create_refresh_token(identity=user['id'])

        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email']
            }
        }), 200

    except Exception as e:
        logger.exception("Login error")
        return jsonify({"error": "Internal server error"}), 500

@login_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    conn = get_db_connection()
    user = conn.execute("SELECT session_id FROM users WHERE id = ?", (current_user_id,)).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    new_access_token = create_access_token(identity=current_user_id)
    return jsonify({
        "access_token": new_access_token,
        "session_id": user['session_id']
    }), 200

@login_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, username, email, session_id FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user['id'],
        "username": user['username'],
        "email": user['email'],
        "session_id": user['session_id']
    }), 200