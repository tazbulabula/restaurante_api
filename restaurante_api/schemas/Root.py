from pydantic import BaseModel


class RootPublic(BaseModel):
    message: str
