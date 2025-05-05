from typing import Annotated, List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from starlette import status

from database import db
from models import Question
from routers.auth import get_current_user
from dotenv import load_dotenv
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import markdown
from bs4 import BeautifulSoup

router = APIRouter(
    prefix="/questions",
    tags=["Questions"],
)

class QuestionRequest(BaseModel):
    text: str
    result:str
    topic_id:str

@router.get("/", response_model=List[Question])
async def get_questions(user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = user.get("id")
    questions = []
    cursor = db["questions"].find({"user_id": user_id})
    async for question in cursor:
        question["id"] = str(question["_id"])
        questions.append(question)

    return questions

@router.get("/{id}")
async def get_question(id: str, user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = user.get("id")
    try:
        # ObjectId'ları düzgün bir şekilde işleyebilmek için doğrulama
        question_id = ObjectId(id)
        user_id = ObjectId(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    question = await db["questions"].find_one({"_id": question_id, "user_id": user_id})
    if question:
        question["_id"] = str(question["_id"])  # _id'yi string'e çevir
        question["user_id"] = str(question["user_id"])  # user_id'yi string'e çevir
        return question

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question not found")


@router.post("/create_question", status_code=status.HTTP_201_CREATED)
async def create_question(question: QuestionRequest, user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    topic = await db["topics"].find_one({"_id": ObjectId(question.topic_id)})
    if topic:
        topic["_id"] = str(topic["_id"])
        topic["user_id"] = str(topic["user_id"])

    created_question = Question(text=question.text,result=question.result, topic_id=topic["_id"])
    db["questions"].insert_one(created_question.model_dump(by_alias=True))

from fastapi import Body

@router.put("/update/{id}", status_code=status.HTTP_200_OK)
async def update_question(
    id: str,
    updated_data: QuestionRequest ,
    user: Annotated[dict, Depends(get_current_user)]
):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        question_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    question = await db["questions"].find_one({"_id": question_id})
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    update_data = {
        "text": updated_data.text,
        "result": updated_data.result,
        "topic_id": ObjectId(updated_data.topic_id),
    }

    await db["questions"].update_one({"_id": question_id}, {"$set": update_data})

    return {"message": "Question updated successfully"}


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(id: str, user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        question_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    delete_result = await db["questions"].delete_one({"_id": question_id})

    if delete_result.deleted_count == 1:
        return
    else:
        raise HTTPException(status_code=404, detail="Question not found")
