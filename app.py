from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-unsafe")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-unsafe")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 604800))

jwt = JWTManager(app)
CORS(app, origins="*")

from services.register import registration_bp
app.register_blueprint(registration_bp)

from services.login import login_bp
app.register_blueprint(login_bp)

from services.main_router import main_router
app.register_blueprint(main_router)

def main():
    app.run(host='0.0.0.0', port=5070, debug=True)

if __name__ == "__main__":
    main()