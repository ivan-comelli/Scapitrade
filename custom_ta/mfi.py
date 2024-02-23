def calcular_mfi(close, high, low, volume, periodo=14):
    # Calcula el precio típico
    typical_price = (close + high + low) / 3.0
    
    # Calcula el money flow
    money_flow = typical_price * volume
    
    # Calcula los cambios de precio
    price_diff = np.diff(typical_price)
    price_diff = np.concatenate(([0], price_diff))
    
    # Inicializa las listas de flujo de dinero positivo y negativo
    positive_flow = np.zeros_like(price_diff)
    negative_flow = np.zeros_like(price_diff)
    
    # Calcula el flujo de dinero positivo y negativo
    positive_flow[price_diff > 0] = money_flow[price_diff > 0]
    negative_flow[price_diff < 0] = money_flow[price_diff < 0]
    
    # Calcula el money ratio
    money_ratio = talib.SUM(positive_flow, timeperiod=periodo) / \
                  talib.SUM(negative_flow, timeperiod=periodo)
    
    # Calcula el MFI
    mfi = 100 - (100 / (1 + money_ratio))
    
    return mfi