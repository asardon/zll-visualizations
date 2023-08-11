import streamlit as st
import pandas as pd
import numpy as np
import helpers
import matplotlib.pyplot as plt
import traceback

CMAP = 'plasma'
LTVs = [.3, .4, .5, .6, .7, .8]
TENORS = [30, 60, 90, 120, 150] # in days

def get_user_input():
    solve_for = st.sidebar.selectbox('Solve for', options=('APR', 'Upfront Fee'))
    vol = st.sidebar.slider('Volatility (p.a.)', .01, 1.4, .5)
    r = st.sidebar.slider('Interest rate (p.a.)', .0, .1, .0)
    spot = st.sidebar.number_input('Spot Price ($)', min_value=.01, max_value=100000., value=2000.)
    loan_token_decimals = st.sidebar.number_input('Loan Token Decimals', min_value=0, max_value=18, value=6)
    coll_token_decimals = st.sidebar.number_input('Coll. Token Decimals', min_value=0, max_value=18, value=18)
    return {'solve_for': solve_for, 'spot': spot, 'vol': vol, 'r': r, 'loan_token_decimals': loan_token_decimals, 'coll_token_decimals': coll_token_decimals}

def get_heatmap(func, title, vol, r):
    fig, ax = plt.subplots()
    heatmap_res = []

    for ltv in LTVs:
        tmp = []
        for tenor in TENORS:
            res = func(ltv, tenor/365, 100, vol, r)
            tmp.append(res)
        heatmap_res.append(tmp)
    heatmap_res = np.array(heatmap_res, dtype=float)
    heatmap_res = np.ma.array(heatmap_res, mask=np.isnan(heatmap_res))

    cmap = plt.cm.get_cmap(CMAP)
    cmap.set_bad('white',1.)
    ax.imshow(heatmap_res, interpolation='nearest', cmap=CMAP)

    normColors = plt.cm.colors.Normalize(vmin=np.min(heatmap_res), vmax=np.max(heatmap_res))
    for i in range(len(LTVs)):
        for j in range(len(TENORS)):
            bg = cmap(normColors(heatmap_res[i][j]))
            v = 0 if (bg[0] + bg[1] + bg[2]) / 3 > 0.5 else 1
            c = (v, v, v, 1.)
            ax.text(j, i, '{:.2f}%'.format(heatmap_res[i][j]*100),
                    ha='center', va='center', color=c, fontsize='x-small')
    
    # Show all ticks and label them with the respective list entries
    ax.set_xticks(np.arange(len(TENORS)), labels=['{:.0f}d'.format(x) for x in TENORS])
    ax.set_yticks(np.arange(len(LTVs)), labels=['{:.0f}%'.format(x*100) for x in LTVs])
    ax.invert_yaxis()

    plt.title(title)
    plt.xlabel('Tenor')
    plt.ylabel('LTV')

        
    return heatmap_res, fig

def get_delta_heatmap(apr_heatmap_res, vol, r):
    fig, ax = plt.subplots()
    heatmap_res = []

    for i, ltv in enumerate(LTVs):
        tmp = []
        for j, tenor in enumerate(TENORS):
            dt = tenor/365.
            s = 100
            k = s*ltv*(1+apr_heatmap_res[i][j]*dt)
            res = 1 - helpers.getDelta(s, k, vol, dt, r, 0)
            print(tenor, ltv, s, k, dt, res)
            tmp.append(res)
        heatmap_res.append(tmp)
    heatmap_res = np.array(heatmap_res, dtype=float)
    heatmap_res = np.ma.array(heatmap_res, mask=np.isnan(heatmap_res))

    cmap = plt.cm.get_cmap(CMAP)
    cmap.set_bad('white',1.)
    ax.imshow(heatmap_res, interpolation='nearest', cmap=CMAP)

    normColors = plt.cm.colors.Normalize(vmin=np.min(heatmap_res), vmax=np.max(heatmap_res))
    for i in range(len(LTVs)):
        for j in range(len(TENORS)):
            bg = cmap(normColors(heatmap_res[i][j]))
            v = 0 if (bg[0] + bg[1] + bg[2]) / 3 > 0.5 else 1
            c = (v, v, v, 1.)
            ax.text(j, i, '{:.2f}'.format(heatmap_res[i][j]),
                    ha='center', va='center', color=c, fontsize='x-small')
    
    # Show all ticks and label them with the respective list entries
    ax.set_xticks(np.arange(len(TENORS)), labels=['{:.0f}d'.format(x) for x in TENORS])
    ax.set_yticks(np.arange(len(LTVs)), labels=['{:.0f}%'.format(x*100) for x in LTVs])
    ax.invert_yaxis()

    plt.title('Delta Risk')
    plt.xlabel('Tenor')
    plt.ylabel('LTV')

    return heatmap_res, fig

def get_raw_quote_tuples(heatmap_res, spot, loan_token_decimals, coll_token_decimals, with_oracle, is_apr):
    quoteTuples = []
    for i, ltv in enumerate(LTVs):
        for j, tenor in enumerate(TENORS):
            try:
                apr = heatmap_res[i][j] if is_apr else 0
                fee = heatmap_res[i][j] if not is_apr else 0
                quoteTuple = helpers.generateQuoteTuple(ltv, spot, tenor/365, apr, fee, loan_token_decimals, coll_token_decimals, with_oracle)
                quoteTuples.append(quoteTuple)
            except Exception:
                traceback.print_exc()
    return quoteTuples

st.title('Zero-Liquidation Loan Pricer')
st.sidebar.header('Input assumptions:')

user_input = get_user_input()

if(user_input['solve_for'] == 'APR'):
    heatmap_res, heatmap_fig = get_heatmap(helpers.getFairApr, 'APR Heatmap', user_input['vol'], user_input['r'])
else:
    heatmap_res, heatmap_fig = get_heatmap(helpers.getFairFee, 'Upfront Fee Heatmap', user_input['vol'], user_input['r'])
raw_quote_tuples = get_raw_quote_tuples(heatmap_res, user_input['spot'], user_input['loan_token_decimals'], user_input['coll_token_decimals'], False, user_input['solve_for'])

st.write(heatmap_fig)
st.subheader('JSON Raw Quote Tuples', anchor=None, help=None)
st.json(raw_quote_tuples, expanded=False)

if(user_input['solve_for'] == 'APR'):
    _, delta_heatmap_fig = get_delta_heatmap(heatmap_res, user_input['vol'], user_input['r'])
    st.write(delta_heatmap_fig)
