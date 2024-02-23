import talib

def ATR(high_prices_array, low_prices_array, close_prices_array, period=14, multiplicador= 2):
    atr_values = talib.ATR(high_prices_array, low_prices_array, close_prices_array, timeperiod=period)
    upper_bands = high_prices_array + multiplicador * atr_values
    lower_bands = low_prices_array - multiplicador * atr_values
    return [upper_bands, lower_bands]