from fastapi import APIRouter

router = APIRouter(
    prefix="/questions",
    tags=["Questions"],
)

