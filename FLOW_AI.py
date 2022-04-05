import time
import pyupbit
import datetime
import schedule
from fbprophet import Prophet

access = "you"
secret = "you"

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

def get_buy_average(ticker):
    """매수 평균가"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['avg_buy_price'] is not None:
                return float(b['avg_buy_price'])
            else:
                return 0
    return 0

predicted_close_price = 0
def predict_price(ticker):
    """Prophet으로 당일 종가 가격 24시간 예측 ---30분간격"""
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, interval="minute30")
    df = df.reset_index()
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    predicted_close_price = closeValue
predict_price("KRW-FLOW")
schedule.every().hour.do(lambda: predict_price("KRW-FLOW"))

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

# 자동매매 시작 , FLOW 5000원 이상으로 바꿈 , seconds을 hours=2로 바꿔서 7시에 매도하게 함.
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-FLOW")
        end_time = start_time + datetime.timedelta(days=1)
        schedule.run_pending()

        if start_time < now < end_time - datetime.timedelta(hours=1):
            target_price = get_target_price("KRW-FLOW", 0.3)
            current_price = get_current_price("KRW-FLOW")
            if target_price < current_price and current_price < predicted_close_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    upbit.buy_market_order("KRW-FLOW", krw*0.9995)


        elif start_time < now < end_time - datetime.timedelta(hours=2):
            current_price = get_current_price("KRW-FLOW")
            avg_buy_price = get_buy_average("KRW-FLOW")
            if current_price > (avg_buy_price*1.1) or current_price < (avg_buy_price*0.94):
                flow = get_balance("FLOW")
                if flow > 0.6:
                    upbit.sell_market_order("KRW-FLOW", flow*0.9995)

        else:
            flow = get_balance("FLOW")
            if flow > 0.6:
                upbit.sell_market_order("KRW-FLOW", flow*0.9995)
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)
