from fastapi import FastAPI 
from app.database import Base, engine 


app = FastAPI(title="Grovii Backend")


app = FastAPI(title="Grovii Backend")

Base.metadata.create_all(bind = engine)

@app.get('/')
def root():   
    return {"message": "Welcome to Grovii API!"}

