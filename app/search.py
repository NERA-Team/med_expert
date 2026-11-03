import json
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

async def search_medications(query: str, db: AsyncSession):
    cache_key = f"search:{query.lower()}"
    
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    sql = text("""
        SELECT 'trade' as type, id, name as title FROM trade_name 
        WHERE name ILIKE :q OR similarity(name, :q) > 0.3
        UNION
        SELECT 'substance' as type, id, name_ru as title FROM active_substance
        WHERE name_ru ILIKE :q OR similarity(name_ru, :q) > 0.3
        UNION
        SELECT 'group' as type, id, name_ru as title FROM pharmacotherapeutic_group
        WHERE name_ru ILIKE :q OR similarity(name_ru, :q) > 0.3
        LIMIT 20;
    """)
    
    result = await db.execute(sql, {"q": f"%{query}%"})
    rows = result.fetchall()
    
    data = [{"type": r.type, "id": str(r.id), "title": r.title} for r in rows]
    
    await redis_client.setex(cache_key, 600, json.dumps(data))
    
    return data