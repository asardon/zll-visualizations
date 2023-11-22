import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import helpers
import matplotlib.pyplot as plt
import traceback

CMAP = 'plasma'

def parse_ltvs(ltv_selection):
    ltvs = [int(ltv.replace('%',''))/100 for ltv in ltv_selection]
    ltvs.sort()
    return ltvs

def parse_tenors(tenor_selection):
    tenors = [int(tenor.replace('d','')) for tenor in tenor_selection]
    tenors.sort()
    return tenors

def get_user_input():
    solve_for = st.sidebar.selectbox('Solve for', options=('APR', 'Upfront Fee', 'Strike'))
    vol = st.sidebar.slider('Volatility (p.a.)', .01, 5., .5)
    r = st.sidebar.slider('Interest rate (p.a.)', .0, .1, .0)

    ltv_selection = st.sidebar.multiselect('LTVs', ('99%', '98%', '97%', '96%', '95%', '94%', '93%', '92%', '91%', '90%', '85%', '80%', '75%', '70%', '65%', '60%', '55%', '50%', '45%', '40%', '35%', '30%', '25%', '20%', '15%', '10%'), default=('70%', '60%', '50%'))
    tenor_selection = st.sidebar.multiselect('Tenors', ('1d', '2d', '3d', '4d', '5d', '6d', '7d', '10d', '20d', '30d', '40d', '50d', '60d', '70d', '80d', '90d', '100d', '110d', '120d', '130d', '140d', '150d', '160d', '170d', '180d'), default=('30d', '60d', '90d'))

    loan_token_decimals = st.sidebar.number_input('Loan Token Decimals', min_value=0, max_value=18, value=6, help="Note: this info is only needed when using the JSON output!")
    spot = st.sidebar.number_input('Spot Price ($)', min_value=.01, max_value=100000., value=2000., help="Note: this info is only needed when using the JSON output!")

    components.html(
        """
    <script>
    const elements = window.parent.document.querySelectorAll('.stNumberInput div[data-baseweb="input"] > div')
    console.log(elements)
    elements[1].style.backgroundColor = 'red'
    </script>
    """,
        height=0,
        width=0,
    )

    return {'solve_for': solve_for, 'ltv_selection': ltv_selection, 'tenor_selection': tenor_selection, 'spot': spot, 'vol': vol, 'r': r, 'loan_token_decimals': loan_token_decimals}

def get_heatmap(func, title, ltv_selection_parsed, tenor_selection_parsed, vol, r):
    fig, ax = plt.subplots()
    heatmap_res = []

    for ltv in ltv_selection_parsed:
        tmp = []
        for tenor in tenor_selection_parsed:
            res = func(ltv, tenor/365, 100, vol, r)
            tmp.append(res)
        heatmap_res.append(tmp)
    heatmap_res = np.array(heatmap_res, dtype=float)
    heatmap_res = np.ma.array(heatmap_res, mask=np.isnan(heatmap_res))

    cmap = plt.cm.get_cmap(CMAP)
    cmap.set_bad('white',1.)
    ax.imshow(heatmap_res, interpolation='nearest', cmap=CMAP)

    normColors = plt.cm.colors.Normalize(vmin=np.min(heatmap_res), vmax=np.max(heatmap_res))
    for i in range(len(ltv_selection_parsed)):
        for j in range(len(tenor_selection_parsed)):
            bg = cmap(normColors(heatmap_res[i][j]))
            v = 0 if (bg[0] + bg[1] + bg[2]) / 3 > 0.5 else 1
            c = (v, v, v, 1.)
            if title == 'Strike':
                text = '{:.2f}%\n({:+.2f}%)'.format(heatmap_res[i][j]*100, (heatmap_res[i][j]/ltv_selection_parsed[i]-1)*100)
            else:
                text = '{:.2f}%'.format(heatmap_res[i][j]*100)
            ax.text(j, i, text,
                    ha='center', va='center', color=c, fontsize='x-small')
    
    # Show all ticks and label them with the respective list entries
    ax.set_xticks(np.arange(len(tenor_selection_parsed)), labels=['{:.0f}d'.format(x) for x in tenor_selection_parsed])
    ax.set_yticks(np.arange(len(ltv_selection_parsed)), labels=['{:.0f}%'.format(x*100) for x in ltv_selection_parsed])
    ax.invert_yaxis()

    plt.title(title)
    plt.xlabel('Tenor')
    plt.ylabel('LTV')

        
    return heatmap_res, fig

