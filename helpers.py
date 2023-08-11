import numpy as np
from scipy.stats import norm
from scipy import optimize

def getD1(S, K, vol, dt, r, q):
    return (np.log(S / K) + (r - q + vol**2 / 2) * dt) / \
        (vol * np.sqrt(dt))

def getDelta(S, K, vol, dt, r, q):
    return norm.cdf(getD1(S, K, vol, dt, r, q))

def getCallPrice(spotPrice, strikePrice, vol, dt, riskFreeRate, q=0):
    if dt <= 0:
        return max([0, spotPrice - strikePrice])
    if strikePrice <= 0:
        return spotPrice
    d1 = getD1(spotPrice, strikePrice, vol, dt, riskFreeRate, q)
    d2 = d1 - vol * np.sqrt(dt)
    value = np.exp(-q * dt) * spotPrice * norm.cdf(d1) - strikePrice * \
        np.exp(-riskFreeRate * dt) * norm.cdf(d2)
    return value

def getFairApr(ltv, loanTenorInYears, spotPrice, vol, riskFreeRate, q=0):
    def minFunc(strike):
        y = spotPrice*ltv
        callPrice = getCallPrice(spotPrice, strike, vol, loanTenorInYears, riskFreeRate, q)
        z = spotPrice - callPrice - y
        z = z * 100 if z < 10 else z # scale up for small prices
        return z**2

    step_size = 0.1  # 10% step size
    upper_bound = spotPrice*10
    lower_bound = .0000001

    # Generate initial guesses
    initStrikeGuesses_increasing = np.arange(spotPrice, upper_bound, spotPrice*step_size)
    initStrikeGuesses_decreasing = np.arange(spotPrice, lower_bound, -spotPrice*step_size)
    initStrikeGuesses = np.concatenate([initStrikeGuesses_decreasing, initStrikeGuesses_increasing])

    strikeBnds = (lower_bound, None)

    for initStrikeGuess in initStrikeGuesses:
        res = optimize.minimize(
            minFunc,
            args=(),
            x0=[initStrikeGuess],
            bounds=[strikeBnds])
        if res["success"] and res["fun"] < 0.001:
            y = ltv*spotPrice
            strike = res['x'][0]
            apr = (strike/y-1)/loanTenorInYears
            return apr
    return None

def getFairFee(ltv, loanTenorInYears, spotPrice, vol, riskFreeRate, q=0):
    def minFunc(fee):
        y = spotPrice*ltv
        callPrice = getCallPrice(spotPrice, y/(1-fee), vol, loanTenorInYears, riskFreeRate, q)
        z = (1-fee)*(spotPrice - callPrice) - (y - fee*spotPrice)
        z = z * 100 if z < 10 else z # scale up z for small prices
        return z**2
    
    maxFee = .1
    middleFee = maxFee / 2
    feeInterval = middleFee / 5
    
    # Create a list of guesses starting from the middle of the range and adding guesses in alternating directions
    initFeeGuesses = [middleFee + i * feeInterval * (-1) ** i for i in range(20)]
    
    for initFeeGuess in initFeeGuesses:
        feeBnds = (.0, maxFee)
        res = optimize.minimize(
            minFunc,
            args=(),
            x0=[initFeeGuess],
            bounds=[feeBnds])
            
        if res["success"] and res["fun"] < 0.001:
            fee = res['x'][0]
            return fee
            
    return None

def generateQuoteTuple(ltv, spotPrice, tenorInYears, apr, upfrontFee, loanTokenDecimals, collTokenDecimals, withOracle=False):            
    if withOracle:
        loanPerCollUnitOrLtv = str(int(ltv * 10 ** 18))
    else:
        loanPerCollUnitOrLtv = str(int(ltv*spotPrice * 10 ** loanTokenDecimals))
    interestRatePctInBase = str(int(apr * tenorInYears* 10 ** 18))
    upfrontFeePctInBase = str(int(upfrontFee * 10 ** collTokenDecimals))
    tenor = str(int(tenorInYears * 60 * 60 * 24 * 365))
            
    return ({"loanPerCollUnitOrLtv": loanPerCollUnitOrLtv, "interestRatePctInBase": interestRatePctInBase, "upfrontFeePctInBase": upfrontFeePctInBase, "tenor": tenor})
