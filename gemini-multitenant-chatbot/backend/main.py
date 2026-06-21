from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

import models
from database import engine, get_db
import dependencies
import llm_service

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gemini Multi-Tenant Chatbot")

class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    response: str

class ChatHistoryResponse(BaseModel):
    role: str
    content: str
    timestamp: str

@app.post("/chat", response_model=MessageResponse)
def chat(request: MessageRequest, tenant: models.Tenant = Depends(dependencies.get_tenant), db: Session = Depends(get_db)):
    # Fetch previous messages
    history = db.query(models.ChatMessage).filter(models.ChatMessage.tenant_id == tenant.id).order_by(models.ChatMessage.timestamp).all()
    
    # Save user message
    user_msg = models.ChatMessage(tenant_id=tenant.id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()
    
    try:
        response_text = llm_service.generate_response(tenant.system_prompt, history, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
        
    # Save model response
    model_msg = models.ChatMessage(tenant_id=tenant.id, role="model", content=response_text)
    db.add(model_msg)
    db.commit()
    
    return MessageResponse(response=response_text)

@app.get("/history", response_model=List[ChatHistoryResponse])
def get_history(tenant: models.Tenant = Depends(dependencies.get_tenant), db: Session = Depends(get_db)):
    history = db.query(models.ChatMessage).filter(models.ChatMessage.tenant_id == tenant.id).order_by(models.ChatMessage.timestamp).all()
    return [{"role": msg.role, "content": msg.content, "timestamp": str(msg.timestamp)} for msg in history]

# Admin endpoints for testing and tenant management
class TenantCreate(BaseModel):
    id: str
    name: str
    system_prompt: Optional[str] = None

@app.post("/admin/tenants")
def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant.id).first()
    if db_tenant:
        raise HTTPException(status_code=400, detail="Tenant ID already exists")
    new_tenant = models.Tenant(id=tenant.id, name=tenant.name, system_prompt=tenant.system_prompt)
    db.add(new_tenant)
    db.commit()
    return {"status": "success", "tenant_id": new_tenant.id}
