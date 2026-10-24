from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pathlib import Path

router = APIRouter(prefix="/docs")


@router.get("/developer-note", response_class=PlainTextResponse)
def get_developer_note():
    content = Path("docs/DEVNOTE.md").read_text(encoding="utf-8")
    return content


@router.get("/privacy-policy", response_class=PlainTextResponse)
def get_privacy_policy():
    content = Path("docs/PRIVACY_POLICY.md").read_text(encoding="utf-8")
    return content


@router.get("/terms-of-service", response_class=PlainTextResponse)
def get_terms_of_service():
    content = Path("docs/TERMS_OF_SERVICE.md").read_text(encoding="utf-8")
    return content
