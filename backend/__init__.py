# this file to create the app and the DB ;

from flask import *
from flask_pymongo import PyMongo
from flask_login import LoginManager
from urllib.parse import quote_plus


db = PyMongo()
login = LoginManager()
login.login_view = 'auth.login'

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    user = quote_plus("kd2oErshad")
    password = quote_plus("kd2o/Ershad")
    app.config["SECRET_KEY"] = 'idk...nononononononononono....iloveu'
    app.config['MONGO_URI'] = f'mongodb+srv://{user}:{password}@cluster0.vvolyr8.mongodb.net/?appName=Cluster0'

    db.init_app(app)
    login.init_app(app)

    # blueprints
    from backend.auth import auth as auth_bp
    from backend.routes import main as main_bp
    from backend.messages import messages as messages_bp
    from backend.requests import requests as requests_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(requests_bp)

    return app