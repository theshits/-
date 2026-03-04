import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.loader import DataLoader
from torch_geometric.data import Data
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from typing import Dict, List, Optional, Tuple
import logging
from tqdm import tqdm
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Trainer:
    def __init__(self, model, config):
        self.model = model
        self.config = config
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        self.learning_rate = config.get('training.learning_rate', 0.001)
        self.weight_decay = config.get('training.weight_decay', 0.0001)
        
        self.optimizer = optim.Adam(
            self.model.parameters(), 
            lr=self.learning_rate,
            weight_decay=self.weight_decay
        )
        
        self.criterion = nn.MSELoss()
        
        self.best_val_loss = float('inf')
        self.patience = config.get('training.early_stopping_patience', 20)
        self.patience_counter = 0
        
        self.train_losses = []
        self.val_losses = []
        
        logger.info(f"Trainer initialized on device: {self.device}")
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        
        for batch in tqdm(train_loader, desc="Training"):
            batch = batch.to(self.device)
            
            self.optimizer.zero_grad()
            
            out = self.model(batch.x, batch.edge_index, batch.edge_attr, batch.batch)
            
            loss = self.criterion(out, batch.y)
            
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item() * batch.num_graphs
        
        avg_loss = total_loss / len(train_loader.dataset)
        return avg_loss
    
    @torch.no_grad()
    def validate(self, val_loader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        
        for batch in val_loader:
            batch = batch.to(self.device)
            
            out = self.model(batch.x, batch.edge_index, batch.edge_attr, batch.batch)
            
            loss = self.criterion(out, batch.y)
            
            total_loss += loss.item() * batch.num_graphs
        
        avg_loss = total_loss / len(val_loader.dataset)
        return avg_loss
    
    def train(self, train_loader: DataLoader, val_loader: DataLoader, 
              num_epochs: int, save_path: Optional[str] = None) -> Dict[str, List[float]]:
        logger.info(f"Starting training for {num_epochs} epochs")
        
        for epoch in range(num_epochs):
            train_loss = self.train_epoch(train_loader)
            val_loss = self.validate(val_loader)
            
            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)
            
            logger.info(f"Epoch {epoch + 1}/{num_epochs} - Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")
            
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                
                if save_path:
                    self.save_model(save_path)
                    logger.info(f"Model saved to {save_path}")
            else:
                self.patience_counter += 1
                
                if self.patience_counter >= self.patience:
                    logger.info(f"Early stopping triggered after {epoch + 1} epochs")
                    break
        
        return {
            'train_losses': self.train_losses,
            'val_losses': self.val_losses
        }
    
    def save_model(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'best_val_loss': self.best_val_loss,
            'train_losses': self.train_losses,
            'val_losses': self.val_losses
        }, path)
    
    def load_model(self, path: str):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.best_val_loss = checkpoint['best_val_loss']
        self.train_losses = checkpoint['train_losses']
        self.val_losses = checkpoint['val_losses']
        
        logger.info(f"Model loaded from {path}")


class Evaluator:
    def __init__(self, model, config):
        self.model = model
        self.config = config
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        self.metrics = config.get('evaluation.metrics', ['rmse', 'mae', 'r2', 'bias'])
        
        logger.info(f"Evaluator initialized on device: {self.device}")
    
    @torch.no_grad()
    def evaluate(self, data_loader: DataLoader) -> Dict[str, float]:
        self.model.eval()
        
        all_predictions = []
        all_targets = []
        
        for batch in tqdm(data_loader, desc="Evaluating"):
            batch = batch.to(self.device)
            
            out = self.model(batch.x, batch.edge_index, batch.edge_attr, batch.batch)
            
            all_predictions.append(out.cpu().numpy())
            all_targets.append(batch.y.cpu().numpy())
        
        predictions = np.concatenate(all_predictions)
        targets = np.concatenate(all_targets)
        
        results = {}
        
        if 'rmse' in self.metrics:
            results['rmse'] = np.sqrt(mean_squared_error(targets, predictions))
        
        if 'mae' in self.metrics:
            results['mae'] = mean_absolute_error(targets, predictions)
        
        if 'r2' in self.metrics:
            results['r2'] = r2_score(targets, predictions)
        
        if 'bias' in self.metrics:
            results['bias'] = np.mean(predictions - targets)
        
        return results
    
    @torch.no_grad()
    def predict(self, data: Data) -> np.ndarray:
        self.model.eval()
        data = data.to(self.device)
        
        out = self.model(data.x, data.edge_index, data.edge_attr, data.batch)
        
        return out.cpu().numpy()
    
    def print_results(self, results: Dict[str, float]):
        logger.info("=" * 50)
        logger.info("Evaluation Results")
        logger.info("=" * 50)
        
        for metric, value in results.items():
            logger.info(f"{metric.upper()}: {value:.6f}")
        
        logger.info("=" * 50)


class DataSplitter:
    def __init__(self, config):
        self.config = config
        
        self.train_ratio = config.get('training.train_ratio', 0.7)
        self.val_ratio = config.get('training.val_ratio', 0.15)
        self.test_ratio = config.get('training.test_ratio', 0.15)
    
    def split_data(self, data: Data) -> Tuple[Data, Data, Data]:
        num_nodes = data.num_nodes
        indices = np.random.permutation(num_nodes)
        
        train_size = int(num_nodes * self.train_ratio)
        val_size = int(num_nodes * self.val_ratio)
        
        train_indices = indices[:train_size]
        val_indices = indices[train_size:train_size + val_size]
        test_indices = indices[train_size + val_size:]
        
        train_data = self._create_subgraph(data, train_indices)
        val_data = self._create_subgraph(data, val_indices)
        test_data = self._create_subgraph(data, test_indices)
        
        logger.info(f"Data split - Train: {len(train_indices)}, Val: {len(val_indices)}, Test: {len(test_indices)}")
        
        return train_data, val_data, test_data
    
    def _create_subgraph(self, data: Data, node_indices: np.ndarray) -> Data:
        node_mask = torch.zeros(data.num_nodes, dtype=torch.bool)
        node_mask[node_indices] = True
        
        edge_mask = node_mask[data.edge_index[0]] & node_mask[data.edge_index[1]]
        
        new_edge_index = data.edge_index[:, edge_mask]
        new_edge_attr = data.edge_attr[edge_mask] if data.edge_attr is not None else None
        
        node_mapping = {old_idx: new_idx for new_idx, old_idx in enumerate(node_indices)}
        new_edge_index = torch.tensor([
            [node_mapping[src.item()] for src in new_edge_index[0]],
            [node_mapping[dst.item()] for dst in new_edge_index[1]]
        ], dtype=torch.long)
        
        new_data = Data(
            x=data.x[node_indices],
            edge_index=new_edge_index,
            edge_attr=new_edge_attr,
            y=data.y[node_indices],
            pos=data.pos[node_indices] if data.pos is not None else None
        )
        
        return new_data
    
    def split_temporal_data(self, graphs: List[Data]) -> Tuple[List[Data], List[Data], List[Data]]:
        num_graphs = len(graphs)
        
        train_size = int(num_graphs * self.train_ratio)
        val_size = int(num_graphs * self.val_ratio)
        
        train_graphs = graphs[:train_size]
        val_graphs = graphs[train_size:train_size + val_size]
        test_graphs = graphs[train_size + val_size:]
        
        logger.info(f"Temporal split - Train: {len(train_graphs)}, Val: {len(val_graphs)}, Test: {len(test_graphs)}")
        
        return train_graphs, val_graphs, test_graphs