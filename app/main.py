from fastapi import FastAPI
from app.db.database import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Spiit Service")
