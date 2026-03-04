import numpy as np
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_data():
    logger.info("Creating sample data for testing...")
    
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    (data_dir / 'tropomi').mkdir(exist_ok=True)
    (data_dir / 'ground').mkdir(exist_ok=True)
    (data_dir / 'weather').mkdir(exist_ok=True)
    
    lat_range = (30.0, 40.0)
    lon_range = (110.0, 120.0)
    
    np.random.seed(42)
    
    num_grid_points = 100
    lats = np.random.uniform(lat_range[0], lat_range[1], num_grid_points)
    lons = np.random.uniform(lon_range[0], lon_range[1], num_grid_points)
    
    dates = pd.date_range('2024-01-01', '2024-01-31', freq='D')
    
    logger.info("Creating TROPOMI data...")
    tropomi_data = []
    for date in dates:
        for i in range(num_grid_points):
            tropomi_data.append({
                'time': date,
                'latitude': lats[i],
                'longitude': lons[i],
                'tropomi_nitrogendioxide_tropospheric_column': np.random.uniform(1e14, 5e15),
                'qa_value': np.random.uniform(0.5, 1.0)
            })
    
    tropomi_df = pd.DataFrame(tropomi_data)
    tropomi_df.to_csv(data_dir / 'tropomi' / 'sample_tropomi.csv', index=False)
    logger.info(f"TROPOMI data saved to {data_dir / 'tropomi' / 'sample_tropomi.csv'}")
    
    logger.info("Creating ground station data...")
    ground_data = []
    for date in dates:
        for i in range(num_grid_points):
            ground_data.append({
                'time': date,
                'latitude': lats[i],
                'longitude': lons[i],
                'ground_no2': np.random.uniform(10, 100)
            })
    
    ground_df = pd.DataFrame(ground_data)
    ground_df.to_csv(data_dir / 'ground' / 'sample_ground.csv', index=False)
    logger.info(f"Ground station data saved to {data_dir / 'ground' / 'sample_ground.csv'}")
    
    logger.info("Creating weather station data...")
    weather_data = []
    for date in dates:
        for i in range(num_grid_points):
            wind_speed = np.random.uniform(0, 10)
            wind_dir = np.random.uniform(0, 360)
            
            weather_data.append({
                'time': date,
                'latitude': lats[i],
                'longitude': lons[i],
                'wind_speed': wind_speed,
                'wind_direction': wind_dir,
                'temperature': np.random.uniform(-10, 30),
                'humidity': np.random.uniform(30, 90),
                'pressure': np.random.uniform(980, 1020)
            })
    
    weather_df = pd.DataFrame(weather_data)
    weather_df.to_csv(data_dir / 'weather' / 'sample_weather.csv', index=False)
    logger.info(f"Weather station data saved to {data_dir / 'weather' / 'sample_weather.csv'}")
    
    logger.info("Sample data created successfully!")
    logger.info(f"TROPOMI: {len(tropomi_df)} records")
    logger.info(f"Ground: {len(ground_df)} records")
    logger.info(f"Weather: {len(weather_df)} records")


if __name__ == '__main__':
    create_sample_data()