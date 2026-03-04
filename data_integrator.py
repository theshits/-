import numpy as np
import pandas as pd
from scipy.spatial import KDTree
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIntegrator:
    def __init__(self, spatial_resolution: float = 0.1):
        self.spatial_resolution = spatial_resolution
        
    def create_spatial_grid(self, lat_range: Tuple[float, float], 
                           lon_range: Tuple[float, float]) -> Tuple[np.ndarray, np.ndarray]:
        lat_grid = np.arange(lat_range[0], lat_range[1] + self.spatial_resolution, 
                            self.spatial_resolution)
        lon_grid = np.arange(lon_range[0], lon_range[1] + self.spatial_resolution, 
                            self.spatial_resolution)
        
        lat_mesh, lon_mesh = np.meshgrid(lat_grid, lon_grid)
        
        return lat_mesh.flatten(), lon_mesh.flatten()
    
    def interpolate_to_grid(self, df: pd.DataFrame, lat_grid: np.ndarray, 
                           lon_grid: np.ndarray, value_col: str) -> np.ndarray:
        logger.info(f"Interpolating {value_col} to grid")
        
        if value_col not in df.columns:
            logger.warning(f"Column {value_col} not found in dataframe")
            return np.full(len(lat_grid), np.nan)
        
        points = df[['latitude', 'longitude']].values
        values = df[value_col].values
        
        tree = KDTree(points)
        
        grid_points = np.column_stack([lat_grid, lon_grid])
        
        distances, indices = tree.query(grid_points, k=5)
        
        interpolated_values = np.zeros(len(grid_points))
        
        for i in range(len(grid_points)):
            valid_mask = ~np.isnan(values[indices[i]])
            if np.sum(valid_mask) > 0:
                weights = 1.0 / (distances[i][valid_mask] + 1e-6)
                weights = weights / np.sum(weights)
                interpolated_values[i] = np.sum(values[indices[i][valid_mask]] * weights)
            else:
                interpolated_values[i] = np.nan
        
        return interpolated_values
    
    def temporal_match(self, df1: pd.DataFrame, df2: pd.DataFrame, 
                      time_col: str = 'time') -> pd.DataFrame:
        logger.info("Matching data temporally")
        
        if time_col not in df1.columns or time_col not in df2.columns:
            logger.warning("Time column not found in one or both dataframes")
            return df1
        
        df1_copy = df1.copy()
        df2_copy = df2.copy()
        
        df1_copy = df1_copy.sort_values(time_col)
        df2_copy = df2_copy.sort_values(time_col)
        
        merged = pd.merge_asof(df1_copy, df2_copy, on=time_col, 
                               by=['latitude', 'longitude'], 
                               direction='nearest', tolerance=pd.Timedelta('1D'))
        
        return merged
    
    def integrate_data(self, tropomi_df: pd.DataFrame, 
                       ground_df: pd.DataFrame, 
                       weather_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Integrating TROPOMI, ground station, and weather data")
        
        if tropomi_df.empty:
            logger.warning("TROPOMI data is empty")
            return pd.DataFrame()
        
        lat_min = tropomi_df['latitude'].min()
        lat_max = tropomi_df['latitude'].max()
        lon_min = tropomi_df['longitude'].min()
        lon_max = tropomi_df['longitude'].max()
        
        lat_grid, lon_grid = self.create_spatial_grid((lat_min, lat_max), (lon_min, lon_max))
        
        integrated_df = pd.DataFrame({
            'latitude': lat_grid,
            'longitude': lon_grid
        })
        
        if 'time' in tropomi_df.columns:
            unique_times = tropomi_df['time'].unique()
            integrated_dfs = []
            
            for time in unique_times:
                time_df = integrated_df.copy()
                time_df['time'] = time
                
                tropomi_time = tropomi_df[tropomi_df['time'] == time]
                
                for col in tropomi_time.columns:
                    if col.startswith('tropomi_') and col != 'tropomi_time':
                        time_df[col] = self.interpolate_to_grid(
                            tropomi_time, lat_grid, lon_grid, col
                        )
                
                if not ground_df.empty and 'time' in ground_df.columns:
                    ground_time = ground_df[
                        (ground_df['time'] - time).abs() <= pd.Timedelta('1D')
                    ]
                    
                    if 'ground_no2' in ground_time.columns:
                        time_df['ground_no2'] = self.interpolate_to_grid(
                            ground_time, lat_grid, lon_grid, 'ground_no2'
                        )
                
                integrated_dfs.append(time_df)
            
            integrated_df = pd.concat(integrated_dfs, ignore_index=True)
        
        if not weather_df.empty and 'time' in weather_df.columns:
            weather_cols = ['wind_speed', 'wind_direction', 'u_wind', 'v_wind', 
                           'temperature', 'humidity', 'pressure']
            
            for col in weather_cols:
                if col in weather_df.columns:
                    integrated_df[f'weather_{col}'] = np.nan
                    
                    for time in integrated_df['time'].unique():
                        time_mask = integrated_df['time'] == time
                        weather_time = weather_df[
                            (weather_df['time'] - time).abs() <= pd.Timedelta('1D')
                        ]
                        
                        if not weather_time.empty:
                            integrated_df.loc[time_mask, f'weather_{col}'] = \
                                self.interpolate_to_grid(weather_time, lat_grid, lon_grid, col)
        
        integrated_df = integrated_df.dropna(subset=['latitude', 'longitude'])
        
        logger.info(f"Integrated data: {len(integrated_df)} records")
        return integrated_df
    
    def create_node_features(self, integrated_df: pd.DataFrame) -> np.ndarray:
        logger.info("Creating node features")
        
        feature_cols = []
        
        tropomi_cols = [col for col in integrated_df.columns if col.startswith('tropomi_')]
        feature_cols.extend(tropomi_cols)
        
        weather_cols = [col for col in integrated_df.columns if col.startswith('weather_')]
        feature_cols.extend(weather_cols)
        
        feature_cols.extend(['latitude', 'longitude'])
        
        node_features = integrated_df[feature_cols].values
        
        node_features = np.nan_to_num(node_features, nan=0.0)
        
        return node_features
    
    def create_labels(self, integrated_df: pd.DataFrame) -> np.ndarray:
        logger.info("Creating labels")
        
        if 'ground_no2' in integrated_df.columns:
            labels = integrated_df['ground_no2'].values
            labels = np.nan_to_num(labels, nan=0.0)
            return labels
        else:
            logger.warning("ground_no2 column not found")
            return np.zeros(len(integrated_df))