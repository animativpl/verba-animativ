from pydantic import BaseModel
from typing import Literal, Optional


class InputText(BaseModel):
    type: Literal["text"]
    text: str
    description: str


class InputNumber(BaseModel):
    type: Literal["number"]
    value: int
    description: str


class FileData(BaseModel):
    filename: str
    extension: str
    content: str
    doctype: Optional[str] = None
