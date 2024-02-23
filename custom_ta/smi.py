import talib

def emaEma(source, length):
    ema1 = talib.EMA(source, timeperiod=length)
    ema2 = talib.EMA(ema1, timeperiod=length)
    return ema2

def SMI(src, lengthK, lengthD, lengthMA):
    highestHigh = talib.MAX(src, timeperiod=lengthK)
    lowestLow = talib.MIN(src, timeperiod=lengthK)
    highestLowestRange = highestHigh - lowestLow
    relativeRange = src - (highestHigh + lowestLow) / 2
    smi = 200 * (emaEma(relativeRange, lengthD) / emaEma(highestLowestRange, lengthD))
    ma = talib.EMA(smi, lengthMA)
    return [smi, ma]