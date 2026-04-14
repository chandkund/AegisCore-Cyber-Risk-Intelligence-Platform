from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AdminDep, ReaderDep
from app.db.deps import get_db
from app.schemas.policy import PolicyRuleCreate, PolicyRuleOut, PolicyViolation
from app.services.policy_service import PolicyService

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("/rules", response_model=PolicyRuleOut)
def create_rule(principal: AdminDep, body: PolicyRuleCreate, db: Session = Depends(get_db)):
    return PolicyService(db, tenant_id=principal.tenant_id).create_rule(body)


@router.get("/rules", response_model=list[PolicyRuleOut])
def list_rules(principal: ReaderDep, db: Session = Depends(get_db)):
    return PolicyService(db, tenant_id=principal.tenant_id).list_rules()


@router.get("/evaluate", response_model=list[PolicyViolation])
def evaluate_policy(principal: ReaderDep, db: Session = Depends(get_db)):
    return PolicyService(db, tenant_id=principal.tenant_id).evaluate()
