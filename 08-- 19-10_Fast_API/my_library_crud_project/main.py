from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from fastapi import FastAPI, HTTPException

app = FastAPI()

class Book(BaseModel):
    book_id: int
    title: str
    author: str
    category: str
    price: float
    stock:int

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="library_store",
        user="postgres",
        password="Admin@123"
    )

    print("Connected to PostgreSQL database")
    return conn


@app.get("/books")
def get_books():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows

@app.post("/books")
def add_book(book: Book):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO books (book_id, title, author, category, price, stock)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (book.book_id, book.title, book.author, book.category, book.price, book.stock)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "message": "Book added successfully",
        "product": book
    }


@app.get("/books/category/{Category}")
def get_book_category(Category: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM books WHERE category = %s",
        (Category,)
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No books found in category '{Category}'"
        )

    return rows


@app.get("/books/price/{cost}")
def get_books_above(cost: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM books WHERE price > %s",
        (cost,)
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No books found above Rupees '{cost}'"
        )

    return rows

@app.put("/books/{book_id}")
def update_book(book_id: int, book: Book):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE books
        SET title = %s, author = %s, category = %s, price = %s, stock = %s
        WHERE book_id = %s
        """,
        (book.title, book.author, book.category, book.price, book.stock, book_id)
    )

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Book of '{book_id}' not found"
        )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "message": f"Book with '{book_id}' updated successfully"
    }

conn = get_connection()
conn.close()