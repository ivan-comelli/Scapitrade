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
    def __init__(self, atr_period = 4, multiplier = 0.3, start_cursor = 16):
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
        self.status = None
        self.choch = None
        self.lastProfit = None

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
        before_cursor = self.all_kline_data.loc[:self.cursor].index[-3]
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
        #podemos medir una vela atrasada para evitar falsas señales
        stop_point = len(self.all_kline_data)-1
        start_point = self.all_kline_data.index.get_loc(self.cursor)+1
        for count in range(start_point, stop_point):
            self.cursor = self.all_kline_data.index[count]
            self.step_stop()
            if count > self.start_cursor+1:
                self.detectar_cruces()
                if self.csmi[self.cursor] is not None:
                    self.setStatus(swap=True, isBull=self.csmi[self.cursor])
                    self.choch = self.csmi[self.cursor]
                """elif self.ccycle[self.cursor] is not None:
                    self.setStatus(isBull=self.ccycle[self.cursor])
                elif self.crisk[self.cursor] is not None:
                    if self.crisk[self.cursor] and self.choch:
                        self.setStatus(isBull=False)
                    elif not self.crisk[self.cursor] and not self.choch:
                        self.setStatus(isBull=True)"""  
                item = {
                    'index': self.cursor,
                    'close': self.all_kline_data.close.loc[self.cursor]
                }
                #Falta la condicion de revertir las falsas señales. Aunque nose si es un caso de uso que deberia pasar
                # Añadir el status al diccionario del item
                if self.status is None:
                    item['status'] = 0.5
                else:
                    item['status'] = int(self.status)
                if item['index'] in self.orders.index:
                    # Si el índice existe, actualizar los valores correspondientes
                    self.orders.loc[item['index']] = item
                else:
                    # Si el índice no existe, agregar una nueva fila al DataFrame
                    new_item_df = pd.DataFrame(item, index=[item['index']])
                    self.orders = pd.concat([self.orders, new_item_df])
            profit, quantity=self.calculate_profit()
            if profit != self.lastProfit:
                self.lastProfit = profit
                print(self.cursor, " | Ganancias: ", profit, " x ", quantity, " Total: ", profit-(quantity * 0.05 * 2))
            
            
                            
    def setStatus(self, swap = False, isBull = None):
        if isBull != None:
            if swap:
                if self.status:
                    self.call_to_action(pos = isBull)
                self.status = self.call_to_action(pos = isBull)
            else:
                if self.status != None and self.status != isBull:
                    self.call_to_action(pos = isBull)
                    self.status = None
                elif self.choch == isBull:
                    self.status = self.call_to_action(pos = isBull)    

    def step_stop(self):
        idx = self.all_kline_data.index.get_loc(self.cursor)
        close = self.all_kline_data.close.iloc[idx - self.atr_period: idx].values
        high = self.all_kline_data.high.iloc[idx - self.atr_period: idx].values
        low = self.all_kline_data.low.iloc[idx - self.atr_period: idx].values
        self.atr[self.cursor] = talib.ATR(high, low, close, self.atr_period-1)[-1]
        atr_idx = self.atr.index.get_loc(self.cursor)
        src = self.all_kline_data.open.iloc[idx]
        if self.choch and atr_idx > 0:
            self.risk[self.cursor] = src - (self.atr[atr_idx - 1] * self.multiplier)
        elif not self.choch and atr_idx > 0:
            self.risk[self.cursor] = src + (self.atr[atr_idx - 1] * self.multiplier)
        else:
            self.risk[self.cursor] = src

    def call_to_action(self, pos = None):
        isSync = self.isSync()
        if isSync:
            if pos == True:
                print("LONG")
                self.go_to_long()
            elif pos == False:
                print("SHORT")
                self.go_to_short()
        return pos

    def isSync(self):
        tiempo_actual = datetime.fromtimestamp(datetime.now().timestamp(), tz=pytz.utc).astimezone(utc3)
        diferencia_tiempo = tiempo_actual - self.cursor
        if diferencia_tiempo.total_seconds() < 60:
            return True
        return False
    
    def calculate_profit(self):
        resultado = 0
        acum = 0
        last_price = 0
        last_status = None
        change = -1
        quantity= 0
        for data in range(len(self.orders)):
            item = self.orders.iloc[data]
            if change != item.status:
                quantity = quantity + 1
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
        return resultado, quantity

