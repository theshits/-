import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv,  EdgeConv, global_mean_pool, global_max_pool
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherTransportGNN(nn.Module):
    def __init__(self, in_channels: int, hidden_dim: int = 128, 
                 num_layers: int = 3, dropout: float = 0.3, 
                 num_heads: int = 4, out_channels: int = 1):
        super(WeatherTransportGNN, self).__init__()
        
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.num_heads = num_heads
        
        self.input_proj = nn.Linear(in_channels, hidden_dim)
        
        self.gat_layers = nn.ModuleList()
        self.gcn_layers = nn.ModuleList()
        
        for i in range(num_layers):
            self.gat_layers.append(
                GATConv(hidden_dim, hidden_dim // num_heads, 
                       heads=num_heads, dropout=dropout, edge_dim=1)
            )
            self.gcn_layers.append(
                GCNConv(hidden_dim, hidden_dim)
            )
        
        self.batch_norms = nn.ModuleList([
            nn.BatchNorm1d(hidden_dim) for _ in range(num_layers)
        ])
        
        self.fusion_layers = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        self.output_layer = nn.Linear(hidden_dim // 2, out_channels)
        
        self._init_weights()
        
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x, edge_index, edge_attr=None, batch=None):
        x = self.input_proj(x)
        x = F.relu(x)
        
        gat_out = x
        gcn_out = x
        
        for i in range(self.num_layers):
            gat_out = self.gat_layers[i](gat_out, edge_index, edge_attr)
            gat_out = self.batch_norms[i](gat_out)
            gat_out = F.relu(gat_out)
            gat_out = F.dropout(gat_out, p=self.dropout, training=self.training)
            
            gcn_out = self.gcn_layers[i](gcn_out, edge_index, edge_attr)
            gcn_out = F.relu(gcn_out)
            gcn_out = F.dropout(gcn_out, p=self.dropout, training=self.training)
        
        fused = torch.cat([gat_out, gcn_out], dim=-1)
        
        fused = self.fusion_layers(fused)
        
        out = self.output_layer(fused)
        
        return out.squeeze(-1)


class EdgeWeightedGNN(nn.Module):
    def __init__(self, in_channels: int, hidden_dim: int = 128,
                 num_layers: int = 3, dropout: float = 0.3,
                 out_channels: int = 1):
        super(EdgeWeightedGNN, self).__init__()
        
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        
        self.input_proj = nn.Linear(in_channels, hidden_dim)
        
        self.edge_convs = nn.ModuleList()
        for i in range(num_layers):
            self.edge_convs.append(
                EdgeConv(nn=nn.Sequential(
                    nn.Linear(hidden_dim * 2, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, hidden_dim)
                ))
            )
        
        self.batch_norms = nn.ModuleList([
            nn.BatchNorm1d(hidden_dim) for _ in range(num_layers)
        ])
        
        self.output_layers = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, out_channels)
        )
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x, edge_index, edge_attr=None, batch=None):
        x = self.input_proj(x)
        x = F.relu(x)
        
        for i in range(self.num_layers):
            x = self.edge_convs[i](x, edge_index)
            x = self.batch_norms[i](x)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        
        out = self.output_layers(x)
        
        return out.squeeze(-1)


class SpatialTemporalGNN(nn.Module):
    def __init__(self, in_channels: int, hidden_dim: int = 128,
                 num_layers: int = 3, dropout: float = 0.3,
                 num_heads: int = 4, out_channels: int = 1):
        super(SpatialTemporalGNN, self).__init__()
        
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        
        self.input_proj = nn.Linear(in_channels, hidden_dim)
        
        self.spatial_gnn = WeatherTransportGNN(
            hidden_dim, hidden_dim, num_layers // 2, dropout, num_heads, hidden_dim
        )
        
        self.temporal_gnn = WeatherTransportGNN(
            hidden_dim, hidden_dim, num_layers // 2, dropout, num_heads, hidden_dim
        )
        
        self.fusion = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out_channels)
        )
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x, spatial_edge_index, temporal_edge_index=None,
                edge_attr=None, batch=None):
        x = self.input_proj(x)
        x = F.relu(x)
        
        spatial_out = self.spatial_gnn(x, spatial_edge_index, edge_attr, batch)
        
        if temporal_edge_index is not None:
            temporal_out = self.temporal_gnn(x, temporal_edge_index, edge_attr, batch)
            fused = torch.cat([spatial_out, temporal_out], dim=-1)
        else:
            fused = spatial_out.unsqueeze(-1)
        
        out = self.fusion(fused)
        
        return out.squeeze(-1)


class NO2InversionModel(nn.Module):
    def __init__(self, config):
        super(NO2InversionModel, self).__init__()
        
        self.model_type = config.get('model.name', 'WeatherTransportGNN')
        in_channels = config.get('data.in_channels', 10)
        hidden_dim = config.get('model.hidden_dim', 128)
        num_layers = config.get('model.num_layers', 3)
        dropout = config.get('model.dropout', 0.3)
        num_heads = config.get('model.num_heads', 4)
        out_channels = 1
        
        if self.model_type == 'WeatherTransportGNN':
            self.model = WeatherTransportGNN(
                in_channels, hidden_dim, num_layers, dropout, num_heads, out_channels
            )
        elif self.model_type == 'EdgeWeightedGNN':
            self.model = EdgeWeightedGNN(
                in_channels, hidden_dim, num_layers, dropout, out_channels
            )
        elif self.model_type == 'SpatialTemporalGNN':
            self.model = SpatialTemporalGNN(
                in_channels, hidden_dim, num_layers, dropout, num_heads, out_channels
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        logger.info(f"Initialized {self.model_type} model")
    
    def forward(self, x, edge_index, edge_attr=None, batch=None):
        return self.model(x, edge_index, edge_attr, batch)
    
    def predict(self, data):
        self.eval()
        with torch.no_grad():
            out = self.forward(data.x, data.edge_index, data.edge_attr, data.batch)
        return out