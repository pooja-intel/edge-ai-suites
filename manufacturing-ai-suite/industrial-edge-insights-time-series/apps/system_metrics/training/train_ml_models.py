#!/usr/bin/env python3
"""
ML Model Training for Predictive Maintenance
Uses labeled synthetic dataset to train anomaly detection and failure prediction models
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import warnings
warnings.filterwarnings('ignore')


class PredictiveMaintenanceML:
    def __init__(self, csv_file='tick_synthetic_pm_dataset.csv'):
        """Initialize with dataset"""
        print(f"Loading dataset from {csv_file}...")
        self.df = pd.read_csv(csv_file)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        
        print(f"Dataset loaded: {len(self.df)} records")
        print(f"Time range: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        
        self.feature_columns = [
            'cpu_total_pct', 'cpu_user_pct', 'cpu_system_pct', 'cpu_iowait_pct',
            'mem_used_pct', 'swap_used_pct',
            'disk_used_pct', 'disk_read_bps', 'disk_write_bps', 'disk_latency_ms', 'disk_iops',
            'net_in_bps', 'net_out_bps', 'net_err_rate',
            'load1', 'proc_running',
            'ctr_cpu_total_pct', 'ctr_mem_used_pct_of_limit', 'ctr_unhealthy_count', 'ctr_exited_count'
        ]
        
        self.scaler = StandardScaler()
        self.anomaly_model = None
        self.failure_model = None
        
    def prepare_features(self):
        """Prepare features for training"""
        print("\nPreparing features...")
        
        # Extract features
        X = self.df[self.feature_columns].copy()
        
        # Handle any missing values
        X = X.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled, X
    
    def train_anomaly_detector(self, test_size=0.2):
        """Train binary anomaly detection model"""
        print("\n" + "="*60)
        print("TRAINING ANOMALY DETECTION MODEL")
        print("="*60)
        
        X_scaled, X = self.prepare_features()
        y = self.df['anomaly']
        
        print(f"\nClass distribution:")
        print(f"  Normal: {(y==0).sum()} ({(y==0).sum()/len(y)*100:.1f}%)")
        print(f"  Anomaly: {(y==1).sum()} ({(y==1).sum()/len(y)*100:.1f}%)")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=42, stratify=y
        )
        
        print(f"\nTraining set: {len(X_train)} samples")
        print(f"Test set: {len(X_test)} samples")
        
        # Train Random Forest
        print("\nTraining Random Forest Classifier...")
        self.anomaly_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        
        self.anomaly_model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.anomaly_model.score(X_train, y_train)
        test_score = self.anomaly_model.score(X_test, y_test)
        
        print(f"\nTrain Accuracy: {train_score:.4f}")
        print(f"Test Accuracy: {test_score:.4f}")
        
        # Predictions
        y_pred = self.anomaly_model.predict(X_test)
        y_proba = self.anomaly_model.predict_proba(X_test)[:, 1]
        
        # Classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Normal', 'Anomaly']))
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print("\nConfusion Matrix:")
        print(cm)
        
        # ROC AUC
        roc_auc = roc_auc_score(y_test, y_proba)
        print(f"\nROC AUC Score: {roc_auc:.4f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.anomaly_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 10 Important Features:")
        print(feature_importance.head(10).to_string(index=False))
        
        # Save model
        joblib.dump(self.anomaly_model, 'anomaly_detector_model.pkl')
        print("\n✓ Model saved to: anomaly_detector_model.pkl")
        
        return self.anomaly_model, test_score, roc_auc
    
    def train_failure_predictor(self, test_size=0.2):
        """Train failure prediction model (60-minute horizon)"""
        print("\n" + "="*60)
        print("TRAINING FAILURE PREDICTION MODEL (60-min horizon)")
        print("="*60)
        
        X_scaled, X = self.prepare_features()
        y = self.df['failure_within_horizon']
        
        print(f"\nClass distribution:")
        print(f"  No failure within 60min: {(y==0).sum()} ({(y==0).sum()/len(y)*100:.1f}%)")
        print(f"  Failure within 60min: {(y==1).sum()} ({(y==1).sum()/len(y)*100:.1f}%)")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=42, stratify=y
        )
        
        print(f"\nTraining set: {len(X_train)} samples")
        print(f"Test set: {len(X_test)} samples")
        
        # Train Gradient Boosting
        print("\nTraining Gradient Boosting Classifier...")
        self.failure_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        self.failure_model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.failure_model.score(X_train, y_train)
        test_score = self.failure_model.score(X_test, y_test)
        
        print(f"\nTrain Accuracy: {train_score:.4f}")
        print(f"Test Accuracy: {test_score:.4f}")
        
        # Predictions
        y_pred = self.failure_model.predict(X_test)
        y_proba = self.failure_model.predict_proba(X_test)[:, 1]
        
        # Classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['No Failure', 'Failure Soon']))
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print("\nConfusion Matrix:")
        print(cm)
        
        # ROC AUC
        roc_auc = roc_auc_score(y_test, y_proba)
        print(f"\nROC AUC Score: {roc_auc:.4f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.failure_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 10 Important Features for Failure Prediction:")
        print(feature_importance.head(10).to_string(index=False))
        
        # Save model
        joblib.dump(self.failure_model, 'failure_predictor_model.pkl')
        print("\n✓ Model saved to: failure_predictor_model.pkl")
        
        return self.failure_model, test_score, roc_auc
    
    def train_multiclass_anomaly_classifier(self, test_size=0.2):
        """Train multi-class anomaly type classifier"""
        print("\n" + "="*60)
        print("TRAINING MULTI-CLASS ANOMALY TYPE CLASSIFIER")
        print("="*60)
        
        X_scaled, X = self.prepare_features()
        y = self.df['anomaly_type']
        
        # Filter only anomalous records for type classification
        anomaly_mask = self.df['anomaly'] == 1
        X_anomalies = X_scaled[anomaly_mask]
        y_types = y[anomaly_mask]
        
        print(f"\nAnomaly type distribution:")
        for atype in sorted(y_types.unique()):
            count = (y_types == atype).sum()
            type_name = {0: 'Normal', 1: 'CPU Spike', 2: 'Memory Leak', 
                        3: 'I/O Bottleneck', 4: 'Network', 5: 'Container'}.get(atype, 'Unknown')
            print(f"  {type_name} ({atype}): {count} ({count/len(y_types)*100:.1f}%)")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_anomalies, y_types, test_size=test_size, random_state=42
        )
        
        # Train classifier
        print("\nTraining Random Forest Classifier for anomaly types...")
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        
        clf.fit(X_train, y_train)
        
        # Evaluate
        test_score = clf.score(X_test, y_test)
        print(f"\nTest Accuracy: {test_score:.4f}")
        
        # Predictions
        y_pred = clf.predict(X_test)
        
        # Classification report
        print("\nClassification Report:")
        # Dynamically get class names based on actual classes present
        type_name_map = {0: 'Normal', 1: 'CPU', 2: 'Memory', 3: 'I/O', 4: 'Network', 5: 'Container'}
        unique_classes = sorted(y_test.unique())
        type_names = [type_name_map.get(c, f'Type{c}') for c in unique_classes]
        print(classification_report(y_test, y_pred, target_names=type_names, zero_division=0))
        
        # Save model
        joblib.dump(clf, 'anomaly_type_classifier_model.pkl')
        joblib.dump(self.scaler, 'feature_scaler.pkl')
        print("\n✓ Model saved to: anomaly_type_classifier_model.pkl")
        print("✓ Scaler saved to: feature_scaler.pkl")
        
        return clf, test_score
    
    def predict_realtime(self, metrics):
        """
        Make real-time predictions (for Kapacitor integration)
        
        Args:
            metrics: dict with current metric values
            
        Returns:
            dict with predictions
        """
        if self.anomaly_model is None or self.failure_model is None:
            raise ValueError("Models not trained. Call train_* methods first.")
        
        # Prepare features
        features = np.array([[
            metrics.get(col, 0) for col in self.feature_columns
        ]])
        
        features_scaled = self.scaler.transform(features)
        
        # Predictions
        is_anomaly = self.anomaly_model.predict(features_scaled)[0]
        anomaly_prob = self.anomaly_model.predict_proba(features_scaled)[0][1]
        
        failure_soon = self.failure_model.predict(features_scaled)[0]
        failure_prob = self.failure_model.predict_proba(features_scaled)[0][1]
        
        return {
            'is_anomaly': bool(is_anomaly),
            'anomaly_probability': float(anomaly_prob),
            'failure_within_60min': bool(failure_soon),
            'failure_probability': float(failure_prob),
            'alert_level': 'CRITICAL' if failure_prob > 0.8 else 'WARNING' if failure_prob > 0.6 else 'NORMAL'
        }


def main():
    """
    Main training pipeline
    """
    print("="*60)
    print("PREDICTIVE MAINTENANCE ML TRAINING")
    print("="*60)
    
    # Initialize
    pm_ml = PredictiveMaintenanceML('tick_synthetic_pm_dataset.csv')
    
    # Train anomaly detector
    anomaly_model, anomaly_acc, anomaly_roc = pm_ml.train_anomaly_detector()
    
    # Train failure predictor
    failure_model, failure_acc, failure_roc = pm_ml.train_failure_predictor()
    
    # Train anomaly type classifier
    type_model, type_acc = pm_ml.train_multiclass_anomaly_classifier()
    
    # Summary
    print("\n" + "="*60)
    print("TRAINING SUMMARY")
    print("="*60)
    print(f"Anomaly Detection:")
    print(f"  Accuracy: {anomaly_acc:.4f}")
    print(f"  ROC AUC: {anomaly_roc:.4f}")
    print(f"\nFailure Prediction (60-min horizon):")
    print(f"  Accuracy: {failure_acc:.4f}")
    print(f"  ROC AUC: {failure_roc:.4f}")
    print(f"\nAnomaly Type Classification:")
    print(f"  Accuracy: {type_acc:.4f}")
    
    print("\n" + "="*60)
    print("MODELS SAVED")
    print("="*60)
    print("  - anomaly_detector_model.pkl")
    print("  - failure_predictor_model.pkl")
    print("  - anomaly_type_classifier_model.pkl")
    print("  - feature_scaler.pkl")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("""
