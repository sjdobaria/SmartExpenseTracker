from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")  # put this in .env

DB_NAME = "SmartExpenseTracker"

_client = None

def get_mongo_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DB_NAME]

def get_transactions_collection():
    db = get_mongo_db()
    return db["Transactions"]
