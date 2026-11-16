from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from FastAPI"}

@app.get("/hello/{name}")
# {} - curly brackets means a value is going there
# name is a dynamic value that we will be getting in the runtime
def say_hello(name: str):
    return {"message": f"Hello {name}"}