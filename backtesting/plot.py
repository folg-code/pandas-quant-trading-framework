import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import os


def plot_equity(trades_df):
    """
    Rysuje krzywą kapitału na podstawie kolumny 'capital' i 'timestamp'.
    """
    if 'capital' not in trades_df.columns:
        raise ValueError("Brakuje kolumny 'capital' – oblicz ją najpierw (np. przez compute_equity()).")

    plt.figure(figsize=(12, 5))
    plt.plot(trades_df['exit_time'], trades_df['capital'], label='Equity Curve', color='blue')
    plt.title("Equity Curve")
    plt.xlabel("time")
    plt.ylabel("Capital")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()




def add_zone(fig, row, df, label, fillcolor, font_color):
    x0 = df.loc[row['idxx'], 'time'] if 'time' in df.columns else row['idxx']
    x1 = (
        df.loc[row['validate_till'], 'time']
        if pd.notna(row['validate_till']) and 'time' in df.columns
        else (row['validate_till'] if pd.notna(row['validate_till']) else df.iloc[-1]['time'])
    )

    fig.add_shape(
        type='rect',
        x0=x0,
        x1=x1,
        y0=row['low_boundary'],
        y1=row['high_boundary'],
        fillcolor=fillcolor,
        line=dict(width=0),
        layer='below'
    )
    fig.add_annotation(
        x=x0,
        y=row['high_boundary'],
        text=label,
        showarrow=False,
        yshift=10,
        font=dict(color=font_color),
        bgcolor="white",
        opacity=0.8
    )

def add_trade_marker(fig, x, y, tag, position_size, pnl_usd, price, marker_type, color, symbol, showlegend=False, exit_reason=None):
    hovertext = (
        f"Enter Tag: {tag.get('entry_tag', '')}<br>" +
        f"Exit Tag: {tag.get('exit_tag', '')}<br>" +
        f"position_size: {position_size:.5f} <br>" +
        f"Profit: {pnl_usd:.5f} <br>" +
        f"Price: {price:.5f}<br>" +
        (f"Exit Reason: {exit_reason}<br>" if exit_reason else "") +
        f"Time: {x}<extra></extra>"
    )

    fig.add_trace(go.Scatter(
        x=[x],
        y=[y],
        mode='markers',
        name=marker_type,
        showlegend=showlegend,
        marker=dict(color=color, symbol=symbol, size=10),
        hovertemplate=hovertext
    ))


