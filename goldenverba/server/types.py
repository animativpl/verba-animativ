from typing import Optional

from pydantic import BaseModel
from goldenverba.components.types import FileData


class QueryPayload(BaseModel):
    query: str
    doc_label: str


class ConversationItem(BaseModel):
    type: str
    content: str


class GeneratePayload(BaseModel):
    query: str
    context: str
    conversation: list[ConversationItem]


class SearchQueryPayload(BaseModel):
    query: str
    doc_type: Optional[str] = None
    page: Optional[int] = None
    pageSize: Optional[int] = None


class GetDocumentPayload(BaseModel):
    document_id: str


class ResetPayload(BaseModel):
    resetMode: str


class LoadPayload(BaseModel):
    reader: str
    chunker: str
    embedder: str
    fileBytes: list[str]
    fileNames: list[str]
    filePath: str
    document_type: str
    chunkUnits: int
    chunkOverlap: int


class ImportPayload(BaseModel):
    data: list[FileData]
    textValues: Optional[list[str]] = None
    config: Optional[dict] = None


class ConfigPayload(BaseModel):
    config: dict


class GetComponentPayload(BaseModel):
    component: str


class SetComponentPayload(BaseModel):
    component: str
    selected_component: str


class DeleteDocumentPayload(BaseModel):
    document_id: str


class DeleteDocumentNamePayload(BaseModel):
    document_name: str
