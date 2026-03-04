import torch
import numpy as np
import pandas as pd
from pathlib import Path
import logging
import argparse

from config import Config
from data_processor import TROPOMIDataProcessor
from station_processor import GroundStationProcessor, WeatherStationProcessor
from data_integrator import DataIntegrator
from graph_builder import WeatherTransportGraph
from gnn_model import NO2InversionModel
from trainer import Trainer, Evaluator, DataSplitter
from torch_geometric.loader import DataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='GNN-based NO2 Inversion Model')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--mode', type=str, default='train', choices=['train', 'evaluate', 'predict'], 
                       help='Mode: train, evaluate, or predict')
    parser.add_argument('--model_path', type=str, default='models/best_model.pt', 
                       help='Path to save/load model')
    args = parser.parse_args()
    
    config = Config(args.config)
    
    logger.info("Starting NO2 Inversion Pipeline")
    logger.info(f"Mode: {args.mode}")
    
    tropomi_path = config.get('data.tropomi_path', 'data/tropomi/')
    ground_path = config.get('data.ground_path', 'data/ground/')
    weather_path = config.get('data.weather_path', 'data/weather/')
    
    logger.info("Loading and preprocessing data...")
    
    tropomi_processor = TROPOMIDataProcessor(
        tropomi_path, 
        spatial_resolution=config.get('data.spatial_resolution', 0.1)
    )
    
    ground_processor = GroundStationProcessor(ground_path)
    weather_processor = WeatherStationProcessor(weather_path)
    
    tropomi_df = tropomi_processor.process_directory()
    ground_df = ground_processor.process_directory(
        resample_freq=config.get('data.time_resolution', 'daily')
    )
    weather_df = weather_processor.process_directory(
        resample_freq=config.get('data.time_resolution', 'daily')
    )
    
    if tropomi_df.empty:
        logger.error("TROPOMI data is empty. Please check data path.")
        return
    
    logger.info("Integrating data...")
    
    integrator = DataIntegrator(spatial_resolution=config.get('data.spatial_resolution', 0.1))
    integrated_df = integrator.integrate_data(tropomi_df, ground_df, weather_df)
    
    logger.info("Creating node features and labels...")
    
    node_features = integrator.create_node_features(integrated_df)
    labels = integrator.create_labels(integrated_df)
    
    logger.info(f"Node features shape: {node_features.shape}")
    logger.info(f"Labels shape: {labels.shape}")
    
    config.config['data']['in_channels'] = node_features.shape[1]
    
    logger.info("Building graph...")
    
    graph_builder = WeatherTransportGraph(
        k_neighbors=config.get('graph.k_neighbors', 8),
        max_distance=config.get('graph.max_distance', 50.0),
        wind_weight=config.get('graph.wind_weight', True)
    )
    
    graph_data = graph_builder.create_graph_data(
        node_features=node_features,
        labels=labels,
        lat=integrated_df['latitude'].values,
        lon=integrated_df['longitude'].values,
        weather_df=integrated_df,
        times=integrated_df['time'].values if 'time' in integrated_df.columns else None,
        temporal_window=config.get('graph.temporal_window', 24)
    )
    
    logger.info(f"Graph created: {graph_data.num_nodes} nodes, {graph_data.num_edges} edges")
    
    logger.info("Splitting data...")
    
    splitter = DataSplitter(config)
    train_data, val_data, test_data = splitter.split_data(graph_data)
    
    batch_size = config.get('training.batch_size', 32)
    
    train_loader = DataLoader([train_data], batch_size=batch_size, shuffle=True)
    val_loader = DataLoader([val_data], batch_size=batch_size, shuffle=False)
    test_loader = DataLoader([test_data], batch_size=batch_size, shuffle=False)
    
    logger.info("Initializing model...")
    
    model = NO2InversionModel(config)
    
    if args.mode == 'train':
        logger.info("Training model...")
        
        trainer = Trainer(model, config)
        
        history = trainer.train(
            train_loader=train_loader,
            val_loader=val_loader,
            num_epochs=config.get('training.num_epochs', 200),
            save_path=args.model_path
        )
        
        logger.info("Training completed!")
        logger.info(f"Best validation loss: {trainer.best_val_loss:.6f}")
        
        logger.info("Evaluating on test set...")
        
        evaluator = Evaluator(model, config)
        test_results = evaluator.evaluate(test_loader)
        evaluator.print_results(test_results)
    
    elif args.mode == 'evaluate':
        if not Path(args.model_path).exists():
            logger.error(f"Model file not found: {args.model_path}")
            return
        
        logger.info(f"Loading model from {args.model_path}...")
        
        trainer = Trainer(model, config)
        trainer.load_model(args.model_path)
        
        logger.info("Evaluating on test set...")
        
        evaluator = Evaluator(model, config)
        test_results = evaluator.evaluate(test_loader)
        evaluator.print_results(test_results)
    
    elif args.mode == 'predict':
        if not Path(args.model_path).exists():
            logger.error(f"Model file not found: {args.model_path}")
            return
        
        logger.info(f"Loading model from {args.model_path}...")
        
        trainer = Trainer(model, config)
        trainer.load_model(args.model_path)
        
        logger.info("Making predictions...")
        
        evaluator = Evaluator(model, config)
        predictions = evaluator.predict(test_data)
        
        logger.info(f"Predictions shape: {predictions.shape}")
        
        if config.get('evaluation.save_predictions', True):
            output_path = 'predictions/predictions.csv'
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            pred_df = pd.DataFrame({
                'latitude': test_data.pos[:, 0].numpy(),
                'longitude': test_data.pos[:, 1].numpy(),
                'predicted_no2': predictions,
                'actual_no2': test_data.y.numpy()
            })
            pred_df.to_csv(output_path, index=False)
            logger.info(f"Predictions saved to {output_path}")
    
    logger.info("Pipeline completed successfully!")


if __name__ == '__main__':
    main()