from plotly.subplots import make_subplots
import pandas as pd
import talib
COLOR_MA = 'red'
COLOR_OSCILATOR = 'blue'
COLOR_FILTER = 'yellow'
COLOR_TREND = 'green'
KLINE = 'Velas'
FILTER = 'Hodrick Prescott'
TREND = 'Tendencia'
STOP = 'STOP'
SMI = 'SMI'
MA_SMI = 'Media SMI'
CYCLER = 'Ciclos'
MA_CYCLER = 'Media Ciclos'
ORDERS = 'Ordenes'
ALERT_BULL_SMI = 'Alzas SMI'
ALERT_BEAR_SMI = 'Bajas SMI'
ALERT_BULL_CYCLER = 'Alzas Ciclos'
ALERT_BEAR_CYCLER = 'Bajas Ciclos'
MARKER_BEAR = dict(
    color='red',  
    size=10,      
    symbol='circle' 
)
MARKER_BULL = dict(
    color='green',  
    size=10,      
    symbol='circle' 
)

class Graph:
    def __init__(self):
        self.layout = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.4, 0.2, 0.2, 0.2])
        self.ci_smi = pd.Series()
        self.co_smi = pd.Series()
        self.ci_cycle = pd.Series()
        self.co_cycle = pd.Series()

    def update_ta_data(self, all_kline_data, price_hp, smi, smi_ma, stl, seasonal, seasonal_ma):
        self.all_kline_data = all_kline_data
        self.price_hp = price_hp
        self.smi = smi
        self.smi_ma = smi_ma
        self.stl = stl
        self.seasonal = seasonal
        self.seasonal_ma = seasonal_ma

    def update_strategy_data(self, csmi, ccycle, orders, stops):
        for count in range(len(csmi)):
            idx = csmi.index[count]
            if csmi[idx]:
                self.co_smi[idx] = csmi[idx]
            elif csmi[idx] != None:
                self.ci_smi[idx] = csmi[idx]
            if ccycle[idx]:
                self.co_cycle[idx] = ccycle[idx]
            elif ccycle[idx] != None:
                self.ci_cycle[idx] = ccycle[idx]
        self.orders = orders
        self.stops = stops
        
    def init_ta_plots(self, TICKET):
        self.layout.update_layout(
            title=TICKET,
            xaxis=dict(title='Tiempo'),
            yaxis=dict(title='Precio'),
            xaxis_rangeslider_visible=False,
            uirevision=True,
            height=800
        )
        self.layout.add_candlestick(
            name=KLINE,
            row=1,
            col=1
        )
        self.layout.add_scatter(
            mode='lines',
            name=FILTER,
            line=dict(color=COLOR_FILTER),
            row=1,
            col=1
        )
        self.layout.add_scatter(
            mode='lines',
            name=SMI,
            line=dict(color=COLOR_OSCILATOR),
            row=2,
            col=1
        )
        self.layout.add_scatter(
            mode='lines',
            name=MA_SMI,
            line=dict(color=COLOR_MA),
            row=2,
            col=1
        )
        self.layout.add_scatter(
            mode='lines',
            name=CYCLER,
            line=dict(color=COLOR_OSCILATOR),
            row=3,
            col=1
        )
        self.layout.add_scatter(
            mode='lines',
            name=MA_CYCLER,
            line=dict(color=COLOR_MA),
            row=3,
            col=1
        )
        self.layout.add_scatter(
            mode='lines',
            name=TREND,
            line=dict(color=COLOR_TREND),
            row=1,
            col=1
        )
        
    def init_strategy_plots(self):
        self.layout.add_scatter(
            mode='lines',
            name=STOP,
            line=dict(color=COLOR_OSCILATOR),
            row=1,
            col=1
        )
        self.layout.add_scatter(
            mode='markers', 
            marker=MARKER_BEAR,
            name=ALERT_BEAR_SMI,
            row=2,
            col=1 
        )
        self.layout.add_scatter(
            mode='markers', 
            marker=MARKER_BULL,
            name=ALERT_BULL_SMI,
            row=2,
            col=1 
        )
        self.layout.add_scatter(
            mode='markers', 
            marker=MARKER_BEAR,
            name=ALERT_BEAR_CYCLER,
            row=3,
            col=1 
        )
        self.layout.add_scatter(
            mode='markers', 
            marker=MARKER_BULL,
            name=ALERT_BULL_CYCLER,
            row=3,
            col=1 
        )
        self.layout.add_scatter(
            mode='lines',
            name=ORDERS,
            line=dict(color=COLOR_OSCILATOR),
            row=4,
            col=1 
        )

    def update_ta_plots(self):
        index = self.all_kline_data.index
        self.layout.update_traces(
            x=index,
            open=self.all_kline_data['open'].values,
            high=self.all_kline_data['high'].values,
            low=self.all_kline_data['low'].values,
            close=self.all_kline_data['close'].values, 
            selector=dict(name=KLINE) 
        )
        self.layout.update_traces(
            x=index,
            y=self.price_hp,
            selector=dict(name=FILTER) 
        )
        self.layout.update_traces(
            x=index,
            y=self.smi, 
            selector=dict(name=SMI) 
        )
        self.layout.update_traces(
            x=index,
            y=self.smi_ma,
            selector=dict(name=MA_SMI) 
        )
        self.layout.update_traces(
            x=index,
            y=self.seasonal, 
            selector=dict(name=CYCLER) 
        )
        self.layout.update_traces(
            x=index,
            y=self.seasonal_ma, 
            selector=dict(name=MA_CYCLER) 
        )
        self.layout.update_traces(
            x=index,
            y=self.stl.trend, 
            selector=dict(name=TREND) 
        )
    def update_strategy_plots(self):
        self.layout.update_traces(
            x=self.stops.index,
            y=talib.EMA(self.stops, 4),
            selector=dict(name=STOP) 
        )
        self.layout.update_traces(
            x=self.ci_smi.index,
            y=self.smi[self.ci_smi.index],
            selector=dict(name=ALERT_BEAR_SMI)
        )
        self.layout.update_traces(
            x=self.co_smi.index,
            y=self.smi[self.co_smi.index],
            selector=dict(name=ALERT_BULL_SMI)
        )
        self.layout.update_traces(
            x=self.ci_cycle.index,
            y=self.seasonal[self.ci_cycle.index],
            selector=dict(name=ALERT_BEAR_CYCLER)
        )
        self.layout.update_traces(
            x=self.co_cycle.index,
            y=self.seasonal[self.co_cycle.index],
            selector=dict(name=ALERT_BULL_CYCLER)
        )
        self.layout.update_traces(
            x=self.orders.index,
            y=self.orders.status,
            selector=dict(name=ORDERS)
        )