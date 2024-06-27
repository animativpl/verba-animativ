import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from dotenv import load_dotenv

load_dotenv()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def check_api_key(api_key_header: str = Security(api_key_header)):
    api_key = os.environ.get("X_API_KEY", "")
    if api_key != "" and api_key != api_key_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
