from fastapi import FastAPI
from routers.auth import router as auth_router
from routers.topics import router as topics_router
from routers.questions import router as questions_router
from routers.creater import router as creater
app = FastAPI()


app.include_router(auth_router)
app.include_router(topics_router)
app.include_router(questions_router)
app.include_router(creater)
