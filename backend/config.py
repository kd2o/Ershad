import os
from urllib.parse import quote_plus


def _build_default_mongo_uri():
    mongo_user = quote_plus(os.getenv("MONGO_USERNAME", "kd2oErshad"))
    mongo_password = quote_plus(os.getenv("MONGO_PASSWORD", "kd2o/Ershad"))
    return (
        "mongodb+srv://"
        f"{mongo_user}:{mongo_password}"
        "@cluster0.vvolyr8.mongodb.net/guidance_app?retryWrites=true&w=majority"
    )


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    MONGO_URI = os.getenv("MONGO_URI", _build_default_mongo_uri())
