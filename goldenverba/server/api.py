from fastapi import FastAPI, WebSocket, status, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import os
from pathlib import Path

from dotenv import load_dotenv
from starlette.websockets import WebSocketDisconnect
from wasabi import msg  # type: ignore[import]
import time

from goldenverba import verba_manager
from goldenverba.server.auth import check_api_key
from goldenverba.server.types import (
    QueryPayload,
    GeneratePayload,
    GetDocumentPayload,
    ImportPayload, DeleteDocumentPayload, DeleteDocumentNamePayload,
)
from goldenverba.server.util import setup_managers

load_dotenv()

production_key = os.environ.get("VERBA_PRODUCTION", "")
tag = os.environ.get("VERBA_GOOGLE_TAG", "")
if production_key == "True":
    msg.info("API runs in Production Mode")
    production = True
else:
    production = False

manager = verba_manager.VerbaManager()
setup_managers(manager)

# FastAPI App
app = FastAPI()
http_guarded_router = APIRouter(dependencies=[Depends(check_api_key)])
http_unguarded_router = APIRouter()
ws_router = APIRouter()

origins = [
    "http://localhost:3000",
    "https://verba-golden-ragtriever.onrender.com",
    "http://localhost:8000",
]

# Add middleware for handling Cross Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.environ.get("ENABLE_FRONTEND", "false") != "false":
    BASE_DIR = Path(__file__).resolve().parent

    # Serve the assets (JS, CSS, images, etc.)
    app.mount(
        "/static/_next",
        StaticFiles(directory=BASE_DIR / "frontend/out/_next"),
        name="next-assets",
    )

    # Serve the main page and other static files
    app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend/out"), name="app")


    @http_guarded_router.get("/")
    @http_guarded_router.head("/")
    async def serve_frontend():
        return FileResponse(os.path.join(BASE_DIR, "frontend/out/index.html"))


# HEAD

