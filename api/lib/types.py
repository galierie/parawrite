from pydantic import BaseModel




class Query(BaseModel):
    text: str
    words: list[str]