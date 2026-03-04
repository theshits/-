import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroundStationProcessor:
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        
    def load_csv(self, file_path: str) -> pd.DataFrame:
        logger.info(f"Loading ground station data from {file_path}")
        df = pd.read_csv(file_path)
        return df
    
    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Preprocessing ground station data")
        
        df = df.dropna(subset=['latitude', 'longitude'])
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        elif 'datetime' in df.columns:
            df['time'] = pd.to_datetime(df['datetime'])
        elif 'date' in df.columns and 'hour' in df.columns:
            df['time'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
        
        no2_cols = [col for col in df.columns if 'no2' in col.lower() or 'NO2' in col]
        if no2_cols:
            df['ground_no2'] = df[no2_cols[0]]
        
        return df
    
    def resample_temporal(self, df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
        logger.info(f"Resampling data to {freq} frequency")
        
        if 'time' not in df.columns:
            return df
        
        df = df.set_index('time')
        
        agg_dict = {'ground_no2': 'mean'}
        
        for col in df.columns:
            if col not in ['time', 'latitude', 'longitude', 'ground_no2']:
                if df[col].dtype in ['float64', 'int64']:
                    agg_dict[col] = 'mean'
        
        df_resampled = df.groupby(['latitude', 'longitude']).resample(freq).agg(agg_dict)
        df_resampled = df_resampled.reset_index()
        
        return df_resampled
    
    def process(self, file_path: str, resample_freq: Optional[str] = None) -> pd.DataFrame:
        df = self.load_csv(file_path)
        df = self.preprocess(df)
        
        if resample_freq:
            df = self.resample_temporal(df, resample_freq)
        
        logger.info(f"Processed ground station data: {len(df)} records")
        return df
    
    def process_directory(self, resample_freq: Optional[str] = None) -> pd.DataFrame:
        all_data = []
        
        for file_path in self.data_path.glob("*.csv"):
            df = self.process(str(file_path), resample_freq)
            all_data.append(df)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Combined ground station data: {len(combined_df)} records")
            return combined_df
        else:
            logger.warning("No ground station data files found")
            return pd.DataFrame()


class WeatherStationProcessor:
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        
    def load_csv(self, file_path: str) -> pd.DataFrame:
        logger.info(f"Loading weather station data from {file_path}")
        df = pd.read_csv(file_path)
        return df
    
    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Preprocessing weather station data")
        
        df = df.dropna(subset=['latitude', 'longitude'])
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        elif 'datetime' in df.columns:
            df['time'] = pd.to_datetime(df['datetime'])
        elif 'date' in df.columns and 'hour' in df.columns:
            df['time'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
        
        wind_cols = [col for col in df.columns if 'wind' in col.lower() or 'ws' in col.lower()]
        if wind_cols:
            df['wind_speed'] = df[wind_cols[0]]
        
        wind_dir_cols = [col for col in df.columns if 'dir' in col.lower() or 'wd' in col.lower()]
        if wind_dir_cols:
            df['wind_direction'] = df[wind_dir_cols[0]]
        
        temp_cols = [col for col in df.columns if 'temp' in col.lower() or 't2m' in col.lower()]
        if temp_cols:
            df['temperature'] = df[temp_cols[0]]
        
        humidity_cols = [col for col in df.columns if 'humid' in col.lower() or 'rh' in col.lower()]
        if humidity_cols:
            df['humidity'] = df[humidity_cols[0]]
        
        pressure_cols = [col for col in df.columns if 'press' in col.lower() or 'ps' in col.lower()]
        if pressure_cols:
            df['pressure'] = df[pressure_cols[0]]
        
        return df
    
    def calculate_wind_vector(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Calculating wind vector components")
        
        if 'wind_speed' in df.columns and 'wind_direction' in df.columns:
            df['u_wind'] = df['wind_speed'] * np.cos(np.radians(df['wind_direction']))
            df['v_wind'] = df['wind_speed'] * np.sin(np.radians(df['wind_direction']))
        
        return df
    
    def resample_temporal(self, df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
        logger.info(f"Resampling data to {freq} frequency")
        
        if 'time' not in df.columns:
            return df
        
        df = df.set_index('time')
        
        agg_dict = {}
        
        for col in df.columns:
            if col not in ['time', 'latitude', 'longitude']:
                if df[col].dtype in ['float64', 'int64']:
                    if col in ['wind_direction']:
                        agg_dict[col] = lambda x: np.arctan2(np.mean(np.sin(np.radians(x))), 
                                                             np.mean(np.cos(np.radians(x)))) * 180 / np.pi % 360
                    else:
                        agg_dict[col] = 'mean'
        
        df_resampled = df.groupby(['latitude', 'longitude']).resample(freq).agg(agg_dict)
        df_resampled = df_resampled.reset_index()
        
        return df_resampled
    
    def process(self, file_path: str, resample_freq: Optional[str] = None) -> pd.DataFrame:
        df = self.load_csv(file_path)
        df = self.preprocess(df)
        df = self.calculate_wind_vector(df)
        
        if resample_freq:
            df = self.resample_temporal(df, resample_freq)
        
        logger.info(f"Processed weather station data: {len(df)} records")
        return df
    
    def process_directory(self, resample_freq: Optional[str] = None) -> pd.DataFrame:
        all_data = []
        
        for file_path in self.data_path.glob("*.csv"):
            df = self.process(str(file_path), resample_freq)
            all_data.append(df)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Combined weather station data: {len(combined_df)} records")
            return combined_df
        else:
            logger.warning("No weather station data files found")
            return pd.DataFrame()