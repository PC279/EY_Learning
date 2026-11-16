from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Product(BaseModel):
    name: str
    price: float

products = []

@app.get("/")
def home():
    return {"message": "FastAPI is running"}

@app.get("/products")
def get_products():
    return products

# FastAPI POST end point function - used to create a new record, send data to server
# Line 23 - Route Decorator, tells FastAPI that this function should handle incoming HTTP POST requests sent to the products URL path
@app.post("/products")

# product: Product - Pydantic Feature, function expects the incoming request to have a JSON body matching the Product model defined above.
# FastAPI automatically reads, validates and converts the incoming JSON into the object of Product class
def add_product(product: Product):

# Adds the newly received product into the python list named products - acts as DB in this case
    products.append(product)

# Sends a response back to whoever called the API.
# FASTAPI automatically converts the Python Dictionary into a JSON response containing a success message and the product data just added
    return {
        "message": "Product added",
        "product": product
    }

