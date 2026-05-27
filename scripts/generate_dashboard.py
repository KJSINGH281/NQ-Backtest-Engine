#!/usr/bin/env python3
"""
Generate interactive HTML dashboard for NQ backtest results
Compatible with Microsoft Edge & Google Chrome
"""

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import argparse
from datetime import datetime

def load_results(results_dir: str) -> list:
    """Load all JSON backtest results"""
    results = []
    for json_file in Path(results_dir).glob("*.json"):
        with open(json_file) as f:
            data = json.load(f)
            data['filename'] = json_file.stem
            results.append(data)
    return results

def create_equity_curve_fig(results: list) -> go.Figure:
    """Create equity curve comparison chart"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Equity Curve', 'Drawdown'),
        vertical_spacing=0.12,
        row_heights=[0.7, 0.3]
    )
    
    for result in results:
        strategy_name = result.get('strategy_name', result['filename'])
        
        # Equity curve
        if 'equity_curve' in result:
            equity = pd.DataFrame(result['equity_curve'])
            fig.add_trace(
                go.Scatter(x=equity['date'], y=equity['equity'], 
                          name=strategy_name, mode='lines'),
                row=1, col=1
            )
            
            # Drawdown
            if 'drawdown' in equity.columns:
                fig.add_trace(
                    go.Scatter(x=equity['date'], y=-equity['drawdown'],
                              name=f"{strategy_name} DD", mode='lines',
                              line=dict(color='red', width=1), showlegend=False),
                    row=2, col=1
                )
    
    fig.update_layout(
        height=800,
        title_text="NQ Futures Backtest Performance",
        hovermode='x unified',
        template='plotly_white'
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    
    return fig

def create_metrics_radar(results: list) -> go.Figure:
    """Create radar chart comparing key metrics"""
    fig = go.Figure()
    
    for result in results:
        strategy_name = result.get('strategy_name', result['filename'])
        metrics = result.get('results', result)
        
        # Normalize metrics to 0-100 scale for radar
        values = [
            metrics.get('win_rate', 0) * 100,
            metrics.get('profit_factor', 0) * 20,  # Scale PF (typical 1-3)
            metrics.get('sharpe_ratio', 0) * 30,   # Scale Sharpe (typical 0.5-2)
            max(0, 100 - metrics.get('max_drawdown_pct', 100) * 2),  # Invert DD
            min(100, metrics.get('total_trades', 0) / 10)  # Scale trades
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=['Win Rate', 'Profit Factor', 'Sharpe Ratio', 'Low Drawdown', 'Trade Count'],
            fill='toself',
            name=strategy_name
        ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title="Strategy Comparison Radar",
        height=600
    )
    
    return fig

def create_trade_distribution(results: list) -> go.Figure:
    """Create trade P&L distribution histogram"""
    fig = make_subplots(
        rows=1, cols=len(results),
        subplot_titles=[r.get('strategy_name', r['filename']) for r in results]
    )
    
    for idx, result in enumerate(results, 1):
        if 'trade_log' in result:
            trades = pd.DataFrame(result['trade_log'])
            pnl_col = 'PnL' if 'PnL' in trades.columns else 'pnl'
            
            fig.add_trace(
                go.Histogram(x=trades[pnl_col], nbinsx=30, 
                            name=f"{result['filename']} trades"),
                row=1, col=idx
            )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        title_text="Trade P&L Distribution"
    )
    
    return fig

def generate_summary_table(results: list) -> str:
    """Generate HTML table with key metrics"""
    html = """
    <div style="margin: 20px 0; overflow-x: auto;">
        <h2>Performance Summary</h2>
        <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif;">
            <thead>
                <tr style="background-color: #4CAF50; color: white;">
                    <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Strategy</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Net Profit %</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Max DD %</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Win Rate</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Profit Factor</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Sharpe</th>
                    <th style="padding: 12px; text-align: right; border: 1px solid #ddd;">Total Trades</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for result in results:
        metrics = result.get('results', result)
        strategy_name = result.get('strategy_name', result['filename'])
        
        # Color code profit/loss
        profit_pct = metrics.get('net_profit_pct', 0)
        profit_color = 'green' if profit_pct > 0 else 'red'
        
        html += f"""
            <tr style="background-color: {'#f2f2f2' if len(html) % 2 else 'white'};">
                <td style="padding: 10px; border: 1px solid #ddd;"><b>{strategy_name}</b></td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd; color: {profit_color};">
                    {profit_pct:.2f}%
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd;">
                    {metrics.get('max_drawdown_pct', 0):.2f}%
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd;">
                    {metrics.get('win_rate', 0)*100:.1f}%
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd;">
                    {metrics.get('profit_factor', 0):.2f}
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd;">
                    {metrics.get('sharpe_ratio', 0):.2f}
                </td>
                <td style="padding: 10px; text-align: right; border: 1px solid #ddd;">
                    {metrics.get('total_trades', 0)}
                </td>
            </tr>
        """
    
    html += """
            </tbody>
        </table>
    </div>
    """
    
    return html

