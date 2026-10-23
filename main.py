from fastapi import (FastAPI, Query, HTTPException)
from typing import Literal 

from psycopg.rows import dict_row
import psycopg

import os


DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "goldapple_pet")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

app = FastAPI()

def get_connection():

    return psycopg.connect(
            dbname = DB_NAME,
            password=DB_PASSWORD,
            user=DB_USER,
            host=DB_HOST,
            port=DB_PORT,
            row_factory=dict_row,
            autocommit=True
        )


@app.get("/")
def root():
    return {
        "project": "GoldApple Analytics API",
        "status": "OK"
    }


@app.get("/health")
def health():
    return {
        "service": "OK",
        "database": "not_check"
    }


@app.get("/products/{item_id}")
def get_product(item_id: str):

    with get_connection() as conn:

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT  
                    *
                FROM product
                WHERE TRUE 
                AND item_id = %s
                """,
                [item_id]
            ) 
            product = cursor.fetchone()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )
        
        return product


@app.get("/products")
def get_products(category: Literal['skincare', 'perfume', 'supplements'] | None = None, limit: int = Query(default=5, ge=1, le=50)):

    with get_connection() as conn:

        with conn.cursor() as cursor:
            if category is not None:
                cursor.execute(
                    """
                    SELECT
                        *
                    FROM product
                    WHERE category = %s
                    LIMIT %s
                    """,
                    [category, limit]
                )
            else:
                cursor.execute(
                    """
                    SELECT 
                        *
                    FROM product
                    LIMIT %s
                    """,
                    [limit]
                )
            
            products = cursor.fetchall()

        return products
