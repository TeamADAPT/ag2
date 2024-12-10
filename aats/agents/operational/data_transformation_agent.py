"""
Data Transformation Agent Implementation
This agent handles data transformation, cleaning, and normalization
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
import dask.dataframe as dd
import pyarrow as pa
import pyarrow.compute as pc
from fuzzywuzzy import fuzz
import re
from dateutil.parser import parse

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class TransformationType(str):
    """Transformation type definitions"""
    CLEANING = "cleaning"
    NORMALIZATION = "normalization"
    STANDARDIZATION = "standardization"
    ENCODING = "encoding"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"

class DataFormat(str):
    """Data format definitions"""
    TABULAR = "tabular"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    PARQUET = "parquet"
    AVRO = "avro"

class DataTransformationAgent(BaseAgent):
    """
    Data Transformation Agent responsible for handling data
    transformation, cleaning, and normalization.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataTransformer",
            description="Handles data transformation and cleaning",
            capabilities=[
                "data_cleaning",
                "data_normalization",
                "data_standardization",
                "data_encoding",
                "data_aggregation"
            ],
            required_tools=[
                "data_cleaner",
                "data_normalizer",
                "data_encoder"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.transformation_stats: Dict[str, Dict] = {}
        self.transformation_methods: Dict[str, callable] = {}
        self.encoders: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the Data Transformation Agent"""
        try:
            self.logger.info("Initializing Data Transformation Agent...")
            
            # Initialize transformation methods
            await self._initialize_transformation_methods()
            
            # Initialize encoders
            await self._initialize_encoders()
            
            # Initialize transformation stats
            await self._initialize_transformation_stats()
            
            self.logger.info("Data Transformation Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Transformation Agent: {str(e)}")
            return False

    async def _initialize_transformation_methods(self) -> None:
        """Initialize transformation methods"""
        try:
            self.transformation_methods = {
                TransformationType.CLEANING: {
                    "missing_values": self._handle_missing_values,
                    "duplicates": self._handle_duplicates,
                    "outliers": self._handle_outliers,
                    "invalid_data": self._handle_invalid_data
                },
                TransformationType.NORMALIZATION: {
                    "min_max": self._normalize_min_max,
                    "z_score": self._normalize_z_score,
                    "decimal_scaling": self._normalize_decimal_scaling
                },
                TransformationType.STANDARDIZATION: {
                    "standard": self._standardize_data,
                    "robust": self._standardize_robust,
                    "custom": self._standardize_custom
                },
                TransformationType.ENCODING: {
                    "label": self._encode_label,
                    "one_hot": self._encode_one_hot,
                    "ordinal": self._encode_ordinal
                },
                TransformationType.AGGREGATION: {
                    "group": self._aggregate_group,
                    "window": self._aggregate_window,
                    "rolling": self._aggregate_rolling
                },
                TransformationType.FILTERING: {
                    "condition": self._filter_condition,
                    "range": self._filter_range,
                    "pattern": self._filter_pattern
                }
            }
            
            # Initialize transformation configurations
            self.transformation_configs = {
                "cleaning": {
                    "missing_threshold": 0.5,
                    "duplicate_subset": None,
                    "outlier_threshold": 3
                },
                "normalization": {
                    "feature_range": (0, 1),
                    "clip": True
                },
                "encoding": {
                    "handle_unknown": "ignore",
                    "sparse": False
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize transformation methods: {str(e)}")

    async def _initialize_encoders(self) -> None:
        """Initialize data encoders"""
        try:
            self.encoders = {
                "label": LabelEncoder(),
                "standard": StandardScaler(),
                "minmax": MinMaxScaler()
            }
            
            # Initialize custom encoders
            self.custom_encoders = {
                "date": self._encode_date,
                "currency": self._encode_currency,
                "categorical": self._encode_categorical
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize encoders: {str(e)}")

    async def _initialize_transformation_stats(self) -> None:
        """Initialize transformation statistics"""
        try:
            self.transformation_stats = {
                transform_type: {
                    "transformations_performed": 0,
                    "successful_transformations": 0,
                    "failed_transformations": 0,
                    "average_duration": 0.0,
                    "last_transformation": None
                }
                for transform_type in TransformationType.__dict__.keys()
                if not transform_type.startswith('_')
            }
            
            # Load historical stats
            stored_stats = await db_utils.get_agent_state(
                self.id,
                "transformation_stats"
            )
            
            if stored_stats:
                self._merge_stats(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize transformation stats: {str(e)}")

    async def transform_data(
        self,
        data: Any,
        transformation_type: str,
        method: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Transform data using specified method
        
        Args:
            data: Input data to transform
            transformation_type: Type of transformation
            method: Transformation method
            options: Optional transformation options
            
        Returns:
            Dictionary containing transformation results
        """
        try:
            # Validate transformation type
            if transformation_type not in self.transformation_methods:
                return {
                    "success": False,
                    "error": f"Invalid transformation type: {transformation_type}"
                }
            
            # Get transformation method
            transform_method = self.transformation_methods[transformation_type].get(method)
            if not transform_method:
                return {
                    "success": False,
                    "error": f"Invalid method: {method}"
                }
            
            # Transform data
            start_time = datetime.now()
            result = await transform_method(
                data,
                options or {}
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            await self._update_transformation_stats(
                transformation_type,
                True,
                duration
            )
            
            return {
                "success": True,
                "transformation_type": transformation_type,
                "method": method,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Data transformation failed: {str(e)}")
            # Update statistics
            await self._update_transformation_stats(
                transformation_type,
                False,
                0.0
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def clean_data(
        self,
        data: pd.DataFrame,
        cleaning_methods: List[str],
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Clean data using specified methods
        
        Args:
            data: Input DataFrame
            cleaning_methods: List of cleaning methods to apply
            options: Optional cleaning options
            
        Returns:
            Dictionary containing cleaning results
        """
        try:
            results = {}
            cleaned_data = data.copy()
            
            for method in cleaning_methods:
                cleaner = self.transformation_methods[TransformationType.CLEANING].get(method)
                if cleaner:
                    method_result = await cleaner(
                        cleaned_data,
                        options or {}
                    )
                    cleaned_data = method_result["data"]
                    results[method] = method_result["stats"]
            
            return {
                "success": True,
                "data": cleaned_data,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Data cleaning failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def normalize_data(
        self,
        data: Union[pd.DataFrame, np.ndarray],
        method: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Normalize data using specified method
        
        Args:
            data: Input data
            method: Normalization method
            options: Optional normalization options
            
        Returns:
            Dictionary containing normalization results
        """
        try:
            normalizer = self.transformation_methods[TransformationType.NORMALIZATION].get(method)
            if not normalizer:
                return {
                    "success": False,
                    "error": f"Invalid normalization method: {method}"
                }
            
            result = await normalizer(
                data,
                options or {}
            )
            
            return {
                "success": True,
                "data": result["data"],
                "stats": result["stats"]
            }
            
        except Exception as e:
            self.logger.error(f"Data normalization failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_missing_values(
        self,
        data: pd.DataFrame,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle missing values in data"""
        try:
            # Get missing value statistics
            missing_stats = data.isnull().sum()
            total_missing = missing_stats.sum()
            
            # Apply handling strategy
            strategy = options.get('strategy', 'drop')
            if strategy == 'drop':
                cleaned_data = data.dropna(
                    thresh=options.get('threshold', None)
                )
            elif strategy == 'fill':
                fill_value = options.get('fill_value')
                cleaned_data = data.fillna(fill_value)
            elif strategy == 'interpolate':
                method = options.get('method', 'linear')
                cleaned_data = data.interpolate(method=method)
            else:
                raise ValueError(f"Invalid missing value strategy: {strategy}")
            
            return {
                "data": cleaned_data,
                "stats": {
                    "total_missing": total_missing,
                    "missing_by_column": missing_stats.to_dict(),
                    "rows_affected": len(data) - len(cleaned_data)
                }
            }
            
        except Exception as e:
            raise Exception(f"Missing value handling failed: {str(e)}")

    async def _normalize_min_max(
        self,
        data: Union[pd.DataFrame, np.ndarray],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Min-max normalization"""
        try:
            feature_range = options.get(
                'feature_range',
                self.transformation_configs["normalization"]["feature_range"]
            )
            
            # Initialize scaler
            scaler = MinMaxScaler(feature_range=feature_range)
            
            # Fit and transform
            if isinstance(data, pd.DataFrame):
                normalized_data = pd.DataFrame(
                    scaler.fit_transform(data),
                    columns=data.columns,
                    index=data.index
                )
            else:
                normalized_data = scaler.fit_transform(data)
            
            return {
                "data": normalized_data,
                "stats": {
                    "min": scaler.data_min_.tolist(),
                    "max": scaler.data_max_.tolist(),
                    "scale": scaler.scale_.tolist()
                }
            }
            
        except Exception as e:
            raise Exception(f"Min-max normalization failed: {str(e)}")

    async def _update_transformation_stats(
        self,
        transformation_type: str,
        success: bool,
        duration: float
    ) -> None:
        """Update transformation statistics"""
        try:
            stats = self.transformation_stats[transformation_type]
            
            # Update counters
            stats["transformations_performed"] += 1
            if success:
                stats["successful_transformations"] += 1
            else:
                stats["failed_transformations"] += 1
            
            # Update average duration
            total_transformations = stats["transformations_performed"]
            current_avg = stats["average_duration"]
            stats["average_duration"] = (
                (current_avg * (total_transformations - 1) + duration) /
                total_transformations
            )
            
            stats["last_transformation"] = datetime.now().isoformat()
            
            # Store metrics
            await db_utils.record_metric(
                agent_id=self.id,
                metric_type="data_transformation",
                value=duration,
                tags={
                    "transformation_type": transformation_type,
                    "success": success
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update transformation stats: {str(e)}")

# Global data transformer instance
data_transformer = DataTransformationAgent()
