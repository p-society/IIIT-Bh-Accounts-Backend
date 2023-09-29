from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pymongo import MongoClient
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime

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


@app.get("/")
async def root():
    return {"message": "Hello World"}

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
    return {"message": "Amount added to entities successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)