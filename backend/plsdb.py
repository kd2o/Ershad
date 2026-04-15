from pymongo import MongoClient

import certifi

from backend.config import Config


def list_database_names():
    client = MongoClient(Config.MONGO_URI, tlsCAFile=certifi.where())
    return client.list_database_names()


if __name__ == "__main__":
    print(list_database_names())
