import pandas_ta as ta
import pandas as pd

class MiEstrategia:
    def __init__(self):
        self.ci_smi = []
        self.co_smi = []
        self.ci_cycle = []
        self.co_cycle = []
        self.position = None
        self.tendencia = False
        self.orders = []

    def update_ta_data(self, all_kline_data, smi, smi_ma, seasonal, seasonal_ma, lower_atr, high_atr):
        self.all_kline_data = all_kline_data
        self.smi = smi.fillna(value = 0)
        self.smi_ma = smi_ma.fillna(value = 0.1)
        self.cycle = seasonal
        self.cycle_ma = seasonal_ma
        self.lower_atr = lower_atr
        self.high_atr = high_atr

    def detectar_cruces(self):
        co_smi = ta.cross(self.smi, self.smi_ma, above=True)[1:]
        ci_smi = ta.cross(self.smi, self.smi_ma, above=False)[1:]
        for idx, val in co_smi.items():
            if val == 0:
                co_smi.drop(idx, inplace=True)
        self.co_smi = co_smi.index.tolist()
        
        for idx, val in ci_smi.items():
            if val == 0:
                ci_smi.drop(idx, inplace=True)
        self.ci_smi = ci_smi.index.tolist()

        co_cycle = ta.cross(self.cycle, self.cycle_ma, above=True)
        ci_cycle = ta.cross(self.cycle, self.cycle_ma, above=False)
        
        for idx, val in co_cycle.items():
            if val == 0:
                co_cycle.drop(idx, inplace=True)
        self.co_cycle = co_cycle.index.tolist()
        
        for idx, val in ci_cycle.items():
            if val == 0:
                ci_cycle.drop(idx, inplace=True)
        self.ci_cycle = ci_cycle.index.tolist()

    def simular_estrategia(self):
        status = None
        data = []
        for count in range(len(self.all_kline_data)):
            idx = self.all_kline_data.index[count]  
            #Hay una condicion que por ejemplo abre smi y cierra en el mismo instante el cycle
            if idx in self.ci_smi:
                status = self.setStatus(swap=True, isBull=False)
            elif idx in self.co_smi:
                status = self.setStatus(swap=True, isBull=True)
            elif idx in self.ci_cycle:
                status = self.setStatus(isBull=False)
            elif idx in self.co_cycle:
                status = self.setStatus(isBull=True)
            if status == None:
                item = {
                    'index': idx,
                    'close': self.all_kline_data.close.loc[idx],
                    'status': 0.5
                }
            else:
                item = {
                    'index': idx,
                    'close': self.all_kline_data.close.loc[idx],
                    'status': int(status)
                }
            data.append(item)
        self.orders = pd.DataFrame(data).set_index('index')
            
    def setStatus(self, swap = False, isBull = None):
        if isBull != None:
            if swap:
                if self.position:
                    self.action(pos = isBull)
                self.position = self.action(pos = isBull)
            else:
                if self.position:
                    if self.position != isBull:
                        self.action(pos = isBull)
                        self.position = None
                else:
                    self.position = self.action(pos = isBull)    
        return self.position          

    def action(self, pos = None):
        #Tal vez si pudiera saber que es una operacion que esta a tiempo de ser operada, y esta habilitado el procedimiento se ejecutan las ordenes
        if pos == True:
            return True
        elif pos == False:
            return False
        return None

    def set_orders(self):
        return True

    def calculate_profit(self):
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
        self.detectar_cruces()
        self.simular_estrategia()
        result = self.calculate_profit()
        return result
