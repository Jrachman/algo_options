import json
import requests
import urllib3
import bs4 as bs
import numpy as np
import pandas as pd
from iex import Stock
import matplotlib.pyplot as plt

#personal notes:
# - periods are based on what the increments on the charted data are (i.e., if 1m is based on day, then the period will be days)

def sp500_tickers() -> [str]:
    resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    soup = bs.BeautifulSoup(resp.text, 'lxml')
    table = soup.find('table', {'class': 'wikitable sortable'})
    tickers = []
    for row in table.findAll('tr')[1:]:
        ticker = row.findAll('td')[0].text
        tickers.append(ticker)

    return tickers

def nyse_is_open() -> str: #return whether or not the stock market is open right now. if it is, then continue running application; else, stop feeding data as long as market is closed
    response = requests.get("https://www.stockmarketclock.com/api-v1/status?exchange=nyse")
    return response.json()['results']['nyse']['status']

def test_for_hourly_analysis(): #note that this function should be based on the range of init_get_data
    response = requests.get("https://api.iextrading.com/1.0/stock/aapl/chart/1d")
    list_of_dicts = response.json()
    time_and_close = {'minute': [], 'close': []}
    for dict_ in list_of_dicts:
        if int(dict_['minute'][-2:]) == 59:
            time_and_close['minute'].append(dict_['minute'])
            time_and_close['close'].append(dict_['close']) 
    return time_and_close


def init_get_data(stock: str, range_: str):
    stock_chart = Stock(stock).chart_table(range=range_)
    return stock_chart[['date', 'close']]

def init_rsi_func(prices, n=14):
    deltas = np.diff(prices) #out[n] = a[n+1] - a[n]
    seed = deltas[:n+1]
    up = seed[seed >= 0].sum() / n
    down = -seed[seed < 0].sum() / n
    rs = up / down
    rsi = np.zeros_like(prices)
    rsi[:n] = 100 - 100 / (1 + rs)
    #part above takes care of the initialization of the rsi function from 1 to n (14), then the rsi calculation begins
    for i in range(n, len(prices)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0
        else:
            upval = 0
            downval = -delta
        up = (up * (n - 1) + upval) / n
        down = (down * (n - 1) + downval) / n
        rs = up / down
        rsi[i] = 100 - 100 / (1 + rs)
        #note: in order to calculate today's rsi, you need to have 
        # (1) the difference between today's current/closing price to the previous day's closing price
        # (2) the previous up and down
    temp_up = np.zeros_like(prices)
    temp_up[-1] = up
    up = temp_up
    temp_down = np.zeros_like(prices)
    temp_down[-1] = down
    down = temp_down
    return rsi, np.diff(pd.concat([pd.Series([0]), prices])), up, down

def ma_func(values, window):
    weigths = np.repeat(1.0, window) / window
    smas = np.convolve(values, weigths, 'valid')
    return smas # as a numpy array

def ema_func(values, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a

def computeMACD(x, slow=26, fast=12):
    #compute the MACD (Moving Average Convergence/Divergence) using a fast and slow exponential moving avg'
    #return value is emaslow, emafast, macd which are len(x) arrays
    emaslow = ema_func(x, slow)
    emafast = ema_func(x, fast)
    return emaslow, emafast, emafast - emaslow

def init_data(stock: str, range_: str) -> None:
    stock_data = init_get_data(stock, range_)
    rsi, deltas, up, down = init_rsi_func(stock_data['close'], 8) #8 periods, instead of default 14; 70/30 is indicator for oversold, overbought
    stock_data = stock_data.assign(rsi=rsi, deltas=deltas, up=up, down=down) 
    file_name = 'data-' + stock + '.csv'
    stock_data.to_csv(file_name, index=False)

def use_data(stock): #still a testing func
    file_name = 'data-' + stock + '.csv'
    data = pd.read_csv(file_name)
    return [data['close'], ma_func(data['close'], 13), ma_func(data['close'], 30), ma_func(data['close'], 200)]

if __name__ == "__main__":
    my_stocks = ['SPY', 'AMZN', 'AMD', 'AAPL', 'NVDA', 'TSLA']
    #if len(my_stocks) == 0:
        #my_stocks = sp500_tickers()
        
    for stock in my_stocks:
        init_data(stock, '1y') #change range for iextrading api here

    print(nyse_is_open())
    print(test_for_hourly_analysis())
    
    for data in use_data('SPY'):
        plt.plot(data)
    plt.show()

    #for _ in range(20):
        #print(Stock("F").price())