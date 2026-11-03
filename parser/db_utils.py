from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import models

async def get_or_create_group(session: AsyncSession, name: str):
    name = name.strip()
    stmt = select(models.PharmacotherapeuticGroup).where(models.PharmacotherapeuticGroup.name_ru == name)
    res = await session.execute(stmt)
    group = res.scalar_one_or_none()
    if not group:
        group = models.PharmacotherapeuticGroup(
            code=name.lower().replace(" ", "_")[:90],
            name_ru=name,
            level=1
        )
        session.add(group)
        await session.flush()
    return group

async def get_or_create_substance(session: AsyncSession, name_ru: str, name_latin: str):
    stmt = select(models.ActiveSubstance).where(models.ActiveSubstance.name_latin == name_latin)
    res = await session.execute(stmt)
    sub = res.scalar_one_or_none()
    if not sub:
        sub = models.ActiveSubstance(
            kind="mnn",
            name_ru=name_ru.strip(),
            name_latin=name_latin.strip()
        )
        session.add(sub)
        await session.flush()
    return sub

async def get_or_create_trade_name(session: AsyncSession, name: str):
    name = name.strip()
    stmt = select(models.TradeName).where(models.TradeName.name == name)
    res = await session.execute(stmt)
    trade = res.scalar_one_or_none()
    if not trade:
        trade = models.TradeName(name=name)
        session.add(trade)
        await session.flush()
    return trade