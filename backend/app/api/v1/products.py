from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.product import Product
from app.models.watch import Watch
from app.schemas.product import ProductCreate, ProductList, ProductRead, ProductUpdate

router = APIRouter()


@router.get("", response_model=ProductList)
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
) -> ProductList:
    stmt = select(Product).order_by(Product.name)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.offset(skip).limit(limit)
    products = list((await db.execute(stmt)).scalars().all())

    # Beregn watch_count og lowest_price i én samlet forespørgsel
    stats: dict = {}
    if products:
        product_ids = [p.id for p in products]
        stats_rows = (
            await db.execute(
                select(
                    Watch.product_id,
                    func.count(Watch.id).label("wc"),
                    func.min(Watch.current_price).label("lp"),
                )
                .where(Watch.product_id.in_(product_ids))
                .group_by(Watch.product_id)
            )
        ).all()
        stats = {row.product_id: (row.wc, row.lp) for row in stats_rows}

    items = []
    for p in products:
        wc, lp = stats.get(p.id, (0, None))
        pr = ProductRead.model_validate(p)
        pr.watch_count = wc
        pr.lowest_price = float(lp) if lp is not None else None
        items.append(pr)

    return ProductList(items=items, total=total)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.watches).selectinload(Watch.shop))
    )
    product = (await db.execute(stmt)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produkt ikke fundet")
    return product


@router.post("", response_model=ProductRead, status_code=201)
async def create_product(
    body: ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    product = Product(**body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    product = (
        await db.execute(select(Product).where(Product.id == product_id))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produkt ikke fundet")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204, response_model=None)
async def delete_product(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    product = (
        await db.execute(select(Product).where(Product.id == product_id))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produkt ikke fundet")
    await db.delete(product)
    await db.commit()