def plot_trades_with_indicators(df, trades, bullish_zones=None, bearish_zones=None, extra_series=None, bool_series=None, save_path=None):


    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.02, row_heights=[0.9, 0.1])

    fig.add_trace(go.Candlestick(x=df['time'],
                                open=df['open'],
                                high=df['high'],
                                low=df['low'],
                                close=df['close'],
                                name='candlestick'), row=1, col=1)

    shown_legend = {"Entry": False, "custom_SL": False, "custom_TP": False, "manual_exit": False, "TP1": False}


    for _, trade in trades.iterrows():
        print()
        add_trade_marker(
            fig=fig,
            x=trade['entry_time'],
            y=trade['entry_price'],
            tag=trade,
            position_size=trade['position_size'],
            pnl_usd=trade['pnl_usd'],
            price=trade['entry_price'],
            marker_type='Entry',
            color='black',
            symbol='circle',
            showlegend=not shown_legend["Entry"]
        )
        shown_legend["Entry"] = True

        if pd.notna(trade.get('tp1_time')) and pd.notna(trade.get('tp1_price')):
            fig.add_trace(go.Scatter(
                x=[trade['entry_time'], trade['tp1_time']],
                y=[trade['entry_price'], trade['tp1_price']],
                mode='lines',
                line=dict(color='gray', width=1.5, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))
            fig.add_trace(go.Scatter(
                x=[trade['tp1_time'], trade['exit_time']],
                y=[trade['tp1_price'], trade['exit_price']],
                mode='lines',
                line=dict(color='gray', width=1.5, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))

            add_trade_marker(
                fig=fig,
                x=trade['tp1_time'],
                y=trade['tp1_price'],
                tag=trade,
                position_size=trade['position_size'],
                pnl_usd=trade['tp1_pnl'],
                price=trade['tp1_price'],
                marker_type='TP1',
                color='blue',
                symbol='square',
                showlegend=not shown_legend['TP1'],
                exit_reason=trade['tp1_exit_reason'] if trade['tp1_exit_reason'] is not None else None
            )
            shown_legend['TP1'] = True
        else:
            fig.add_trace(go.Scatter(
                x=[trade['entry_time'], trade['exit_time']],
                y=[trade['entry_price'], trade['exit_price']],
                mode='lines',
                line=dict(color='gray', width=1.5, dash='dot'),
                showlegend=False,
                hoverinfo='skip'
            ))

        exit_tag = trade.get('exit_tag', 'manual_exit')
        if 'TP' in exit_tag:
            color, symbol, legend_key = 'blue', 'triangle-down', 'custom_TP'
        elif 'SL' in exit_tag:
            color, symbol, legend_key = 'orange', 'triangle-up', 'custom_SL'
        else:
            color, symbol, legend_key = 'gray', 'x', 'manual_exit'

        add_trade_marker(
            fig=fig,
            x=trade['exit_time'],
            y=trade['exit_price'],
            tag=trade,
            position_size=trade['position_size'],
            pnl_usd=trade['pnl_usd'],
            price=trade['exit_price'],
            marker_type=legend_key,
            color=color,
            symbol=symbol,
            showlegend=not shown_legend[legend_key]
        )
        shown_legend[legend_key] = True

    if extra_series:
        for extra in extra_series:
            if len(extra) == 4:
                name, series, color, dash = extra
                line_style = dict(color=color, dash=dash)
            else:
                name, series = extra[:2]
                line_style = dict()
            fig.add_trace(go.Scatter(
                x=df['time'],
                y=series,
                mode='lines',
                name=name,
                line=line_style
            ))

    for zones, default_color in zip([bullish_zones, bearish_zones],
                                     ['rgba(255, 152, 0, 0.4)', 'rgba(33, 150, 243, 0.4)']):
        if zones is not None:
            for zone in zones:
                if len(zone) == 3:
                    zone_name, zone_df, fillcolor = zone
                else:
                    zone_name, zone_df = zone
                    fillcolor = default_color
                if zone_df.empty:
                    continue
                for i, (_, row) in enumerate(zone_df.iterrows()):
                    x0 = row['time']
                    x1 = row['validate_till_time'] if pd.notna(row['validate_till_time']) else df['time'].iloc[-1]
                    y0 = row['low_boundary']
                    y1 = row['high_boundary']
                    fig.add_trace(go.Scatter(
                        x=[x0, x1, x1, x0, x0],
                        y=[y0, y0, y1, y1, y0],
                        fill='toself',
                        fillcolor=fillcolor,
                        line=dict(width=0),
                        mode='lines',
                        name=zone_name if i == 0 else None,
                        showlegend=(i == 0),
                        opacity=0.4,
                        hoverinfo='skip'
                    ), row=1, col=1)

    if bool_series:
        for name, bool_series, color in bool_series:
            if bool_series is None or not isinstance(bool_series, pd.Series):
                continue
            bar_y = bool_series.astype(int)
            fig.add_trace(go.Bar(
                x=df['time'],
                y=bar_y,
                name=name,
                marker_color=color,
                opacity=0.6,
            ), row=2, col=1)

    # Linie pomocnicze z pivotów (HH, LL, EQH, EQL)
    pivot_sources = [
        ('pivot_15', {
            3: {'color': 'red',   'label': 'HH'},
            4: {'color': 'green', 'label': 'LL'},
            5: {'color': 'red',   'label': 'LH'},
            6: {'color': 'green', 'label': 'HL'},
        })
    ]

    low_rolling_min = df['low'].rolling(16).min()
    high_rolling_max = df['high'].rolling(16).max()

    for pivot_col, pivot_map in pivot_sources:
        if pivot_col not in df.columns:
            continue

        for i, row in df.reset_index(drop=True).iterrows():
            pivot_val = row.get(pivot_col)
            if pivot_val not in pivot_map:
                continue

            info = pivot_map[pivot_val]
            start_idx = max(i - 15, 0)
            end_idx = min(start_idx + 30, len(df) - 1)
            x_values = [df['time'].iloc[start_idx], df['time'].iloc[end_idx]]

            # Ustal wartość Y na podstawie rodzaju pivotu
            y_value = None
            if pivot_val == 3:
                y_value = row.get('HH_50')
            elif pivot_val == 4:
                y_value = row.get('LL_50')
            elif pivot_val == 5:
                y_value = row.get('LH_50')
            elif pivot_val == 6:
                y_value = row.get('HL_50')

            if pd.isna(y_value):
                continue

            fig.add_trace(go.Scatter(
                x=x_values,
                y=[y_value, y_value],
                mode='lines+text',
                line=dict(color=info['color'], width=1.5, dash='dash'),
                name=info['label'],
                text=[info['label'], None],
                textposition='top right',
                showlegend=False,
                hoverinfo='text'
            ), row=1, col=1)
    else:
        print("no pivot")

    fig.update_layout(
        title='Wykres z transakcjami i strefami',
        xaxis_title='Czas',
        yaxis_title='Cena',
        xaxis_rangeslider_visible=False,
        height=800
    )

    if save_path:
        folder = os.path.dirname(save_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        try:
            fig.write_image(save_path)
            print(f"Wykres zapisany do {save_path}")
        except Exception as e:
            print(f"Nie udało się zapisać PNG: {e}")
            html_path = save_path.rsplit('.', 1)[0] + ".html"
            fig.write_html(html_path)
            print(f"Wykres zapisany jako HTML do {html_path}")
    else:
        fig.show(renderer="browser")
