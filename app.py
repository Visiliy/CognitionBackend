from flask import *
from flask_cors import CORS
from services.main_router import main_router


app = Flask(__name__)
app.register_blueprint(main_router)
CORS(app, origins="*")

def main():
    app.run(host='0.0.0.0', port=5070, debug=True)

if __name__ == "__main__":
    main()