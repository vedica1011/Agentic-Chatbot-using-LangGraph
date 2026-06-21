from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

def get_tenant(x_tenant_id: str = Header(...), db: Session = Depends(get_db)):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == x_tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid Tenant ID")
    return tenant
