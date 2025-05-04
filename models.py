from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Geçersiz ObjectId")
        return ObjectId(v)


class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    username: str=Field(min_length=3,max_length=64)
    email: str=Field(min_length=3,max_length=64)
    first_name: str=Field(min_length=3,max_length=64)
    last_name: str=Field(min_length=3,max_length=64)
    hashed_password: str=Field(min_length=6,max_length=20)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Topic(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    title: str
    user_id: PyObjectId

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Question(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    text: str
    topic_id: PyObjectId

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