1. Deploy models to ML service for real-time predictions
2. Configure Kapacitor to send metrics to ML service
3. Set up alerts based on predictions
4. Monitor model performance and retrain periodically

Example Kapacitor integration:
  POST http://ml-service:5000/predict with current metrics
  Receive: {is_anomaly, failure_probability, alert_level}
    """)
    
    # Example prediction
    print("\n" + "="*60)
    print("EXAMPLE REAL-TIME PREDICTION")
    print("="*60)
    
    # Get a sample from the dataset (anomalous point)
    anomaly_sample = pm_ml.df[pm_ml.df['anomaly'] == 1].iloc[0]
    sample_metrics = {col: anomaly_sample[col] for col in pm_ml.feature_columns}
    
    prediction = pm_ml.predict_realtime(sample_metrics)
    
    print(f"\nSample metrics (actual anomaly):")
    print(f"  CPU: {sample_metrics['cpu_total_pct']:.1f}%")
    print(f"  Memory: {sample_metrics['mem_used_pct']:.1f}%")
    print(f"  Disk Latency: {sample_metrics['disk_latency_ms']:.1f}ms")
    
    print(f"\nPredictions:")
    print(f"  Is Anomaly: {prediction['is_anomaly']}")
    print(f"  Anomaly Probability: {prediction['anomaly_probability']:.3f}")
    print(f"  Failure Within 60min: {prediction['failure_within_60min']}")
    print(f"  Failure Probability: {prediction['failure_probability']:.3f}")
    print(f"  Alert Level: {prediction['alert_level']}")


if __name__ == '__main__':
    main()
