"""Promotion endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.product import Product, WBAccount
from app.models.promotion import Promotion, PromotionProduct
from app.models.user import User
from app.schemas.promotion import (
    DecisionUpdate,
    PromotionDetailResponse,
    PromotionListResponse,
    PromotionProductResponse,
    PromotionResponse,
)

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get("", response_model=PromotionListResponse)
async def list_promotions(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List promotions with aggregated margin stats."""
    query = select(Promotion).order_by(Promotion.start_date.desc())
    if status:
        query = query.where(Promotion.status == status)

    result = await db.execute(query)
    promotions = list(result.scalars().all())

    items = []
    for promo in promotions:
        # Aggregate promotion products stats
        agg_result = await db.execute(
            select(
                func.count(PromotionProduct.id),
                func.avg(PromotionProduct.current_margin_pct),
                func.avg(PromotionProduct.promo_margin_pct),
                func.count().filter(PromotionProduct.promo_margin_pct > 0),
            ).where(PromotionProduct.promotion_id == promo.id)
        )
        row = agg_result.one()
        products_count = row[0] or 0
        avg_current = round(float(row[1]), 1) if row[1] is not None else None
        avg_promo = round(float(row[2]), 1) if row[2] is not None else None
        profitable = row[3] or 0

        items.append(PromotionResponse(
            id=promo.id,
            wb_promo_id=promo.wb_promo_id,
            name=promo.name,
            start_date=promo.start_date,
            end_date=promo.end_date,
            promo_type=promo.promo_type,
            status=promo.status,
            in_action_count=promo.in_action_count or 0,
            total_available=promo.total_available or 0,
            products_count=products_count,
            avg_current_margin=avg_current,
            avg_promo_margin=avg_promo,
            profitable_count=profitable,
        ))

    return PromotionListResponse(items=items, total=len(items))


@router.get("/{promo_id}", response_model=PromotionDetailResponse)
async def get_promotion_detail(
    promo_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get promotion details with all products and margins."""
    result = await db.execute(
        select(Promotion).where(Promotion.id == promo_id)
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")

    # Get promotion products
    pp_result = await db.execute(
        select(PromotionProduct)
        .where(PromotionProduct.promotion_id == promo_id)
        .order_by(PromotionProduct.promo_margin_pct.desc().nulls_last())
    )
    promo_products = list(pp_result.scalars().all())

    # Enrich with product info (vendor_code, title, image_url)
    nm_ids = [pp.nm_id for pp in promo_products]
    product_info = {}
    if nm_ids:
        prod_result = await db.execute(
            select(Product.nm_id, Product.vendor_code, Product.title, Product.image_url)
            .where(Product.nm_id.in_(nm_ids))
        )
        for row in prod_result.all():
            product_info[row[0]] = {
                "vendor_code": row[1],
                "title": row[2],
                "image_url": row[3],
            }

    # Aggregate stats
    agg_result = await db.execute(
        select(
            func.count(PromotionProduct.id),
            func.avg(PromotionProduct.current_margin_pct),
            func.avg(PromotionProduct.promo_margin_pct),
            func.count().filter(PromotionProduct.promo_margin_pct > 0),
        ).where(PromotionProduct.promotion_id == promo_id)
    )
    agg = agg_result.one()

    promo_response = PromotionResponse(
        id=promo.id,
        wb_promo_id=promo.wb_promo_id,
        name=promo.name,
        start_date=promo.start_date,
        end_date=promo.end_date,
        promo_type=promo.promo_type,
        status=promo.status,
        in_action_count=promo.in_action_count or 0,
        total_available=promo.total_available or 0,
        products_count=agg[0] or 0,
        avg_current_margin=round(float(agg[1]), 1) if agg[1] is not None else None,
        avg_promo_margin=round(float(agg[2]), 1) if agg[2] is not None else None,
        profitable_count=agg[3] or 0,
    )

    products = []
    for pp in promo_products:
        info = product_info.get(pp.nm_id, {})
        products.append(PromotionProductResponse(
            nm_id=pp.nm_id,
            vendor_code=info.get("vendor_code"),
            title=info.get("title"),
            image_url=info.get("image_url"),
            plan_price=float(pp.plan_price) if pp.plan_price else None,
            plan_discount=float(pp.plan_discount) if pp.plan_discount else None,
            current_price=float(pp.current_price) if pp.current_price else None,
            in_action=pp.in_action or False,
            current_margin_pct=float(pp.current_margin_pct) if pp.current_margin_pct is not None else None,
            current_margin_rub=float(pp.current_margin_rub) if pp.current_margin_rub is not None else None,
            promo_margin_pct=float(pp.promo_margin_pct) if pp.promo_margin_pct is not None else None,
            promo_margin_rub=float(pp.promo_margin_rub) if pp.promo_margin_rub is not None else None,
            decision=pp.decision or "pending",
        ))

    return PromotionDetailResponse(promotion=promo_response, products=products)


@router.post("/{promo_id}/decisions")
async def update_decisions(
    promo_id: int,
    data: DecisionUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Batch update decisions (enter/skip) for promotion products."""
    result = await db.execute(
        select(Promotion).where(Promotion.id == promo_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Promotion not found")

    if data.decision not in ("enter", "skip", "pending"):
        raise HTTPException(status_code=400, detail="Invalid decision. Use 'enter', 'skip', or 'pending'.")

    now = datetime.now(UTC)
    pp_result = await db.execute(
        select(PromotionProduct).where(
            PromotionProduct.promotion_id == promo_id,
            PromotionProduct.nm_id.in_(data.nm_ids),
        )
    )
    updated = 0
    for pp in pp_result.scalars().all():
        pp.decision = data.decision
        pp.decided_at = now
        updated += 1

    await db.commit()
    return {"updated": updated}
