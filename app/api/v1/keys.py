from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.key_manager import KeyManager

router = APIRouter()

class KeyProvisionRequest(BaseModel):
    key_id: str = Field(..., example="sk-gw-tenant-beta-002")
    organization_id: str = Field(..., example="org-analytics")
    rpm_limit: int = Field(default=120, ge=1)
    tpm_limit: int = Field(default=100000, ge=100)
    budget_limit_usd: float = Field(default=1000.0, ge=0.0)
    is_active: bool = Field(default=True)

@router.post("/keys", status_code=status.HTTP_201_CREATED)
async def provision_key(req: KeyProvisionRequest):
    await KeyManager.upsert_key(
        virtual_key=req.key_id,
        organization_id=req.organization_id,
        rpm_limit=req.rpm_limit,
        tpm_limit=req.tpm_limit,
        budget_limit_usd=req.budget_limit_usd,
        is_active=req.is_active
    )
    return {"message": "Key provisioned successfully", "key": req.dict()}

@router.get("/keys/{key_id}")
async def get_key_details(key_id: str):
    meta = await KeyManager.get_key_metadata(key_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Virtual key not found")
    return meta

@router.delete("/keys/{key_id}/revoke")
async def revoke_key(key_id: str):
    meta = await KeyManager.get_key_metadata(key_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Virtual key not found")
    await KeyManager.upsert_key(
        virtual_key=key_id,
        organization_id=meta["organization_id"],
        rpm_limit=meta["rpm_limit"],
        tpm_limit=meta["tpm_limit"],
        budget_limit_usd=meta["budget_limit_usd"],
        is_active=False
    )
    return {"message": f"Virtual key {key_id} has been revoked."}
