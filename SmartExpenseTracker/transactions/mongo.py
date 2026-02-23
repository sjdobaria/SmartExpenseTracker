from pymongo import MongoClient
import os
import certifi
from dotenv import load_dotenv

# Load .env from project root (3 levels up: transactions -> SmartExpenseTracker -> SmartExpenseTracker)
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_base, '.env'))

MONGO_URI = os.getenv("MONGO_URI")

DB_NAME = "SmartExpenseTracker"

_client = None

def get_mongo_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    return _client[DB_NAME]

def get_transactions_collection():
    db = get_mongo_db()
    return db["Transactions"]