def get_delta_heatmap(heatmap_res, is_apr, ltv_selection_parsed, tenor_selection_parsed, vol, r):
    fig, ax = plt.subplots()
    delta_heatmap_res = []

    for i, ltv in enumerate(ltv_selection_parsed):
        tmp = []
        for j, tenor in enumerate(tenor_selection_parsed):
            dt = tenor/365.
            s = 100
            k = s*ltv*(1+heatmap_res[i][j]*dt) if is_apr else s*ltv
            alpha = 1 if is_apr else 1 - heatmap_res[i][j]
            res = 1 - alpha * helpers.getDelta(s, k, vol, dt, r, 0)
            tmp.append(res)
        delta_heatmap_res.append(tmp)
    delta_heatmap_res = np.array(delta_heatmap_res, dtype=float)
    delta_heatmap_res = np.ma.array(delta_heatmap_res, mask=np.isnan(delta_heatmap_res))

    cmap = plt.cm.get_cmap(CMAP)
    cmap.set_bad('white',1.)
    ax.imshow(delta_heatmap_res, interpolation='nearest', cmap=CMAP)

    normColors = plt.cm.colors.Normalize(vmin=np.min(delta_heatmap_res), vmax=np.max(delta_heatmap_res))
    for i in range(len(ltv_selection_parsed)):
        for j in range(len(tenor_selection_parsed)):
            bg = cmap(normColors(delta_heatmap_res[i][j]))
            v = 0 if (bg[0] + bg[1] + bg[2]) / 3 > 0.5 else 1
            c = (v, v, v, 1.)
            ax.text(j, i, '{:.2f}'.format(delta_heatmap_res[i][j]),
                    ha='center', va='center', color=c, fontsize='x-small')
    
    # Show all ticks and label them with the respective list entries
    ax.set_xticks(np.arange(len(tenor_selection_parsed)), labels=['{:.0f}d'.format(x) for x in tenor_selection_parsed])
    ax.set_yticks(np.arange(len(ltv_selection_parsed)), labels=['{:.0f}%'.format(x*100) for x in ltv_selection_parsed])
    ax.invert_yaxis()

    plt.title('Delta Risk')
    plt.xlabel('Tenor')
    plt.ylabel('LTV')

    return delta_heatmap_res, fig

def get_raw_quote_tuples(heatmap_res, ltv_selection_parsed, tenor_selection_parsed, spot, loan_token_decimals, with_oracle, is_apr):
    quoteTuples = []
    for i, ltv in enumerate(ltv_selection_parsed):
        for j, tenor in enumerate(tenor_selection_parsed):
            try:
                apr = heatmap_res[i][j] if is_apr else 0
                fee = heatmap_res[i][j] if not is_apr else 0
                quoteTuple = helpers.generateQuoteTuple(ltv, spot, tenor/365, apr, fee, loan_token_decimals, with_oracle)
                quoteTuples.append(quoteTuple)
            except Exception:
                traceback.print_exc()
    return quoteTuples

st.title('Zero-Liquidation Loan Pricer')
st.sidebar.header('Input assumptions:')

user_input = get_user_input()
ltv_selection_parsed = parse_ltvs(user_input['ltv_selection'])
tenor_selection_parsed = parse_tenors(user_input['tenor_selection'])

if(user_input['solve_for'] == 'APR'):
    heatmap_res, heatmap_fig = get_heatmap(helpers.getFairApr, 'APR Heatmap', ltv_selection_parsed, tenor_selection_parsed, user_input['vol'], user_input['r'])
elif(user_input['solve_for'] == 'Upfront Fee'):
    heatmap_res, heatmap_fig = get_heatmap(helpers.getFairFee, 'Upfront Fee Heatmap', ltv_selection_parsed, tenor_selection_parsed, user_input['vol'], user_input['r'])
else:
    heatmap_res, heatmap_fig = get_heatmap(helpers.getFairStrike, 'Strike', ltv_selection_parsed, tenor_selection_parsed, user_input['vol'], user_input['r'])
raw_quote_tuples = get_raw_quote_tuples(heatmap_res, ltv_selection_parsed, tenor_selection_parsed, user_input['spot'], user_input['loan_token_decimals'], False, user_input['solve_for'] == 'APR')

st.write(heatmap_fig)

_, delta_heatmap_fig = get_delta_heatmap(heatmap_res, user_input['solve_for'] == 'APR' or user_input['solve_for'] == 'Strike', ltv_selection_parsed, tenor_selection_parsed, user_input['vol'], user_input['r'])
st.write(delta_heatmap_fig)

st.subheader('JSON Raw Quote Tuples', anchor=None, help=None)
st.json(raw_quote_tuples, expanded=False)