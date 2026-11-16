from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

app = FastAPI()

class Product(BaseModel):
    id: int
    name: str
    price: float

products = []

@app.get("/products")
def get_products():
    return products

@app.post("/products")
def add_product(product: Product):
    products.append(product)
    return product

@app.get("/products/{product_id}")
# returns a single product that is asked by matching it with the id
def get_products(product_id: int):
    for product in products:
        if product.id == product_id:
            return product

    raise HTTPException(status_code=404, detail="Product not found")

@app.put("/products/{product_id}")
# to change the product details using PUT command. It takes id from the user, product_id, check if there is an id
# in the list matching with the given product_id, if matched updates it with the data given by user. the new data given
# by the user should match the Product class, it should has id,name and price, otherwise it will not be updated
def update_product(product_id: int, updated_product: Product):
    for index, product in enumerate(products):
        if product.id == product_id:
            products[index] = updated_product
            return updated_product

    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    for index, product in enumerate(products):
        if product.id == product_id:
            deleted = products.pop(index)
            return {
                "message": "Product deleted!",
                "product": deleted
            }
    raise HTTPException(status_code=404, detail="Product not found")
