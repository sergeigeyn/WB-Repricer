"""Product endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.price import PriceSnapshot
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCostUpdate, ProductList, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


async def _enrich_with_prices(
    db: AsyncSession, products: list[Product]
) -> list[ProductResponse]:
    """Attach latest price snapshot data to each product."""
    if not products:
        return []

    product_ids = [p.id for p in products]

    # Get latest snapshot per product using DISTINCT ON
    latest_prices_q = (
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id.in_(product_ids))
        .distinct(PriceSnapshot.product_id)
        .order_by(PriceSnapshot.product_id, PriceSnapshot.collected_at.desc())
    )
    result = await db.execute(latest_prices_q)
    snapshots = {s.product_id: s for s in result.scalars().all()}

    items = []
    for p in products:
        snap = snapshots.get(p.id)
        items.append(
            ProductResponse(
                id=p.id,
                nm_id=p.nm_id,
                vendor_code=p.vendor_code,
                brand=p.brand,
                category=p.category,
                title=p.title,
                image_url=p.image_url,
                cost_price=float(p.cost_price) if p.cost_price else None,
                tax_rate=float(p.tax_rate) if p.tax_rate else None,
                total_stock=p.total_stock,
                is_active=p.is_active,
                is_locomotive=p.is_locomotive,
                created_at=p.created_at,
                current_price=float(snap.wb_price) if snap else None,
                discount_pct=float(snap.wb_discount) if snap else None,
                final_price=float(snap.final_price) if snap and snap.final_price else None,
            )
        )
    return items


@router.get("", response_model=ProductList)
async def list_products(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    brand: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    in_stock: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    query = select(Product)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Product.title.ilike(pattern),
                Product.vendor_code.ilike(pattern),
                Product.brand.ilike(pattern),
            )
        )
    if brand:
        query = query.where(Product.brand == brand)
    if category:
        query = query.where(Product.category == category)
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
    if in_stock:
        query = query.where(Product.total_stock >= 1)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit).order_by(Product.nm_id))
    products = list(result.scalars().all())

    items = await _enrich_with_prices(db, products)
    return ProductList(items=items, total=total)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    enriched = await _enrich_with_prices(db, [product])
    return enriched[0]


@router.put("/{product_id}/cost", response_model=ProductResponse)
async def update_product_cost(
    product_id: int,
    data: ProductCostUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.cost_price is not None:
        product.cost_price = data.cost_price
    if data.tax_rate is not None:
        product.tax_rate = data.tax_rate
    if data.extra_costs_json is not None:
        product.extra_costs_json = data.extra_costs_json

    enriched = await _enrich_with_prices(db, [product])
    return enriched[0]
