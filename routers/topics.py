from typing import List, Annotated
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette import status

from database import db
from models import Topic
from routers.auth import get_current_user

router = APIRouter(
    prefix="/topics",
    tags=["Topics"],
)

class TopicRequest(BaseModel):
    title: str

@router.get("/", response_model=List[Topic])
async def get_topics(user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = user.get("id")
    topics = []
    cursor = db["topics"].find({"user_id": user_id})
    async for topic in cursor:
        topic["id"] = str(topic["_id"])
        topics.append(topic)

    return topics

@router.get("/{id}")
async def get_topic(id: str, user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = user.get("id")
    try:
        # ObjectId'ları düzgün bir şekilde işleyebilmek için doğrulama
        topic_id = ObjectId(id)
        user_id = ObjectId(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    topic = await db["topics"].find_one({"_id": topic_id, "user_id": user_id})
    if topic:
        topic["_id"] = str(topic["_id"])  # _id'yi string'e çevir
        topic["user_id"] = str(topic["user_id"])  # user_id'yi string'e çevir
        return topic

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")


@router.post("/create_topic", status_code=status.HTTP_201_CREATED)
async def create_topic(topic: TopicRequest, user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = user.get("id")
    created_topic = Topic(title=topic.title, user_id=user_id)
    db["topics"].insert_one(created_topic.model_dump(by_alias=True))
    return created_topic