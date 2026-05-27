#!/usr/bin/env python3
"""
Download or generate sample NQ futures data for testing
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from datetime import datetime, timedelta

def generate_sample_nq_data(start_date: str, end_date: str, output_path: str):
    """Generate realistic synthetic NQ 1-minute data"""
    print(f"📈 Generating synthetic NQ data from {start_date} to {end_date}...")
    
    # Create date range (RTH only: 9:30 AM - 4:00 PM ET)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    times = pd.date_range(start='09:30', end='16:00', freq='1T').time
    
    data = []
    base_price = 15000  # Starting NQ price
    
    for date in dates:
        daily_open = base_price + np.random.uniform(-100, 100)
        daily_volatility = np.random.uniform(50, 150)
        
        for time in times:
            # Random walk with slight upward bias
            change = np.random.normal(0.1, 2.5)
            base_price += change
            
            open_price = base_price
            close_price = open_price + np.random.uniform(-5, 5)
            high_price = max(open_price, close_price) + abs(np.random.normal(0, 3))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, 3))
            volume = int(np.random.exponential(1000))
            
            data.append({
                'datetime': f"{date.date()} {time}",
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"✅ Generated {len(df)} bars → {output_path}")
    return df

def download_from_databento(start_date: str, end_date: str, output_path: str):
    """Download real NQ data from Databento (requires API key)"""
    try:
        import databento as db
        
        print("📡 Downloading real NQ data from Databento...")
        
        # Get API key from environment
        db_client = db.Historical(key=None)  # Will use DATABENTO_API_KEY env var
        
        data = db_client.timeseries.get(
            dataset="GLBX.MDP3",
            schema="ohlcv-1m",
            symbols=["NQ.M2024", "NQ.M2025", "NQ.M2026"],
            start=start_date,
            end=end_date,
        )
        
        df = data.df.reset_index()
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df.to_csv(output_path, index=False)
        
        print(f"✅ Downloaded {len(df)} bars → {output_path}")
        return df
        
    except ImportError:
        print("⚠️  Databento not installed. Generating synthetic data instead...")
        return generate_sample_nq_data(start_date, end_date, output_path)
    except Exception as e:
        print(f"⚠️  Databento error: {e}. Generating synthetic data...")
        return generate_sample_nq_data(start_date, end_date, output_path)

def main():
    parser = argparse.ArgumentParser(description="Download NQ futures data")
    parser.add_argument("--symbol", default="NQ", help="Futures symbol")
    parser.add_argument("--start", default="2024-01-01", help="Start date")
    parser.add_argument("--end", default="2026-05-28", help="End date")
    parser.add_argument("--output", default="data/nq_test_1m.csv", help="Output CSV path")
    parser.add_argument("--source", choices=["databento", "synthetic"], default="synthetic",
                       help="Data source")
    
    args = parser.parse_args()
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    if args.source == "databento":
        df = download_from_databento(args.start, args.end, args.output)
    else:
        df = generate_sample_nq_data(args.start, args.end, args.output)
    
    # Display stats
    print(f"\n📊 Data Statistics:")
    print(f"   Total bars: {len(df):,}")
    print(f"   Date range: {df['datetime'].min()} → {df['datetime'].max()}")
    print(f"   Price range: ${df['low'].min():,.2f} - ${df['high'].max():,.2f}")
    print(f"   Avg volume: {df['volume'].mean():,.0f}")

if __name__ == "__main__":
    main()
