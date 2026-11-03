from fastapi import FastAPI, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.search import redis_client
from enum import Enum
import json

app = FastAPI(title="MedExpert API", version="1.0.0")

class SearchType(str, Enum):
    all = "all"
    trade = "trade"
    mnn = "mnn"
    group = "group"

@app.get("/api/search")
async def search_medications(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    search_by: SearchType = Query(SearchType.all, description="Где искать: all, trade, mnn, group"),
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"search:{search_by.value}:{q.lower()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return JSONResponse(
            content={"query": q, "search_by": search_by.value, "source": "cache", "results": json.loads(cached)},
            media_type="application/json; charset=utf-8"
        )

    base_select = """
        SELECT DISTINCT 
            dp.id::text as product_id,
            tn.name as trade_name,
            df.name_short as dosage_form,
            dp.strength_value,
            dp.strength_unit,
            pg.name_ru as group_name,
            ast.name_ru as mnn_name
        FROM drug_product dp
        JOIN trade_name tn ON dp.trade_name_id = tn.id
        JOIN dosage_form df ON dp.dosage_form_id = df.id
        LEFT JOIN product_group pgrp ON dp.id = pgrp.drug_product_id
        LEFT JOIN pharmacotherapeutic_group pg ON pgrp.pharmacotherapeutic_group_id = pg.id
        LEFT JOIN product_active_substance pas ON dp.id = pas.drug_product_id
        LEFT JOIN active_substance ast ON pas.active_substance_id = ast.id
    """

    if search_by == SearchType.trade:
        where_clause = """
            WHERE tn.name ILIKE :q OR similarity(tn.name, :q) > 0.3
        """
    elif search_by == SearchType.mnn:
        where_clause = """
            WHERE ast.name_ru ILIKE :q OR ast.name_latin ILIKE :q 
               OR similarity(ast.name_ru, :q) > 0.3 OR similarity(ast.name_latin, :q) > 0.3
        """
    elif search_by == SearchType.group:
        where_clause = """
            WHERE pg.name_ru ILIKE :q OR similarity(pg.name_ru, :q) > 0.3
        """
    else:
        where_clause = """
            WHERE tn.name ILIKE :q OR similarity(tn.name, :q) > 0.3
               OR ast.name_ru ILIKE :q OR similarity(ast.name_ru, :q) > 0.3
               OR pg.name_ru ILIKE :q OR similarity(pg.name_ru, :q) > 0.3
        """

    final_sql = text(base_select + where_clause + " LIMIT 50;")
    result = await db.execute(final_sql, {"q": f"%{q}%"})
    rows = result.fetchall()

    results = []
    for r in rows:
        if not r.dosage_form and not r.strength_value:
            continue
            
        dosage = ""
        if r.strength_value:
            val_formatted = f"{float(r.strength_value):g}"
            dosage = f"{val_formatted} {r.strength_unit}"
            
        results.append({
            "product_id": r.product_id,
            "trade_name": r.trade_name,
            "dosage": dosage,
            "form": r.dosage_form,
            "group": r.group_name,
            "mnn": r.mnn_name
        })

    await redis_client.setex(cache_key, 600, json.dumps(results, ensure_ascii=False))
    
    return JSONResponse(
        content={"query": q, "search_by": search_by.value, "source": "database", "results": results},
        media_type="application/json; charset=utf-8"
    )

@app.get("/api/products/{product_id}")
async def get_product_details(product_id: str, db: AsyncSession = Depends(get_db)):
    sql_product = text("""
        SELECT 
            dp.id::text, tn.name as trade_name, df.name_ru as form_name,
            dp.strength_value, dp.strength_unit
        FROM drug_product dp
        JOIN trade_name tn ON dp.trade_name_id = tn.id
        JOIN dosage_form df ON dp.dosage_form_id = df.id
        WHERE dp.id = :pid
    """)
    res = await db.execute(sql_product, {"pid": product_id})
    product = res.fetchone()
    
    if not product:
        return JSONResponse(status_code=404, content={"error": "Препарат не найден"})

    sql_regimens = text("""
        SELECT regimen_text, course_note, age_min_months
        FROM dosing_regimen
        WHERE drug_product_id = :pid
        ORDER BY age_min_months NULLS FIRST
    """)
    res_reg = await db.execute(sql_regimens, {"pid": product_id})
    regimens = res_reg.fetchall()

    return JSONResponse(content={
        "product_id": product.id,
        "trade_name": product.trade_name,
        "form": product.form_name,
        "dosage": f"{float(product.strength_value):g} {product.strength_unit}" if product.strength_value else "",
        "regimens": [
            {
                "text": r.regimen_text,
                "course": r.course_note,
                "min_age_months": r.age_min_months
            } for r in regimens
        ]
    }, media_type="application/json; charset=utf-8")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}