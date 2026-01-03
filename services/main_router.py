import os
import sqlite3
from flask import *
from werkzeug.utils import secure_filename
import yadisk

main_router = Blueprint("api", __name__, url_prefix="/main_router")

TOKEN = "y0__xC9xu6BBhjc1jwgqL7o8RWGkcNghbCfof-5T4IJe74HTprUig"
main_path = "user_files"
db_path = "db/users.db"


def get_yadisk_client():
    return yadisk.Client(token=TOKEN)


def init_db(path):
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SessionsID (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                is_register INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL DEFAULT (datetime('now', '+1 day'))
            )
        """)


def upsert_session(path, session_id, is_register=0):
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO SessionsID (session_id, is_register, expires_at)
            VALUES (?, ?, datetime('now', '+30 days'))
            ON CONFLICT(session_id) DO UPDATE SET
                is_register = CASE WHEN is_register = 0 THEN excluded.is_register ELSE is_register END,
                expires_at = CASE WHEN is_register = 0 THEN datetime('now', '+30 days') ELSE expires_at END
        """, (session_id, is_register))


@main_router.route("/", methods=["POST"])
def main_router_functions():
    try:
        if not os.path.isfile(db_path):
            init_db(db_path)

        content = request.form
        files = request.files

        text = content.get("text", "")
        add_files_to_storage = content.get("add_files_to_storage", "false")
        is_registered = content.get("is_registered", "false") == "true"
        session_id = content.get("session_id")

        if not session_id:
            return jsonify([{"Message": "session_id required"}]), 400

        client = get_yadisk_client()
        if not client.exists(main_path):
            client.mkdir(main_path)

        session_dir = f"{main_path}/{session_id}"
        storage_path = f"{session_dir}/storage"
        private_storage_path = f"{session_dir}/private_storage"

        client.makedirs(session_dir, exist_ok=True)
        client.makedirs(storage_path, exist_ok=True)
        client.makedirs(private_storage_path, exist_ok=True)

        files_list = files.getlist("files")

        if add_files_to_storage == "false" and files_list:
            try:
                items = client.listdir(private_storage_path)
                for item in items:
                    if item.get("type") == "file":
                        try:
                            client.remove(item["path"])
                        except Exception as e:
                            print(f"Warn: failed to remove {item.get('path')}: {e}")
            except yadisk.exceptions.PathNotFoundError:
                pass

        for file in files_list:
            filename = secure_filename(file.filename)
            if not filename:
                continue

            temp_path = f"/tmp/{filename}"
            try:
                file.save(temp_path)
                remote_path = f"{storage_path}/{filename}" if add_files_to_storage == "true" else f"{private_storage_path}/{filename}"
                client.upload(temp_path, remote_path, overwrite=True)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        upsert_session(db_path, session_id, 1 if is_registered else 0)

        return jsonify([{"SearchAnswer": "Ответ успешно завершён"}]), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify([{"Message": "Global server error", "error": str(e)}]), 500


@main_router.route("/delete_session", methods=["POST"])
def delete_session():
    try:
        session_id = request.form.get("session_id")
        if not session_id:
            return jsonify([{"Message": "session_id required"}]), 400

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM SessionsID WHERE session_id = ?", (session_id,))

        return jsonify([{"Message": "Сессия успешно удалена"}]), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify([{"Message": "Global server error"}]), 500


def _list_files(session_id, subdir):
    try:
        client = get_yadisk_client()
        path = f"{main_path}/{session_id}/{subdir}"
        items = client.listdir(path)
        return [item["name"] for item in items if item.get("type") == "file"]
    except yadisk.exceptions.PathNotFoundError:
        return []
    except Exception as e:
        print(f"Error listing {path}:", e)
        return []


@main_router.route("/upload_private_files", methods=["GET"])
def upload_private_files():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify([{"Message": "session_id required"}]), 400
    files = _list_files(session_id, "private_storage")
    return jsonify([{"FilesNames": files}]), 200


@main_router.route("/upload_storage_files", methods=["GET"])
def upload_storage_files():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify([{"Message": "session_id required"}]), 400
    files = _list_files(session_id, "storage")
    return jsonify([{"FilesNames": files}]), 200