from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

MONGO_URI = "mongodb://localhost:27017"  # Yerel MongoDB için

client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi('1'))
db = client["mydatabase"]  # Veritabanı adı
