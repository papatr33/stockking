import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

def filter_date_range(df, start_date, end_date):
    start_date = pd.to_datetime(start_date) # Convert start_date to datetime
    end_date = pd.to_datetime(end_date) # Convert end_date to datetime
    filtered_df = df[(df.index >= start_date) & (df.index <= end_date)]
    return filtered_df

# Read the data
df = pd.read_csv('data.csv')
df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
df.set_index('Date', inplace=True)

# Ensure market cap columns are numeric and fill NaNs
mc_columns = [col for col in df.columns if '_MC' in col]
df[mc_columns] = df[mc_columns].apply(pd.to_numeric, errors='coerce').fillna(-1)

# Function to perform the backtest
def backtest_strategy(df, start_date, end_date):
    # Filter data based on date range
    df_filtered = filter_date_range(df, start_date, end_date)
    
    # Initialize variables
    initial_investment = 1000000
    current_position = None
    current_shares = 0
    cash = initial_investment
    nav = initial_investment
    trade_records = []
    
    # Initialize benchmark investments
    spy_initial_shares = initial_investment / df_filtered.iloc[0]['SPY']
    qqq_initial_shares = initial_investment / df_filtered.iloc[0]['QQQ']
    
    # Prepare the result dataframe
    result_list = []
    trade_logs = []
    
    # Iterate through each day
    for index, row in df_filtered.iterrows():
        # Identify the stock with the highest market cap
        highest_mc_stock = row[mc_columns].idxmax().replace('_MC', '')
        
        if current_position is None:
            # Initial purchase
            current_position = highest_mc_stock
            current_shares = cash / row[current_position]
            cost = row[current_position]
            cash = 0
            # record entry date
            entry_date = index.strftime('%Y/%m/%d')

            trade_logs.append(f"Date = {index.strftime('%Y/%m/%d')} Buy {highest_mc_stock} @ {row[current_position]} for notional = ${int(cost * current_shares)}\n")
        elif highest_mc_stock != current_position:
            # Sell current position
            cash = current_shares * row[current_position]
            trade_logs.append(f"Date = {index.strftime('%Y/%m/%d')} Sold {current_position} @ {row[current_position]} for notional = ${int(row[current_position] * current_shares)}\n")
            exit_date = index.strftime('%Y/%m/%d')
            pnl = int(current_shares * (row[current_position] - cost))
            trade_records.append([entry_date, exit_date, current_position, cost, row[current_position], pnl])
            # Buy new position
            entry_date = index.strftime('%Y/%m/%d')
            current_position = highest_mc_stock
            current_shares = cash / row[current_position]
            cost = row[current_position]
            cash = 0
            trade_logs.append(f"Date = {index.strftime('%Y/%m/%d')} Buy {highest_mc_stock} @ {row[current_position]} for notional = ${int(cost * current_shares)}\n")
        
        # Calculate daily PnL and NAV
        daily_pnl = current_shares * (row[current_position] - cost)
        nav = cash + (current_shares * row[current_position])
        
        # Calculate benchmark NAVs
        spy_nav = spy_initial_shares * row['SPY']
        qqq_nav = qqq_initial_shares * row['QQQ']
        
        # Append to result list
        result_list.append({
            'Date': index,
            'Position': current_position,
            'Cost': cost,
            'Daily PnL': daily_pnl,
            'Strategy_NAV': nav,  # Ensure the column name matches here
            'SPY_NAV': spy_nav,
            'QQQ_NAV': qqq_nav
        })
    
        trade_records_df = pd.DataFrame(trade_records, columns=['Entry Date', 'Exit Date', 'Ticker', 'Entry Price', 'Exit Price', 'PnL'])

    # Create result dataframe from the result list
    result_df = pd.DataFrame(result_list)
    result_df.set_index('Date', inplace=True)
    
    return result_df, trade_logs, trade_records_df

# Streamlit app layout
st.title('股王策略')

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input('Start Date', value=pd.to_datetime('2000-01-03'))
with col2:
    end_date = st.date_input('End Date', value=pd.to_datetime('2024-06-18'))  # Update to a reasonable default end date

if st.button('Run Backtest'):
    result_df, trade_logs, trade_records_df = backtest_strategy(df, start_date, end_date)

    
    # Create tabs
    tab1, tab2 = st.tabs(["NAV Graph", "Trade Logs"])
    
    with tab1:
        # Plot the NAV curves using Plotly
        fig = px.line(result_df.reset_index(), 
                      x='Date', 
                      y=['Strategy_NAV', 'SPY_NAV', 'QQQ_NAV'], 
                      labels={'value': 'NAV', 'variable': 'Portfolio'},
                      title='NAV Comparison: Strategy vs SPY vs QQQ')

        fig.update_layout(xaxis_title='Date', yaxis_title='NAV')
        st.plotly_chart(fig, use_container_width=True) 

        st.divider()

        st.header('Trade Records')

        st.dataframe(trade_records_df)
    
    with tab2:
        # Display trade logs
        for log in trade_logs:
            st.text(log)