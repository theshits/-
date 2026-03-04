import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data, HeteroData
from scipy.spatial import KDTree
from typing import Tuple, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherTransportGraph:
    def __init__(self, k_neighbors: int = 8, max_distance: float = 50.0, 
                 wind_weight: bool = True):
        self.k_neighbors = k_neighbors
        self.max_distance = max_distance
        self.wind_weight = wind_weight
        
    def haversine_distance(self, lat1: np.ndarray, lon1: np.ndarray, 
                          lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
        R = 6371.0
        
        lat1_rad = np.radians(lat1)
        lon1_rad = np.radians(lon1)
        lat2_rad = np.radians(lat2)
        lon2_rad = np.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        
        distance = R * c
        
        return distance
    
    def calculate_wind_transport_weight(self, lat1: np.ndarray, lon1: np.ndarray,
                                      lat2: np.ndarray, lon2: np.ndarray,
                                      u_wind: np.ndarray, v_wind: np.ndarray) -> np.ndarray:
        dx = np.radians(lon2 - lon1) * 6371.0 * np.cos(np.radians((lat1 + lat2) / 2))
        dy = np.radians(lat2 - lat1) * 6371.0
        
        distance = np.sqrt(dx ** 2 + dy ** 2)
        
        wind_speed = np.sqrt(u_wind ** 2 + v_wind ** 2)
        
        if np.sum(wind_speed) == 0:
            return np.ones_like(distance) / (distance + 1e-6)
        
        dot_product = (u_wind * dx + v_wind * dy) / (wind_speed * distance + 1e-6)
        
        transport_weight = wind_speed * np.maximum(0, dot_product)
        
        distance_weight = 1.0 / (distance + 1e-6)
        
        combined_weight = transport_weight * distance_weight
        
        return combined_weight
    
    def build_knn_edges(self, lat: np.ndarray, lon: np.ndarray, 
                       weather_df: Optional[pd.DataFrame] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        logger.info(f"Building KNN edges with k={self.k_neighbors}")
        
        points = np.column_stack([lat, lon])
        tree = KDTree(points)
        
        distances, indices = tree.query(points, k=self.k_neighbors + 1)
        
        edge_indices = []
        edge_weights = []
        
        for i in range(len(points)):
            for j in range(1, self.k_neighbors + 1):
                neighbor_idx = indices[i, j]
                distance = distances[i, j]
                
                if distance <= self.max_distance:
                    edge_indices.append([i, neighbor_idx])
                    
                    if self.wind_weight and weather_df is not None:
                        lat1, lon1 = lat[i], lon[i]
                        lat2, lon2 = lat[neighbor_idx], lon[neighbor_idx]
                        
                        u_wind = weather_df['weather_u_wind'].iloc[i]
                        v_wind = weather_df['weather_v_wind'].iloc[i]
                        
                        weight = self.calculate_wind_transport_weight(
                            np.array([lat1]), np.array([lon1]),
                            np.array([lat2]), np.array([lon2]),
                            np.array([u_wind]), np.array([v_wind])
                        )[0]
                    else:
                        weight = 1.0 / (distance + 1e-6)
                    
                    edge_weights.append(weight)
        
        edge_indices = np.array(edge_indices)
        edge_weights = np.array(edge_weights)
        
        logger.info(f"Created {len(edge_indices)} edges")
        return edge_indices, edge_weights
    
    def build_temporal_edges(self, times: np.ndarray, node_indices: np.ndarray,
                            temporal_window: int = 24) -> Tuple[np.ndarray, np.ndarray]:
        logger.info(f"Building temporal edges with window={temporal_window} hours")
        
        times_sorted = np.sort(times)
        time_diffs = np.diff(times_sorted) / np.timedelta64(1, 'h')
        
        edge_indices = []
        edge_weights = []
        
        for i in range(len(times_sorted) - 1):
            if time_diffs[i] <= temporal_window:
                edge_indices.append([node_indices[i], node_indices[i + 1]])
                weight = 1.0 / (time_diffs[i] + 1e-6)
                edge_weights.append(weight)
        
        edge_indices = np.array(edge_indices)
        edge_weights = np.array(edge_weights)
        
        logger.info(f"Created {len(edge_indices)} temporal edges")
        return edge_indices, edge_weights
    
    def create_graph_data(self, node_features: np.ndarray, labels: np.ndarray,
                          lat: np.ndarray, lon: np.ndarray,
                          weather_df: Optional[pd.DataFrame] = None,
                          times: Optional[np.ndarray] = None,
                          temporal_window: Optional[int] = None) -> Data:
        logger.info("Creating PyG graph data")
        
        edge_index, edge_weight = self.build_knn_edges(lat, lon, weather_df)
        
        if times is not None and temporal_window is not None:
            temporal_edge_index, temporal_edge_weight = self.build_temporal_edges(
                times, np.arange(len(lat)), temporal_window
            )
            
            edge_index = np.vstack([edge_index, temporal_edge_index])
            edge_weight = np.concatenate([edge_weight, temporal_edge_weight])
        
        edge_index = torch.tensor(edge_index.T, dtype=torch.long)
        edge_weight = torch.tensor(edge_weight, dtype=torch.float)
        
        x = torch.tensor(node_features, dtype=torch.float)
        y = torch.tensor(labels, dtype=torch.float)
        
        pos = torch.tensor(np.column_stack([lat, lon]), dtype=torch.float)
        
        data = Data(x=x, edge_index=edge_index, edge_attr=edge_weight, 
                   y=y, pos=pos)
        
        logger.info(f"Graph created: {data.num_nodes} nodes, {data.num_edges} edges")
        return data
    
    def create_temporal_graphs(self, integrated_df: pd.DataFrame,
                              node_features: np.ndarray,
                              labels: np.ndarray) -> List[Data]:
        logger.info("Creating temporal sequence of graphs")
        
        graphs = []
        
        unique_times = sorted(integrated_df['time'].unique())
        
        for time in unique_times:
            time_mask = integrated_df['time'] == time
            time_df = integrated_df[time_mask]
            
            time_features = node_features[time_mask]
            time_labels = labels[time_mask]
            time_lat = time_df['latitude'].values
            time_lon = time_df['longitude'].values
            
            graph = self.create_graph_data(
                time_features, time_labels, time_lat, time_lon, time_df
            )
            
            graphs.append(graph)
        
        logger.info(f"Created {len(graphs)} temporal graphs")
        return graphs