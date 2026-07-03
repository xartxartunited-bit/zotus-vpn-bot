"""Async MySQL connections to Zotus++ and Store databases."""
import aiomysql
from config import ZOTUSPP_DB, STORE_DB

_zotuspp_pool: aiomysql.Pool | None = None
_store_pool: aiomysql.Pool | None = None


async def init_pools() -> None:
    global _zotuspp_pool, _store_pool
    _zotuspp_pool = await aiomysql.create_pool(**ZOTUSPP_DB, autocommit=True)
    _store_pool = await aiomysql.create_pool(**STORE_DB, autocommit=True)


async def close_pools() -> None:
    if _zotuspp_pool:
        _zotuspp_pool.close()
        await _zotuspp_pool.wait_closed()
    if _store_pool:
        _store_pool.close()
        await _store_pool.wait_closed()


def zotuspp() -> aiomysql.Pool:
    assert _zotuspp_pool, "DB not initialized"
    return _zotuspp_pool


def store() -> aiomysql.Pool:
    assert _store_pool, "DB not initialized"
    return _store_pool


async def fetch_one(pool: aiomysql.Pool, sql: str, params: tuple = ()) -> dict | None:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params)
            return await cur.fetchone()


async def fetch_all(pool: aiomysql.Pool, sql: str, params: tuple = ()) -> list[dict]:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def execute(pool: aiomysql.Pool, sql: str, params: tuple = ()) -> int:
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return cur.rowcount


async def fetch_val(pool: aiomysql.Pool, sql: str, params: tuple = ()):
    row = await fetch_one(pool, sql, params)
    if row:
        return next(iter(row.values()))
    return None
