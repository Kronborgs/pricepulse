from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import SuperOrAdmin, get_current_user
from app.database import get_db
from app.models.product import Product
from app.models.product_watch import ProductWatch
from app.models.user import User
from app.models.watch import Watch
from app.schemas.product import MergeProductRequest, ProductCreate, ProductList, ProductRead, ProductUpdate

router = APIRouter()


def _is_privileged(user: User) -> bool:
    return user.role in ("admin", "superuser")


def _assert_ownership(product: Product, user: User) -> None:
    if not _is_privileged(user) and product.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Ikke tilstrækkelige rettigheder")


@router.get("", response_model=ProductList)
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
) -> ProductList:
    stmt = select(Product).order_by(Product.name)

    # Brugere (user-rolle) ser kun egne produkter
    if not _is_privileged(user):
        stmt = stmt.where(Product.owner_id == user.id)

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
    user: User = Depends(get_current_user),
) -> Product:
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.watches).selectinload(Watch.shop))
    )
    product = (await db.execute(stmt)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produkt ikke fundet")
    _assert_ownership(product, user)
    return product


@router.post("", response_model=ProductRead, status_code=201)
async def create_product(
    body: ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> Product:
    product = Product(**body.model_dump(), owner_id=user.id)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> Product:
    product = (
        await db.execute(select(Product).where(Product.id == product_id))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produkt ikke fundet")
    _assert_ownership(product, user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.post("/{product_id}/merge", response_model=ProductRead)
async def merge_products(
    product_id: uuid.UUID,
    body: MergeProductRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: User = Depends(SuperOrAdmin),
) -> ProductRead:
    """Sammenflet kilde-produktets watches ind i dette produkt og slet kilde-produktet."""
    if product_id == body.source_product_id:
        raise HTTPException(status_code=400, detail="Kan ikke sammenflet et produkt med sig selv")

    target = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Produkt ikke fundet")

    source = (await db.execute(select(Product).where(Product.id == body.source_product_id))).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Kilde-produkt ikke fundet")

    # Flyt V1 watches
    await db.execute(
        update(Watch)
        .where(Watch.product_id == body.source_product_id)
        .values(product_id=product_id)
    )
    # Flyt V2 product_watches
    await db.execute(
        update(ProductWatch)
        .where(ProductWatch.product_id == body.source_product_id)
        .values(product_id=product_id)
    )
    # Arv billede hvis target mangler
    if not target.image_url and source.image_url:
        target.image_url = source.image_url

    await db.delete(source)
    await db.commit()

    # Genindlæs med stats
    product = (await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.watches).selectinload(Watch.shop))
    )).scalar_one()
    stats_rows = (await db.execute(
        select(func.count(Watch.id).label("wc"), func.min(Watch.current_price).label("lp"))
        .where(Watch.product_id == product_id)
    )).one()
    pr = ProductRead.model_validate(product)
    pr.watch_count = stats_rows.wc or 0
    pr.lowest_price = float(stats_rows.lp) if stats_rows.lp is not None else None
    return pr


@router.delete("/{product_id}", status_code=204, response_model=None)
async def delete_product(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
) -> None:
    product = (
        await db.execute(select(Product).where(Product.id == product_id))
    ).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produkt ikke fundet")
    _assert_ownership(product, user)
    await db.delete(product)
    await db.commit()
