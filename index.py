from dash import dcc, html, Dash, Output, Input
from binance import ThreadedWebsocketManager, Client
from datetime import datetime, timedelta
import pytz
import talib
import statsmodels.api as sm
from statsmodels.tsa.seasonal import STL
from custom_ta.smi import SMI
import pandas as pd
from strategy import MiEstrategia
from plots import Graph
from dotenv import load_dotenv
import os
import warnings
from custom_ta.vsa import vsa_indicator
warnings.filterwarnings("ignore")
load_dotenv()
TICKET = os.getenv("TICKET")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
DEBUG=os.getenv("DEBUG")

utc3 = pytz.timezone('America/Buenos_Aires')
columns = ['open', 'high', 'low', 'close', 'volume']
all_kline_data = pd.DataFrame(columns=columns)
real_time_kline_data = pd.DataFrame(columns=columns)
app = Dash(__name__, suppress_callback_exceptions=True)
client = Client(API_KEY, API_SECRET)
strategy = MiEstrategia()
graph = Graph()
cursor = None
stop_cursor = None
def update_all_kline_data(symbol, interval, start_time):
    global all_kline_data
    try:
        klines = client.get_historical_klines(symbol, interval, start_time)
        data = []
        for kline in klines:
            kline_data = {
                'time': datetime.fromtimestamp(kline[0] / 1000, tz=pytz.utc).astimezone(utc3),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            }
            data.append(kline_data)
        all_kline_data = pd.DataFrame(data)
        all_kline_data.set_index('time', inplace=True)

    except Exception as e:
        print(f"Error al obtener los datos de la línea de tiempo: {e}")        

def update_real_time_kline_data(msg):
    global real_time_kline_data
    if 'k' in msg:
        kline = msg['k']
        new_row = pd.DataFrame({
            'time': [datetime.fromtimestamp(kline['t'] / 1000, tz=pytz.utc).astimezone(utc3)],
            'open': [float(kline['o'])],
            'high': [float(kline['h'])],
            'low': [float(kline['l'])],
            'close': [float(kline['c'])],
            'volume': [float(kline['v'])]
        })
        new_row = new_row.dropna()
        new_row.set_index('time', inplace=True)
        real_time_kline_data = pd.concat([real_time_kline_data, new_row])
        if len(real_time_kline_data) > 60:
            real_time_kline_data = real_time_kline_data[-60:]

def calculate_ta(lamb=1, k=5, d=3, ma=4, seasonal=20):
    data = all_kline_data
    close = data['close'].values
    high = data['high'].values
    low = data['low'].values
    volume = data['volume'].values
    price_hp = sm.tsa.filters.hpfilter(close, lamb=lamb)[-1]
    #price_hp = talib.EMA(close, 14)
    [smi, smi_ma] = SMI(price_hp, k, d, ma)
    stl = STL(close, period=seasonal).fit()
    seasonal =  talib.RSI(stl.trend, ma)
    seasonal_ma = talib.EMA(seasonal, ma)
    price_hp = pd.Series(price_hp, index=data.index)
    smi = pd.Series(smi, index=data.index)
    smi_ma = pd.Series(smi_ma, index=data.index)
    seasonal = pd.Series(seasonal, index=data.index)
    seasonal_ma = pd.Series(seasonal_ma, index=data.index)
    return [price_hp, smi, smi_ma, stl, seasonal, seasonal_ma]

def abrir_orden(symbol, side, quantity):
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        print(f"Orden {side} abierta para {quantity} {symbol}")
    except Exception as e:
        print(f"Error al abrir la orden: {e}")

@app.callback(
    Output('kline-graph', 'figure'),
    Input('interval-component', 'n_intervals')
)    
def sync_data(n):
    global all_kline_data, real_time_kline_data
    if all_kline_data.empty or real_time_kline_data.empty or (all_kline_data.iloc[-1] == real_time_kline_data.iloc[-1]).all():
        return graph.layout
    all_kline_data.loc[real_time_kline_data.index[-1]] = real_time_kline_data.iloc[-1]
    [price_hp, smi, smi_ma, stl, seasonal, seasonal_ma] = calculate_ta()
    strategy.update_ta_data(all_kline_data, smi, smi_ma, seasonal, seasonal_ma)
    strategy.simular_estrategia()
    graph.update_ta_data(all_kline_data, price_hp, smi, smi_ma, stl, seasonal, seasonal_ma)
    graph.update_strategy_data(strategy.csmi, strategy.ccycle, strategy.orders, strategy.risk)
    graph.update_ta_plots()
    graph.update_strategy_plots()
    return graph.layout

def start_service():
    bsm = ThreadedWebsocketManager()
    bsm.start()
    try:
        bsm.start_kline_socket(callback=update_real_time_kline_data, symbol=TICKET, interval='1m')#Se debe modificar a futures, no se realizo por los parametros extras
    except Exception as e:
        print("Error al iniciar el socket:", str(e))

if __name__ == '__main__':
    #esto falla por culpla de la zona horaria -arreglar 
    start_time = (datetime.now() - timedelta(minutes= 60)).strftime("%d %b %Y %H:%M:%S")
    update_all_kline_data(TICKET, Client.KLINE_INTERVAL_1MINUTE, start_time)
    if all_kline_data is not None:  # Verifica si se obtuvieron los datos correctamente
        graph.init_ta_plots(TICKET=TICKET)
        graph.init_strategy_plots()
        start_service()
        app.layout = html.Div([
            html.H1("Tiempo Real"),
            dcc.Graph(id='kline-graph'),
            dcc.Interval(id='interval-component', interval=1000),  # Actualizar cada 5 segundos
        ])
        app.run_server(debug=DEBUG)
    else:
        print("No se pudieron obtener los datos de la línea de tiempo.")