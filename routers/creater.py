from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from starlette import status


from routers.auth import get_current_user
from dotenv import load_dotenv
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import markdown
from bs4 import BeautifulSoup

from routers.questions import QuestionRequest
from routers.topics import create_topic, TopicRequest

router = APIRouter(
    prefix="/creater",
    tags=["Creater"],
)



def markdown_to_text(markdown_string):
    html = markdown.markdown(markdown_string)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    return text

@router.get("/get_question", status_code=status.HTTP_200_OK)
async def create_question_with_gemini(topic: str,user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    load_dotenv()
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro",google_api_key=os.environ.get('GOOGLE_API_KEY'))
    api_key = os.environ.get('GOOGLE_API_KEY')
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google API key not found.")

    response_question = llm.invoke(
        [
            HumanMessage(content="Sana bir konu vereceğim sen de bana bu konu ile ilgili çoktan seçmeli bir konu ver.Konum:"),
            HumanMessage(content=topic),
        ]
    )
    content_question= markdown_to_text(response_question.content)
    response_result=llm.invoke(
        [
            HumanMessage(content="Sana bir soru vericem onun cevabını ver.Soru:"),
            HumanMessage(content=content_question),
        ]
    )
    result_question= markdown_to_text(response_result.content)
    topic_request = TopicRequest(title=topic)
    topic_obj = await create_topic(topic_request, user)
    topic_id = str(topic_obj.id)
    question = QuestionRequest(text=content_question,result=result_question, topic_id=topic_id)
    return question

