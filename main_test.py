from models import Stock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, get_db

from database import Base

# from mock_alchemy.mocking import AlchemyMagicMock

client = TestClient(app)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200

def test_create_stock():
    response = client.post("/stock", json={ "symbol": "AAPL" })

    session = override_get_db()

    id = session.query(Stock).filter(Stock.id == "AAPL").all()
    session.add_task.assert_called_once_with(fetch_stock_data, id)

    assert response.status_code == 200
    assert response.json() == {
        "code": "success",
        "message": "stock created"
    }


def test_duplicated_stock_should_reject():
    apple_stock = { "symbol": "AAPL" }
    response = client.post("/stock", json=apple_stock)
    assert response.status_code == 200

    response = client.post("/stock", json=apple_stock) # post the same stock
    assert response.status_code == 400
