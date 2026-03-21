from pymongo import MongoClient

uri = "mongodb+srv://kd2oErshad:kdo3liloverayan@cluster0.vvolyr8.mongodb.net/guidance_app?retryWrites=true&w=majority"
client = MongoClient(uri)

print(client.list_database_names())