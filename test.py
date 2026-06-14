from pymongo import MongoClient
import os

uri = os.getenv("MONGO_URI")

try:
    client = MongoClient(uri)
    print(client.admin.command("ping"))
    print("Connected!")
except Exception as e:
    print("Error:", e)