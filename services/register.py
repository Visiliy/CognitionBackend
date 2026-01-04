
from flask import Blueprint, request, jsonify
import sqlite3
import bcrypt
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "db/users_enter.db"

registration_bp = Blueprint("registration", __name__, url_prefix="/register")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@registration_bp.route("/", methods=["POST"])
def register():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Request body must be JSON"}), 400

        session_id = data.get("session_id")
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if not all([session_id, username, email, password]):
            return jsonify({"error": "session_id, username, email and password are required"}), 400

        conn = get_db_connection()

        existing_user = conn.execute("""
            SELECT id FROM users WHERE username = ? AND email = ?
        """, (username, email)).fetchone()

        if existing_user:
            conn.close()
            return jsonify({"status": "already_registered"}), 200

        user_with_same_username = conn.execute("""
            SELECT id FROM users WHERE username = ?
        """, (username,)).fetchone()

        if user_with_same_username:
            conn.close()
            return jsonify({"error": "username_already_taken"}), 409

        user_with_same_email = conn.execute("""
            SELECT id FROM users WHERE email = ?
        """, (email,)).fetchone()

        if user_with_same_email:
            conn.close()
            return jsonify({"error": "email_already_taken"}), 409

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_session_id = str(uuid.uuid4())

        conn.execute("""
            INSERT INTO users (username, email, password_hash, session_id)
            VALUES (?, ?, ?, ?)
        """, (username, email, hashed_pw, new_session_id))

        conn.commit()
        conn.close()

        return jsonify({
            "status": "registered",
            "session_id": new_session_id,
            "username": username,
            "email": email
        }), 201

    except Exception as e:
        logger.exception("Registration error")
        return jsonify({"error": "Internal server error"}), 500