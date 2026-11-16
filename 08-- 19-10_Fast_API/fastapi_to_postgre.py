from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
# psycopg2 acts as a translator between python and postgre as postgreSQL speaks its own protocol.

app = FastAPI()

class Product(BaseModel):
    id: int
    name: str
    price: float

# Defining a reusable function that handles setting up and establishing the connection with database
def get_connection():
    # psycopg2.connect - it attempts to open the connection to the database using the details provided
    conn = psycopg2.connect(
        host="localhost",
        database="fastapi_store",
        user="postgres",
        password="Admin@123",
    )

    print("Connected to PostgreSQL successfully")
    return conn
# return conn - sends the active connection object so it can be used for database operations

@app.get("/products")
def get_products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


@app.post("/products")
def add_product(product: Product):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO products (id, name, price)
        VALUES (%s, %s, %s)
        """,
        (product.id, product.name, product.price)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "message": "Product added successfully",
        "product": product
    }


@app.put("/products/{product_id}")
def update_product(product_id: int, product: Product):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE products
        SET name = %s,
            price = %s
        WHERE id = %s
        """,
        (product.name, product.price, product_id)
    )

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "message": "Product updated successfully"
    }


@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM products WHERE id = %s",
        (product_id,)
    )

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "message": "Product deleted successfully"
    }



conn = get_connection()
conn.close()
