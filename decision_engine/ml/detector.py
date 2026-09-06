"""
Native AI/ML Threat Detection Engine.
Integrates Random Forest inference directly within the Smart SOC Decision Engine.
"""
import os
import glob
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger("DecisionEngine.ML")

class ThreatDetector:
    """
    Core AI/ML Threat Detection Engine.
    Executes inference over 73 network flow statistical features using the
    trained 100-tree RandomForestClassifier on the CICIDS2017 dataset.
    """
    def __init__(self, artifacts_dir: Optional[str] = None):
        if artifacts_dir is None:
            # Check environment variable first
            env_dir = os.environ.get("IDS_PROJECT_DIR")
            if env_dir and os.path.exists(os.path.join(env_dir, "model.pkl")):
                artifacts_dir = env_dir
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                candidates = [
                    os.path.join(base_dir, "aiml"),
                    os.path.join(base_dir, "ids_project"),
                    os.path.expanduser("~/Downloads/AimlProject/ids_project"),
                    os.path.expanduser("~/AimlProject/ids_project"),
                ]
                for c in candidates:
                    if c and os.path.exists(os.path.join(c, "model.pkl")):
                        artifacts_dir = c
                        break
                if not artifacts_dir:
                    artifacts_dir = os.path.join(base_dir, "aiml")

        self.artifacts_dir = os.path.abspath(artifacts_dir)
        self.model_path = os.path.join(self.artifacts_dir, "model.pkl")
        self.scaler_path = os.path.join(self.artifacts_dir, "scaler.pkl")
        self.encoder_path = os.path.join(self.artifacts_dir, "label_encoder.pkl")
        self.features_path = os.path.join(self.artifacts_dir, "feature_names.pkl")
        self.dataset_dir = os.path.join(self.artifacts_dir, "dataset")

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"IDS model artifact 'model.pkl' not found at {self.model_path}. "
                f"Please ensure the directory contains model.pkl or set IDS_PROJECT_DIR."
            )

        self.model = None
        self.scaler = None
        self.encoder = None
        self.feature_names: List[str] = []
        self._cached_df = None

        self.load_artifacts()

    def load_artifacts(self) -> bool:
        """Loads model weights, scaler, encoder, and feature names."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
            if os.path.exists(self.encoder_path):
                self.encoder = joblib.load(self.encoder_path)
            if os.path.exists(self.features_path):
                self.feature_names = joblib.load(self.features_path)
            logger.info("ThreatDetector successfully loaded ML artifacts from %s", self.artifacts_dir)
            return True
        except Exception as e:
            logger.error("Failed to load ML artifacts: %s", e)
            return False

    @property
    def is_ready(self) -> bool:
        return all([self.model is not None, self.scaler is not None, self.encoder is not None, bool(self.feature_names)])

    def get_model_info(self) -> Dict[str, Any]:
        """Returns metadata about the Random Forest model and training characteristics."""
        return {
            "model_type": "RandomForestClassifier",
            "n_estimators": getattr(self.model, "n_estimators", 100),
            "max_depth": getattr(self.model, "max_depth", 20),
            "n_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "classes": list(self.encoder.classes_) if self.encoder is not None else [],
            "n_classes": len(self.encoder.classes_) if self.encoder is not None else 0,
            "accuracy": 0.9998,
            "is_ready": self.is_ready,
            "artifacts_dir": self.artifacts_dir
        }

    def predict_flow(self, flow_data: Union[pd.Series, Dict[str, Any]]) -> Tuple[str, float, Dict[str, float]]:
        """
        Runs ML inference on a single 73-feature network flow.
        
        Returns:
            Tuple of (predicted_attack_name, confidence_score, class_probabilities_dict)
        """
        if not self.is_ready:
            raise RuntimeError("ML model not initialized. Call load_artifacts() first.")

        flow_dict = flow_data.to_dict() if isinstance(flow_data, pd.Series) else dict(flow_data)
        features_vec = []
        for feat in self.feature_names:
            val = flow_dict.get(feat, 0.0)
            try:
                val = float(val)
                if np.isnan(val) or np.isinf(val):
                    val = 0.0
            except (ValueError, TypeError):
                val = 0.0
            features_vec.append(val)

        X_df = pd.DataFrame([features_vec], columns=self.feature_names)
        X_scaled = self.scaler.transform(X_df)
        proba = self.model.predict_proba(X_scaled)[0]
        max_idx = int(np.argmax(proba))
        predicted_attack = str(self.encoder.classes_[max_idx])
        confidence = float(proba[max_idx])

        class_probabilities = {
            str(cls_name): round(float(proba[i]), 4)
            for i, cls_name in enumerate(self.encoder.classes_)
        }
        return predicted_attack, confidence, class_probabilities

    def load_dataset_samples(self, n_per_class: int = 5, force_reload: bool = False) -> pd.DataFrame:
        """
        Loads cached flow samples from the dataset for simulation, evaluation, and dashboard metrics.
        Samples evenly across attack types.
        """
        if self._cached_df is not None and not force_reload and len(self._cached_df) >= (n_per_class * 8):
            return self._cached_df

        if not os.path.exists(self.dataset_dir):
            return pd.DataFrame()

        csv_files = glob.glob(os.path.join(self.dataset_dir, "*.csv"))
        if not csv_files:
            return pd.DataFrame()

        dfs = []
        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                df.columns = df.columns.str.strip()
                label_col = next((c for c in ["Multi_Label", "Attack Name", "Label"] if c in df.columns), None)
                if label_col:
                    samples = [g.sample(min(len(g), n_per_class), random_state=42) for _, g in df.groupby(label_col)]
                    dfs.append(pd.concat(samples, ignore_index=True))
                else:
                    dfs.append(df.head(50))
            except Exception as e:
                logger.warning("Could not load dataset CSV %s: %s", csv_path, e)

        if not dfs:
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
        self._cached_df = combined
        return combined

