"""Settings endpoints: WB accounts, API key management."""

import json
import logging
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.security import decrypt_api_key, encrypt_api_key
from app.models.product import WBAccount
from app.models.user import User
from app.schemas.wb_account import (
    WBAccountCreate,
    WBAccountList,
    WBAccountResponse,
    WBKeyValidationResult,
)

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)

WB_API_ENDPOINTS = {
    # Product cards
    "content": ("POST", "https://content-api.wildberries.ru/content/v2/get/cards/list", {"settings": {"cursor": {"limit": 1}, "filter": {"withPhoto": -1}}}),
    # Prices & discounts
    "prices": ("GET", "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter?limit=1", None),
    # Statistics (orders, sales, incomes)
    "statistics": ("GET", "https://statistics-api.wildberries.ru/api/v1/supplier/orders?dateFrom=2025-01-01", None),
    # Seller analytics (v2 nm-report/detail removed; use downloads list)
    "analytics": ("GET", "https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads", None),
    # Marketplace (FBO/FBS new orders — no required params)
    "marketplace": ("GET", "https://marketplace-api.wildberries.ru/api/v3/orders/new", None),
    # Advertising / promotions
    "advert": ("GET", "https://advert-api.wildberries.ru/adv/v1/promotion/count", None),
    # Reviews / feedbacks
    "feedbacks": ("GET", "https://feedbacks-api.wildberries.ru/api/v1/feedbacks/count", None),
    # Questions (same domain as feedbacks)
    "questions": ("GET", "https://feedbacks-api.wildberries.ru/api/v1/questions/count-unanswered", None),
    # Recommendations (domain: recommend-api; requires POST)
    "recommendations": ("POST", "https://recommend-api.wildberries.ru/api/v1/list", []),
    # Returns (endpoint: /claims, not /returns)
    "returns": ("GET", "https://returns-api.wildberries.ru/api/v1/claims", None),
    # Common (tariffs — date param required, set dynamically)
    "common": ("GET", None, None),  # URL built dynamically in _check_wb_permissions
}


def _mask_key(key: str) -> str:
    """Show only last 8 chars of API key."""
    if len(key) <= 12:
        return "***" + key[-4:]
    return "***" + key[-8:]


async def _check_wb_permissions(api_key: str) -> list[str]:
    """Test WB API key against different endpoints to determine permissions.

    Only 200/201 counts as confirmed access. Everything else (401, 403, 400,
    429, 5xx, timeouts) means no confirmed access for that section.
    """
    permissions = []
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    async with httpx.AsyncClient(timeout=10.0) as client:
        for perm_name, (method, url, body) in WB_API_ENDPOINTS.items():
            # Build dynamic URLs
            if perm_name == "common":
                url = f"https://common-api.wildberries.ru/api/v1/tariffs/box?date={today}"
            if url is None:
                continue
            try:
                kwargs = {"headers": {"Authorization": api_key}}
                if body is not None and method == "POST":
                    kwargs["json"] = body
                resp = await client.request(method, url, **kwargs)
                if resp.status_code in (200, 201):
                    permissions.append(perm_name)
                else:
                    logger.debug(
                        "WB permission %s: HTTP %s", perm_name, resp.status_code
                    )
            except httpx.TimeoutException:
                logger.debug("WB permission %s: timeout", perm_name)
            except Exception as e:
                logger.debug("WB permission %s: error %s", perm_name, e)
    return permissions


@router.post("/wb-accounts/validate-key", response_model=WBKeyValidationResult)
async def validate_wb_key(
    data: WBAccountCreate,
    _current_user: User = Depends(get_current_user),
):
    """Validate WB API key and check available permissions."""
    try:
        permissions = await _check_wb_permissions(data.api_key)
    except Exception as e:
        logger.error("WB key validation failed: %s", e)
        return WBKeyValidationResult(valid=False, permissions=[], error="Connection error")

    if not permissions:
        return WBKeyValidationResult(
            valid=False,
            permissions=[],
            error="API ключ невалиден или не имеет прав доступа",
        )

    return WBKeyValidationResult(valid=True, permissions=permissions)


@router.post("/wb-accounts", response_model=WBAccountResponse)
async def create_wb_account(
    data: WBAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save WB API key (encrypted) and create account."""
    # Check permissions first
    permissions = await _check_wb_permissions(data.api_key)

    account = WBAccount(
        name=data.name,
        api_key_encrypted=encrypt_api_key(data.api_key),
        user_id=current_user.id,
        is_active=True,
        permissions_json=json.dumps(permissions) if permissions else None,
    )
    db.add(account)
    await db.flush()

    return WBAccountResponse(
        id=account.id,
        name=account.name,
        api_key_masked=_mask_key(data.api_key),
        user_id=account.user_id,
        is_active=account.is_active,
        permissions=permissions,
        created_at=account.created_at,
    )


@router.get("/wb-accounts", response_model=WBAccountList)
async def list_wb_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all WB accounts for current user."""
    query = select(WBAccount).where(WBAccount.user_id == current_user.id)
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(query.order_by(WBAccount.created_at.desc()))
    accounts = result.scalars().all()

    items = []
    for acc in accounts:
        try:
            decrypted = decrypt_api_key(acc.api_key_encrypted)
            masked = _mask_key(decrypted)
        except Exception:
            masked = "***invalid***"

        perms = None
        if acc.permissions_json:
            try:
                perms = json.loads(acc.permissions_json)
            except (json.JSONDecodeError, TypeError):
                perms = None

        items.append(WBAccountResponse(
            id=acc.id,
            name=acc.name,
            api_key_masked=masked,
            user_id=acc.user_id,
            is_active=acc.is_active,
            permissions=perms,
            created_at=acc.created_at,
        ))

    return WBAccountList(items=items, total=total)


@router.delete("/wb-accounts/{account_id}")
async def delete_wb_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete WB account."""
    result = await db.execute(
        select(WBAccount).where(
            WBAccount.id == account_id,
            WBAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    await db.delete(account)
    return {"ok": True}


@router.post("/wb-accounts/{account_id}/check-permissions", response_model=WBKeyValidationResult)
async def check_account_permissions(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-check permissions for existing WB account."""
    result = await db.execute(
        select(WBAccount).where(
            WBAccount.id == account_id,
            WBAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        api_key = decrypt_api_key(account.api_key_encrypted)
        permissions = await _check_wb_permissions(api_key)
    except Exception as e:
        return WBKeyValidationResult(valid=False, permissions=[], error=str(e))

    if not permissions:
        account.permissions_json = None
        await db.flush()
        return WBKeyValidationResult(
            valid=False,
            permissions=[],
            error="API ключ больше не действителен",
        )

    account.permissions_json = json.dumps(permissions)
    await db.flush()
    return WBKeyValidationResult(valid=True, permissions=permissions)
