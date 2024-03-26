import pandas as pd
import pandas_ta as ta
import numpy as np
import scipy.stats as stats


def vsa_indicator(data: pd.DataFrame, norm_lookback: int = 168):
    # Norm lookback should be fairly large

    atr = ta.atr(data['high'], data['low'], data['close'], norm_lookback)
    vol_med = data['volume'].rolling(norm_lookback).median()

    data['norm_range'] = (data['high'] - data['low']) / atr 
    data['norm_volume'] = data['volume'] / vol_med 

    norm_vol = data['norm_volume'].to_numpy()
    norm_range = data['norm_range'].to_numpy()

    range_dev = np.zeros(len(data))
    range_dev[:] = np.nan

    for i in range(norm_lookback * 2, len(data)):
        window = data.iloc[i - norm_lookback + 1: i+ 1]
        slope, intercept, r_val,_,_ = stats.linregress(window['norm_volume'], window['norm_range'])

        if slope <= 0.0 or r_val < 0.2:
            range_dev[i] = 0.0
            continue
       
        pred_range = intercept + slope * norm_vol[i]
        range_dev[i] = norm_range[i] - pred_range
        
    return pd.Series(range_dev, index=data.index)

