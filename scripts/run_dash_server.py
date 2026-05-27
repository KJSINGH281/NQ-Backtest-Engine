#!/usr/bin/env python3
"""
Run interactive Dash server for live dashboard
Access at: http://localhost:8050
"""

from dash import Dash, html, dcc, Input, Output
import plotly.graph_objects as go
import pandas as pd
import json
from pathlib import Path
import argparse

def create_app(results_dir: str):
    app = Dash(__name__)
    
    app.layout = html.Div([
        html.H1("🎯 NQ Backtest Dashboard - Live", 
                style={'textAlign': 'center', 'color': '#667eea'}),
        
        dcc.Dropdown(
            id='strategy-dropdown',
            options=[{'label': f.stem, 'value': f.stem} 
                    for f in Path(results_dir).glob("*.json")],
            value=None,
            placeholder="Select a strategy...",
            style={'width': '50%', 'margin': '20px auto'}
        ),
        
        dcc.Graph(id='equity-curve'),
        dcc.Graph(id='metrics-chart'),
        
        html.Div(id='metrics-summary', 
                style={'margin': '20px', 'padding': '20px', 
                      'backgroundColor': '#f5f5f5', 'borderRadius': '10px'})
    ])
    
    @app.callback(
        [Output('equity-curve', 'figure'),
         Output('metrics-chart', 'figure'),
         Output('metrics-summary', 'children')],
        Input('strategy-dropdown', 'value')
    )
    def update_dashboard(selected_strategy):
        if not selected_strategy:
            return go.Figure(), go.Figure(), "Select a strategy to view results"
        
        # Load results
        result_file = Path(results_dir) / f"{selected_strategy}.json"
        with open(result_file) as f:
            data = json.load(f)
        
        # Create figures
        equity_fig = go.Figure()
        if 'equity_curve' in data:
            equity = pd.DataFrame(data['equity_curve'])
            equity_fig.add_trace(go.Scatter(x=equity['date'], y=equity['equity']))
            equity_fig.update_layout(title=f"Equity Curve: {selected_strategy}")
        
        metrics = data.get('results', data)
        metrics_fig = go.Figure(data=[
            go.Bar(
                x=['Net Profit', 'Max DD', 'Win Rate', 'Sharpe'],
                y=[metrics.get('net_profit_pct', 0),
                   -metrics.get('max_drawdown_pct', 0),
                   metrics.get('win_rate', 0) * 100,
                   metrics.get('sharpe_ratio', 0) * 50]
            )
        ])
        
        summary_html = html.Div([
            html.H3("Key Metrics"),
            html.P(f"Net Profit: {metrics.get('net_profit_pct', 0):.2f}%"),
            html.P(f"Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%"),
            html.P(f"Win Rate: {metrics.get('win_rate', 0)*100:.1f}%"),
            html.P(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}"),
            html.P(f"Total Trades: {metrics.get('total_trades', 0)}")
        ])
        
        return equity_fig, metrics_fig, summary_html
    
    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    
    args = parser.parse_args()
    
    app = create_app(args.results_dir)
    
    print(f"🚀 Starting Dash server at http://localhost:{args.port}")
    print(f"📊 Results directory: {args.results_dir}")
    print("Press CTRL+C to stop")
    
    app.run_server(host='0.0.0.0', port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
