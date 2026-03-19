from pydantic import BaseModel


class InvokeRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "default"


class InvokeResponse(BaseModel):
    content: str


class StreamChunk(BaseModel):
    type: str  # "token" | "done"
    content: str
