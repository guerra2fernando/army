"""
Knowledge Base API Routes
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.utils.auth import get_current_user
from app.rag.knowledge_base import get_knowledge_base
from app.models.user import User
from app.rag.ingestion import KnowledgeSource

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


class DocumentCreate(BaseModel):
    """Request to add a document."""
    content: str
    source: str
    title: str
    tags: Optional[List[str]] = None


class CVCreate(BaseModel):
    """Request to add CV."""
    content: str


class TradingRulesCreate(BaseModel):
    """Request to add trading rules."""
    content: str


class SearchRequest(BaseModel):
    """Search request."""
    query: str
    limit: int = 5
    source: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/documents")
async def add_document(
    doc: DocumentCreate,
    current_user: User = Depends(get_current_user)
):
    """Add a document to the knowledge base."""
    kb = get_knowledge_base()
    
    result = await kb.add_document(
        content=doc.content,
        source=doc.source,
        title=doc.title,
        tags=doc.tags,
        user_id=current_user.user_id
    )
    
    return result


@router.post("/cv")
async def add_cv(
    data: CVCreate,
    current_user: User = Depends(get_current_user)
):
    """Upload CV to knowledge base."""
    kb = get_knowledge_base()
    return await kb.add_cv(data.content, current_user.user_id)


@router.post("/trading-rules")
async def add_trading_rules(
    data: TradingRulesCreate,
    current_user: User = Depends(get_current_user)
):
    """Upload trading rules to knowledge base."""
    kb = get_knowledge_base()
    return await kb.add_trading_rules(data.content, current_user.user_id)


@router.post("/search")
async def search_knowledge(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """Search the knowledge base."""
    kb = get_knowledge_base()
    
    results = await kb.search(
        query=request.query,
        limit=request.limit,
        source=request.source,
        tags=request.tags,
        user_id=current_user.user_id
    )
    
    return {"results": results}


@router.get("/documents")
async def list_documents(
    source: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List all documents in the knowledge base."""
    kb = get_knowledge_base()
    
    documents = await kb.list_documents(
        user_id=current_user.user_id,
        source=source
    )
    
    return {"documents": documents}


@router.delete("/documents/{title}")
async def delete_document(
    title: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a document by title."""
    kb = get_knowledge_base()
    
    deleted = await kb.remove_document(
        title=title,
        user_id=current_user.user_id
    )
    
    return {"deleted_chunks": deleted}


@router.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user)):
    """Get knowledge base statistics."""
    kb = get_knowledge_base()
    return await kb.get_stats(current_user.user_id)


@router.get("/sources")
async def list_sources(current_user: User = Depends(get_current_user)):
    """List available source types."""
    return {
        "sources": [
            {"value": KnowledgeSource.CV, "label": "CV / Resume"},
            {"value": KnowledgeSource.TRADING_RULES, "label": "Trading Rules"},
            {"value": KnowledgeSource.PROJECT_DOC, "label": "Project Documentation"},
            {"value": KnowledgeSource.USER_PREFERENCE, "label": "User Preferences"},
            {"value": KnowledgeSource.JOB_DESCRIPTION, "label": "Job Descriptions"},
            {"value": KnowledgeSource.COMPANY_INFO, "label": "Company Information"}
        ]
    }