# Health check endpoint
@http_unguarded_router.head("/api/health")
async def health_check():
    try:
        if manager.client.is_ready():
            return JSONResponse(
                content={"message": "Alive!", "production": production, "gtag": tag}
            )
        else:
            return JSONResponse(
                content={
                    "message": "Database not ready!",
                    "production": production,
                    "gtag": tag,
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
    except Exception as e:
        msg.fail(f"Healthcheck failed with {str(e)}")
        return JSONResponse(
            content={
                "message": f"Healthcheck failed with {str(e)}",
                "production": production,
                "gtag": tag,
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# GET

# Retrieve all documents
@http_guarded_router.get("/api/documents")
async def get_all_documents():
    try:
        docs = manager.retrieve_all_documents()
        return JSONResponse(
            content={
                "documents": list(docs)
            }
        )
    except Exception as e:
        msg.fail(f"All document types retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "documents": [],
            }
        )


# Retrieve specific document based on UUID
@http_guarded_router.get("/api/document")
async def get_document(payload: GetDocumentPayload):
    msg.info(f"Document ID received: {payload.document_id}")

    try:
        document = manager.retrieve_document(payload.document_id)
        document_properties = document.get("properties", {})
        document_obj = {
            "class": document.get("class", "No Class"),
            "id": document.get("id", payload.document_id),
            "chunks": document_properties.get("chunk_count", 0),
            "link": document_properties.get("doc_link", ""),
            "name": document_properties.get("doc_name", "No name"),
            "type": document_properties.get("doc_type", "No type"),
            "text": document_properties.get("text", "No text"),
            "timestamp": document_properties.get("timestamp", ""),
        }

        msg.good(f"Succesfully retrieved document: {payload.document_id}")
        return JSONResponse(
            content={
                "error": "",
                "document": document_obj,
            }
        )
    except Exception as e:
        msg.fail(f"Document retrieval failed: {str(e)}")
        return JSONResponse(
            content={
                "error": str(e),
                "document": None,
            }
        )


# Retrieve auto complete suggestions based on user input
@http_guarded_router.get("/api/suggestions", include_in_schema=False)
async def suggestions(payload: QueryPayload):
    try:
        suggestions = manager.get_suggestions(payload.query)

        return JSONResponse(
            content={
                "suggestions": suggestions,
            }
        )
    except Exception:
        return JSONResponse(
            content={
                "suggestions": [],
            }
        )


# POST

# Import documents
@http_guarded_router.post("/api/import-files")
async def import_files(payload: ImportPayload):
    response = []

    try:
        documents, _ = manager.import_data(
            payload.data, payload.textValues, []
        )

        for document in documents:
            saved_docs = manager.retrieve_all_documents()
            saved_docs = list(map(lambda doc: manager.retrieve_document(doc["_additional"]["id"]), saved_docs))
            for saved in saved_docs:
                document_properties = saved.get("properties", {})
                obj = {
                    "class": saved.get("class", "No Class"),
                    "id": saved.get("id", "No Id"),
                    "chunks": document_properties.get("chunk_count", 0),
                    "link": document_properties.get("doc_link", ""),
                    "name": document_properties.get("doc_name", "No name"),
                    "type": document_properties.get("doc_type", "No type"),
                    "text": document_properties.get("text", "No text"),
                    "timestamp": document_properties.get("timestamp", ""),
                }
                if obj["name"] == document.name and obj["type"] == document.type and obj["text"] == document.text:
                    response.append(obj)

        return JSONResponse(
            content={
                "documents": response,
            }
        )

    except Exception as _:
        return JSONResponse(
            content={
                "documents": response,
            }
        )


# Receive query and return chunks and query answer
@http_guarded_router.post("/api/query")
async def query(payload: QueryPayload):
    msg.good(f"Received query: {payload.query} {payload.doc_label}")
    start_time = time.time()  # Start timing
    try:
        chunks, context = manager.retrieve_chunks([payload])

        retrieved_chunks = [
            {
                "text": chunk.text,
                "doc_name": chunk.doc_name,
                "chunk_id": chunk.chunk_id,
                "doc_uuid": chunk.doc_uuid,
                "doc_type": chunk.doc_type,
                "score": chunk.score,
            }
            for chunk in chunks
        ]

        elapsed_time = round(time.time() - start_time, 2)  # Calculate elapsed time
        msg.good(f"Succesfully processed query: {payload.query} {payload.doc_label} in {elapsed_time}s")

        if len(chunks) == 0:
            return JSONResponse(
                content={
                    "chunks": [],
                    "took": 0,
                    "context": "",
                    "error": "No Chunks Available",
                }
            )

        return JSONResponse(
            content={
                "error": "",
                "chunks": retrieved_chunks,
                "context": context,
                "took": elapsed_time,
            }
        )

    except Exception as e:
        msg.warn(f"Query failed: {str(e)}")
        return JSONResponse(
            content={
                "chunks": [],
                "took": 0,
                "context": "",
                "error": f"Something went wrong: {str(e)}",
            }
        )


@http_guarded_router.post('/api/generate-answer')
async def generate_answer(payload: GeneratePayload):
    msg.good(f"Received generate answer: {payload.query}")
    start_time = time.time()
    try:
        answer = await manager.generate_answer([payload.query], [payload.context], payload.conversation)

        elapsed_time = round(time.time() - start_time, 2)
        msg.good(f"Succesfully generaetd answer: {payload.query} in {elapsed_time}s")

        return JSONResponse(content=answer)
    except Exception as e:
        msg.warn(f"Generate answer failed: {str(e)}")
        return JSONResponse(
            content={
                "message": e,
                "finish_reason": "stop",
            }
        )


# DELETE


# Delete specific document based on UUID
@http_guarded_router.delete("/api/document")
async def delete_document(payload: DeleteDocumentPayload):
    if production:
        msg.warn("Can't delete documents when in Production Mode")
        return JSONResponse(status_code=200, content={})

    msg.info(f"Document ID received: {payload.document_id}")

    manager.delete_document_by_id(payload.document_id)
    return JSONResponse(content={})


# Delete specific document based on name
@http_guarded_router.delete("/api/document-name")
async def delete_document_by_name(payload: DeleteDocumentNamePayload):
    if production:
        msg.warn("Can't delete documents when in Production Mode")
        return JSONResponse(status_code=200, content={})

    msg.info(f"Document Name received: {payload.document_name}")

    manager.delete_document_by_name(payload.document_name)
    return JSONResponse(content={})


# Delete all documents
@http_guarded_router.delete("/api/documents")
async def delete_all_documents():
    if production:
        msg.warn("Can't delete documents when in Production Mode")
        return JSONResponse(status_code=200, content={})

    manager.delete_documents()
    return JSONResponse(content={})


# WEBSOCKETS

@ws_router.websocket("/ws/generate_stream")
async def websocket_generate_stream(websocket: WebSocket):
    await websocket.accept()
    header_key = websocket.headers.get("X-API-Key", "")
    api_key = os.environ.get("X_API_KEY", "")

    if api_key != "" and header_key != api_key:
        msg.fail("WebSocket Error: Invalid API Key")
        await websocket.send_json({"detail": "Invalid API Key"})
        await websocket.close()
    else:
        while True:  # Start a loop to keep the connection alive.
            try:
                data = await websocket.receive_text()
                # Parse and validate the JSON string using Pydantic model
                msg.info(data)
                payload = GeneratePayload.model_validate_json(data)
                msg.good(f"Received generate stream call for {payload.query}")
                full_text = ""
                async for chunk in manager.generate_stream_answer(
                        [payload.query], [payload.context], payload.conversation
                ):
                    full_text += chunk["message"]
                    if chunk["finish_reason"] == "stop":
                        chunk["full_text"] = full_text
                    await websocket.send_json(chunk)

            except WebSocketDisconnect:
                msg.warn("WebSocket connection closed by client.")
                break  # Break out of the loop when the client disconnects

            except Exception as e:
                msg.fail(f"WebSocket Error: {str(e)}")
                await websocket.send_json(
                    {"message": e, "finish_reason": "stop", "full_text": str(e)}
                )
            msg.good("Succesfully streamed answer")


app.include_router(http_guarded_router)
app.include_router(http_unguarded_router)
app.include_router(ws_router)
