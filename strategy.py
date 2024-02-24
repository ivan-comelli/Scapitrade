import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta
import pytz
import talib

##El reemplanteo es que pasa a ser planteado de calculo para historico a calculo en tiempo real, eso significa que debe de mantenerse sincronizado las ordenes con el precio. Parte fundamenta
#es aplicar la logica condicional sobre instancias cerradas para evitar falsas señales y tener que modificar las ordenes.
#la acciones de operativa se ejecutan sin problemas, el unico inconveniente de toda la modificacion es el control de riesgo que necesitava informacion historica y seguimiento en tiempo real.
#por eso en simular_estrategia se va colocar la logica de detectar cruces, de manera que se consulte por cada instancia los cruces y se verifique sus condiciones.

#EL ATR deberia provenir de afuera y el calculo de trailing stop de aca
utc3 = pytz.timezone('America/Buenos_Aires')
class MiEstrategia:
    def __init__(self, atr_period = 14, multiplier = 1.5, start_cursor = 16):
        self.cursor = None
        self.csmi = pd.Series()
        self.ccycle = pd.Series()
        self.crisk = pd.Series()
        self.orders = pd.DataFrame()
        self.risk = pd.Series()
        self.atr = pd.Series()
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.start_cursor = start_cursor

    def set_broker_action(self, short, long):
        self.go_to_short = short
        self.go_to_long = long

    def update_ta_data(self, all_kline_data, smi, smi_ma, seasonal, seasonal_ma):
        self.all_kline_data = all_kline_data
        self.smi = smi
        self.smi_ma = smi_ma
        self.cycle = seasonal
        self.cycle_ma = seasonal_ma
        if not self.cursor:
            self.cursor = self.all_kline_data.index[self.start_cursor]
                        
    def detectar_cruces(self):        
        before_cursor = self.all_kline_data.loc[:self.cursor].index[-2]
        scclose = self.all_kline_data.close.loc[before_cursor:self.cursor]
        scsmi = self.smi.loc[before_cursor:self.cursor]
        scsmi_ma = self.smi_ma.loc[before_cursor:self.cursor]
        sccycle = self.cycle.loc[before_cursor:self.cursor]
        sccycle_ma = self.cycle_ma.loc[before_cursor:self.cursor]
        scrisk = self.risk.loc[before_cursor:self.cursor]
        self.csmi[self.cursor] = None
        self.ccycle[self.cursor] = None
        self.crisk[self.cursor] = None
        if ta.cross(scsmi, scsmi_ma, above=True)[-1] == 1:
            self.csmi[self.cursor] = True
        elif ta.cross(scsmi, scsmi_ma, above=False)[-1] == 1:
            self.csmi[self.cursor] = False
        if ta.cross(sccycle, sccycle_ma, above=True)[-1] == 1:
            self.ccycle[self.cursor] = True
        elif ta.cross(sccycle, sccycle_ma, above=False)[-1] == 1:
            self.ccycle[self.cursor] = False
        if ta.cross(scrisk, scclose, above=True)[-1] == 1:
            self.crisk[self.cursor] = True
        elif ta.cross(scrisk, scclose, above=False)[-1] == 1:
            self.crisk[self.cursor] = False

    def simular_estrategia(self):
        pos = None
        status = None
        choch = None
        stop_point = len(self.all_kline_data)
        start_point = self.all_kline_data.index.get_loc(self.cursor)
        for count in range(start_point, stop_point):
            self.cursor = self.all_kline_data.index[count]
            self.step_stop(choch)
            if count > self.start_cursor+1:
                self.detectar_cruces()
                if self.csmi[self.cursor] is not None:
                    status = self.setStatus(swap=True, isBull=self.csmi[self.cursor], position = pos)
                    choch = self.csmi[self.cursor]
                elif self.ccycle[self.cursor] is not None:
                    status = self.setStatus(isBull=self.ccycle[self.cursor], position = pos)
                elif self.crisk[self.cursor] is not None:
                    if self.crisk[self.cursor] and choch:
                        status = self.setStatus(isBull=False, position = pos)
                    elif not self.crisk[self.cursor] and not choch:
                        status = self.setStatus(isBull=True, position = pos)    
                item = {
                    'index': self.cursor,
                    'close': self.all_kline_data.close.loc[self.cursor]
                }
                
                # Añadir el status al diccionario del item
                if status is None:
                    item['status'] = 0.5
                else:
                    item['status'] = int(status)
                if item['index'] in self.orders.index:
                    # Si el índice existe, actualizar los valores correspondientes
                    self.orders.loc[item['index']] = item
                else:
                    # Si el índice no existe, agregar una nueva fila al DataFrame
                    new_item_df = pd.DataFrame(item, index=[item['index']])
                    self.orders = pd.concat([self.orders, new_item_df])
                             
    def setStatus(self, swap = False, isBull = None, position=False):
        if isBull != None:
            if swap:
                if position:
                    self.call_to_action(pos = isBull)
                position = self.call_to_action(pos = isBull)
            else:
                if position:
                    if position != isBull:
                        self.call_to_action(pos = isBull)
                        position = None
                else:
                    position = self.call_to_action(pos = isBull)    
        return position          

    def step_stop(self, choch):
        idx = self.all_kline_data.index.get_loc(self.cursor)
        close = self.all_kline_data.close.iloc[idx - self.atr_period: idx].values
        high = self.all_kline_data.high.iloc[idx - self.atr_period: idx].values
        low = self.all_kline_data.low.iloc[idx - self.atr_period: idx].values
        self.atr[self.cursor] = talib.ATR(high, low, close, self.atr_period-1)[-1]
        atr_idx = self.atr.index.get_loc(self.cursor)
        src = self.all_kline_data.open.iloc[idx]
        if choch and atr_idx > 0:
            self.risk[self.cursor] = src - (self.atr[atr_idx - 1] * self.multiplier)
        elif not choch and atr_idx > 0:
            self.risk[self.cursor] = src + (self.atr[atr_idx - 1] * self.multiplier)
        else:
            self.risk[self.cursor] = src

    def call_to_action(self, pos = None):
        isSync = self.isSync()
        if isSync:
            if pos == True:
                self.go_to_long()
            elif pos == False:
                self.go_to_short()
        return pos

    def isSync(self):
        tiempo_actual = datetime.fromtimestamp(datetime.now().timestamp(), tz=pytz.utc).astimezone(utc3)
        diferencia_tiempo = tiempo_actual - self.cursor
        if diferencia_tiempo.total_seconds() < 60:
            return True
        return False
    
    def calculate_profit(self):
        #Ya tiene incorporado el choch en el df solo hay que comparar si cambia con el anterior
        resultado = 0
        acum = 0
        last_price = 0
        last_status = None
        change = -1
        for data in range(len(self.orders)):
            item = self.orders.iloc[data]
            if change != item.status:
                if last_status == 1:
                    acum += (item.close/last_price - 1)* 100
                elif last_status == 0:
                    acum +=  (1 - item.close/last_price) * 100
                if item.status != 0.5 and item.status != last_status:
                    last_status = item.status
                    resultado += acum
                    acum = 0
                change = item.status
                last_price = item.close
        return resultado

    def get_report_backtesting(self):
        #Este se queda porque deberia de ser varios los test que se pueden mostrar, no es solo profit
        self.simular_estrategia()
        result = self.calculate_profit()
        return result
