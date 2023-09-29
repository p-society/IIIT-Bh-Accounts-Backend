from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from typing import Optional

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient("mongodb+srv://iiitbhubaneswar:iiitbhubaneswar@clusteriiit-bh.49fkvnc.mongodb.net/")
db = client["accounts"]
transactions = db["transactions"]
users = db["users"]

class Entity(BaseModel):
    name: str
    weightage: float
    current_balance: float

class Transaction(BaseModel):
    sender: str
    receiver: str
    amount: float
    date: str
    time: str

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/entities")
async def get_entities():
    entities = [entity for entity in users.find()]
    for entity in entities:
        entity["_id"] = str(entity["_id"])
    return {"entities": entities}

@app.post("/entities/add")
async def add_entity(entity: Entity):
    result = users.insert_one(entity.dict())
    return {"id": str(result.inserted_id)}

@app.put("/entities/edit/{entity_id}")
async def edit_entity(entity_id: str, entity: Entity):
    object_id = ObjectId(entity_id)
    result = users.update_one({"_id": object_id}, {"$set": entity.dict()})
    return {"message": f"Entity with ID {entity_id} updated successfully"}

@app.get("/entities/sum")
async def get_entities_sum():
    result = users.aggregate([{"$group": {"_id": None, "total": {"$sum": "$current_balance"}}}])
    return {"sum": result.next()["total"]}

@app.post("/entities/add_amount")
async def add_amount_to_entities(amount: float):
    weightage_sum = users.aggregate([{"$group": {"_id": None, "total": {"$sum": "$weightage"}}}]).next()["total"]
    amount_per_weight = amount / weightage_sum
    for entity in users.find():
        current_balance = entity["current_balance"]
        weightage = entity["weightage"]
        new_balance = current_balance + (amount_per_weight * weightage)
        users.update_one({"_id": entity["_id"]}, {"$set": {"current_balance": new_balance}})
    # Record the transaction from admin to all entities
    current_datetime = datetime.now()
    transaction = Transaction(sender="Admin", receiver="All Entities", amount=amount,
                              date=current_datetime.strftime("%Y-%m-%d"), time=current_datetime.strftime("%H:%M:%S"))
    transactions.insert_one(transaction.dict())
    return {"message": "Amount added to entities successfully"}

@app.get("/entities/names")
async def get_entities_names():
    # Get the names of all entities in the collection
    names = [entity["name"] for entity in users.find()]
    # Return the names as a JSON object
    return {"names": names}

@app.post("/transaction")
async def transfer_money(transaction: Transaction):
    sender_entity = users.find_one({"name": transaction.sender})
    receiver_entity = users.find_one({"name": transaction.receiver})
    if transaction.sender == transaction.receiver:
        return {"message": "Sender and receiver cannot be same"}
    elif sender_entity["current_balance"] < transaction.amount:
        return {"message": "Sender does not have enough balance to transfer the amount"}
    sender_new_balance = sender_entity["current_balance"] - transaction.amount
    receiver_new_balance = receiver_entity["current_balance"] + transaction.amount
    users.update_one({"_id": sender_entity["_id"]}, {"$set": {"current_balance": sender_new_balance}})
    users.update_one({"_id": receiver_entity["_id"]}, {"$set": {"current_balance": receiver_new_balance}})
    current_datetime = datetime.now()
    transaction_dict = transaction.dict()
    transaction_dict["date"] = current_datetime.strftime("%Y-%m-%d")
    transaction_dict["time"] = current_datetime.strftime("%H:%M:%S")
    transactions.insert_one(transaction_dict)
    return {"message": "Transaction recorded successfully"}

@app.get("/transaction/filter")
async def filter_transactions(sender: Optional[str] = None, receiver: Optional[str] = None):
    filter_dict = {}
    if sender:
        filter_dict["sender"] = sender
    if receiver:
        filter_dict["receiver"] = receiver
    transactions_list = [transaction for transaction in transactions.find(filter_dict)]
    for transaction in transactions_list:
        transaction["_id"] = str(transaction["_id"])
    transactions_with_id = [Transaction(**transaction) for transaction in transactions_list]
    return {"transactions": transactions_with_id}
