from typing import List, Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from database import db
from models import Topic
from routers.auth import get_current_user

router = APIRouter(
    prefix="/topics",
    tags=["Topics"],
)

@router.get("/", response_model=List[Topic])
def get_topics(user:Annotated[dict,get_current_user]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = user.get("id")  # veya "_id" ise ona göre

    todos = []
    cursor = db["topics"].find({"user_id": ObjectId(user_id)})
    async for todo in cursor:
        todo["id"] = str(todo["id"])  # ObjectId JSON’a çevrilsin diye
        todos.append(todo)

    return todos

@router.get("/{id}", response_model=Topic)
async def get_topic(id:str,user:Annotated[dict,get_current_user]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user_id = user.get("id")
    topic = await db["todos"].find_one({
        "id": id,
        "user_id": user_id
    })

    if topic:
        topic["_id"] = str(topic["_id"])
        return topic

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Topic not found"
    )