def build_dashboard(results: list, output_path: str):
    """Build complete HTML dashboard"""
    
    # Create figures
    equity_fig = create_equity_curve_fig(results)
    radar_fig = create_metrics_radar(results)
    dist_fig = create_trade_distribution(results) if len(results) > 0 else None
    
    # Generate summary table
    summary_html = generate_summary_table(results)
    
    # Build HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NQ Backtest Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
            }}
            .chart-container {{
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .metric-value {{
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
                margin: 10px 0;
            }}
            .metric-label {{
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
            }}
            .footer {{
                text-align: center;
                color: #666;
                margin-top: 40px;
                padding: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 NQ Futures Backtest Dashboard</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
               Strategies Tested: {len(results)} | 
               Data: E-mini Nasdaq-100 (NQ)</p>
        </div>
        
        {summary_html}
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Best Strategy</div>
                <div class="metric-value">
                    {max(results, key=lambda x: x.get('results', x).get('net_profit_pct', 0)).get('strategy_name', 'N/A') if results else 'N/A'}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Highest Sharpe</div>
                <div class="metric-value">
                    {max(results, key=lambda x: x.get('results', x).get('sharpe_ratio', 0)).get('strategy_name', 'N/A') if results else 'N/A'}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Trades</div>
                <div class="metric-value">
                    {sum(r.get('results', r).get('total_trades', 0) for r in results):,}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Win Rate</div>
                <div class="metric-value">
                    {sum(r.get('results', r).get('win_rate', 0) for r in results) / len(results) * 100:.1f}%
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Equity Curve & Drawdown</h2>
            <div id="equity-chart"></div>
        </div>
        
        <div class="chart-container">
            <h2>Strategy Comparison Radar</h2>
            <div id="radar-chart"></div>
        </div>
        
        {f'<div class="chart-container"><h2>Trade Distribution</h2><div id="dist-chart"></div></div>' if dist_fig else ''}
        
        <div class="footer">
            <p><b>NQ Backtest Engine</b> | Powered by VectorBT + Plotly | 
               <a href="file://{Path.cwd()}/htmlcov/index.html" target="_blank">View Test Coverage</a></p>
        </div>
        
        <script>
            // Render equity curve
            var equityData = {json.dumps(equity_fig.to_dict(), default=str)};
            Plotly.newPlot('equity-chart', equityData.data, equityData.layout, {{responsive: true}});
            
            // Render radar chart
            var radarData = {json.dumps(radar_fig.to_dict(), default=str)};
            Plotly.newPlot('radar-chart', radarData.data, radarData.layout, {{responsive: true}});
            
            {f"var distData = {json.dumps(dist_fig.to_dict(), default=str)}; Plotly.newPlot('dist-chart', distData.data, distData.layout, {{responsive: true}});" if dist_fig else ''}
        </script>
    </body>
    </html>
    """
    
    # Write HTML
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html_content)
    print(f"✅ Dashboard saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate NQ backtest dashboard")
    parser.add_argument("--input-dir", default="results", help="Directory with JSON results")
    parser.add_argument("--output", default="dashboard/index.html", help="Output HTML path")
    parser.add_argument("--open-browser", action="store_true", help="Auto-open in browser")
    
    args = parser.parse_args()
    
    # Load results
    results = load_results(args.input_dir)
    print(f"📊 Loaded {len(results)} backtest results from {args.input_dir}")
    
    # Build dashboard
    build_dashboard(results, args.output)
    
    # Auto-open browser
    if args.open_browser:
        import webbrowser
        from pathlib import Path
        webbrowser.open(f"file://{Path(args.output).absolute()}")
        print("🌐 Dashboard opened in default browser")

if __name__ == "__main__":
    main()
