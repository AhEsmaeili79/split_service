from fastapi import FastAPI
from app.db.database import Base, engine
from app.api.v1.routes.groups import router as groups_router
from app.api.v1.routes.expenses import router as expenses_router
from app.api.v1.routes.settlements import router as settlements_router
from app.rabbitmq.setup import init_rabbitmq
from app.rabbitmq.background_consumer import start_background_consumer
from app.services.pending_request_cleanup import start_pending_request_cleanup

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Split Service - Debt Management",
    description="Manages groups, debts, expenses, and settlements",
    version="1.0.0"
)

# Initialize RabbitMQ
init_rabbitmq()

# Start background consumer for async message processing
start_background_consumer()

# Start cleanup process for old pending requests
start_pending_request_cleanup()

app.include_router(groups_router)
app.include_router(expenses_router)
app.include_router(settlements_router)

@app.get("/")
def read_root():
    return {"message": "Split Service API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}