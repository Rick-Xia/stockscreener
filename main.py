import models
from starlette.background import BackgroundTasks
from sqlalchemy.orm import Session
from models import Stock
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from database import SessionLocal, engine
from pydantic import BaseModel
import yfinance as yf

app = FastAPI()

models.Base.metadata.create_all(bind=engine) 

templates = Jinja2Templates(directory="templates")


class StockRequest(BaseModel):
    symbol: str


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.get("/")
def home(request: Request, forward_pe = None, dividend_yield = None, ma50 = False, ma200 = False, db: Session = Depends(get_db)):
    """
    display the stock screener dashboard / homepage
    """

    stocks = db.query(Stock)

    if forward_pe:
        stocks = stocks.filter(Stock.forward_pe < forward_pe)

    if dividend_yield:
        stocks = stocks.filter(Stock.dividend_yield > dividend_yield)

    if ma50:
        stocks = stocks.filter(Stock.price > Stock.ma50)

    if ma200:
        stocks = stocks.filter(Stock.price > Stock.ma200)

    return templates.TemplateResponse("home.html", {
        "request": request,
        "stocks": stocks,
        "forward_pe": forward_pe,
        "dividend_yield": dividend_yield,
        "ma50": ma50,
        "ma200": ma200
    })


def fetch_stock_data(stock_id: int):

    db = SessionLocal()

    stock = db.query(Stock).filter(Stock.id == stock_id).first()

    yahoo_data = yf.Ticker(stock.symbol)

    stock.ma200 = yahoo_data.info['twoHundredDayAverage']
    stock.ma50 = yahoo_data.info['fiftyDayAverage']
    stock.price = yahoo_data.info['previousClose']
    stock.forward_pe = yahoo_data.info['forwardPE']
    stock.forward_eps = yahoo_data.info['forwardEps']

    if yahoo_data.info['dividendYield'] is not None:
        stock.dividend_yield = yahoo_data.info['dividendYield'] * 100

    db.add(stock)
    db.commit()


@app.post("/stock")
async def create_stock(stock_request: StockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    create a stock and stores it in the DB
    background task to load stock info using yfinance
    """

    stock = Stock()
    stock.symbol = stock_request.symbol
    db.add(stock)
    db.commit()

    background_tasks.add_task(fetch_stock_data, stock.id)
    
    return {
        "code": "success",
        "message": "stock created"
    }
