"""
Model Feedback Agent Implementation
This agent handles feedback collection, analysis, and incorporation
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils
from .model_connectivity_agent import ModelType, ModelProvider

class FeedbackType(str, Enum):
    """Feedback type definitions"""
    QUALITY = "quality"
    ACCURACY = "accuracy"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    FEATURE = "feature"
    BUG = "bug"

class FeedbackPriority(str, Enum):
    """Feedback priority definitions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FeedbackStatus(str, Enum):
    """Feedback status definitions"""
    NEW = "new"
    ANALYZING = "analyzing"
    ACTIONABLE = "actionable"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

@dataclass
class Feedback:
    """Feedback definition"""
    id: str
    type: FeedbackType
    model_type: str
    content: str
    metadata: Dict[str, Any]
    priority: FeedbackPriority
    status: FeedbackStatus
    sentiment: float
    created_at: datetime
    updated_at: datetime
    source: str
    tags: List[str]
    related_feedback: List[str]

class ModelFeedbackAgent(BaseAgent):
    """
    Model Feedback Agent responsible for managing model
    feedback and improvements.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="ModelFeedback",
            description="Handles model feedback management",
            capabilities=[
                "feedback_collection",
                "feedback_analysis",
                "sentiment_analysis",
                "clustering",
                "trend_analysis"
            ],
            required_tools=[
                "feedback_collector",
                "feedback_analyzer",
                "trend_analyzer"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.feedback_items: Dict[str, Feedback] = {}
        self.feedback_clusters: Dict[str, List[str]] = {}
        self.sentiment_analyzer: Optional[SentimentIntensityAnalyzer] = None
        self.trend_data: Dict[str, List] = {}

    async def initialize(self) -> bool:
        """Initialize the Model Feedback Agent"""
        try:
            self.logger.info("Initializing Model Feedback Agent...")
            
            # Initialize feedback analysis
            await self._initialize_feedback_analysis()
            
            # Initialize sentiment analysis
            await self._initialize_sentiment_analysis()
            
            # Initialize trend tracking
            await self._initialize_trend_tracking()
            
            # Start feedback tasks
            self._start_feedback_tasks()
            
            self.logger.info("Model Feedback Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Model Feedback Agent: {str(e)}")
            return False

    async def _initialize_feedback_analysis(self) -> None:
        """Initialize feedback analysis"""
        try:
            # Initialize text vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            # Initialize clustering
            self.clusterer = KMeans(
                n_clusters=5,
                random_state=42
            )
            
            # Initialize analysis configurations
            self.analysis_configs = {
                "min_cluster_size": 3,
                "similarity_threshold": 0.7,
                "max_related_items": 5,
                "update_frequency": 3600  # seconds
            }
            
            # Initialize feature extraction
            self.feature_extractors = {
                "keywords": self._extract_keywords,
                "entities": self._extract_entities,
                "topics": self._extract_topics
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize feedback analysis: {str(e)}")

    async def _initialize_sentiment_analysis(self) -> None:
        """Initialize sentiment analysis"""
        try:
            # Download NLTK data
            nltk.download('vader_lexicon')
            
            # Initialize sentiment analyzer
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            
            # Initialize sentiment thresholds
            self.sentiment_thresholds = {
                "positive": 0.2,
                "negative": -0.2,
                "neutral": (-0.2, 0.2)
            }
            
            # Initialize sentiment tracking
            self.sentiment_tracking = {
                model_type: {
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                    "average": 0.0
                }
                for model_type in ModelType
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize sentiment analysis: {str(e)}")

    async def _initialize_trend_tracking(self) -> None:
        """Initialize trend tracking"""
        try:
            # Initialize trend categories
            self.trend_categories = {
                "feedback_volume": self._track_feedback_volume,
                "sentiment_trends": self._track_sentiment_trends,
                "topic_trends": self._track_topic_trends,
                "response_trends": self._track_response_trends
            }
            
            # Initialize trend periods
            self.trend_periods = {
                "hourly": 3600,
                "daily": 86400,
                "weekly": 604800,
                "monthly": 2592000
            }
            
            # Initialize trend data structures
            self.trend_data = {
                category: {
                    period: []
                    for period in self.trend_periods
                }
                for category in self.trend_categories
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize trend tracking: {str(e)}")

    def _start_feedback_tasks(self) -> None:
        """Start feedback tasks"""
        asyncio.create_task(self._process_feedback())
        asyncio.create_task(self._analyze_trends())
        asyncio.create_task(self._update_clusters())

    async def collect_feedback(
        self,
        model_type: str,
        feedback_content: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Collect model feedback
        
        Args:
            model_type: Type of model
            feedback_content: Feedback content
            metadata: Optional feedback metadata
            
        Returns:
            Dictionary containing feedback collection results
        """
        try:
            # Generate feedback ID
            feedback_id = f"feedback_{datetime.now().timestamp()}"
            
            # Analyze sentiment
            sentiment_scores = self.sentiment_analyzer.polarity_scores(
                feedback_content
            )
            
            # Determine feedback type and priority
            feedback_type = await self._determine_feedback_type(
                feedback_content,
                metadata or {}
            )
            
            priority = await self._determine_priority(
                feedback_type,
                sentiment_scores,
                metadata or {}
            )
            
            # Create feedback item
            feedback = Feedback(
                id=feedback_id,
                type=feedback_type,
                model_type=model_type,
                content=feedback_content,
                metadata=metadata or {},
                priority=priority,
                status=FeedbackStatus.NEW,
                sentiment=sentiment_scores["compound"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                source=metadata.get("source", "user"),
                tags=await self._extract_tags(feedback_content),
                related_feedback=[]
            )
            
            # Store feedback
            self.feedback_items[feedback_id] = feedback
            
            # Update sentiment tracking
            self._update_sentiment_tracking(
                model_type,
                sentiment_scores["compound"]
            )
            
            return {
                "success": True,
                "feedback_id": feedback_id,
                "type": feedback_type,
                "priority": priority,
                "sentiment": sentiment_scores
            }
            
        except Exception as e:
            self.logger.error(f"Feedback collection failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_feedback(
        self,
        feedback_id: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze collected feedback
        
        Args:
            feedback_id: Feedback identifier
            options: Optional analysis options
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Get feedback item
            feedback = self.feedback_items.get(feedback_id)
            if not feedback:
                return {
                    "success": False,
                    "error": f"Feedback not found: {feedback_id}"
                }
            
            # Update status
            feedback.status = FeedbackStatus.ANALYZING
            
            # Extract features
            features = {}
            for name, extractor in self.feature_extractors.items():
                features[name] = await extractor(
                    feedback.content,
                    options or {}
                )
            
            # Find related feedback
            related_feedback = await self._find_related_feedback(
                feedback,
                options or {}
            )
            
            # Generate insights
            insights = await self._generate_feedback_insights(
                feedback,
                features,
                related_feedback
            )
            
            # Update feedback
            feedback.status = FeedbackStatus.ACTIONABLE
            feedback.related_feedback = [f.id for f in related_feedback]
            feedback.updated_at = datetime.now()
            
            return {
                "success": True,
                "features": features,
                "related_feedback": [
                    {
                        "id": f.id,
                        "content": f.content,
                        "similarity": s
                    }
                    for f, s in related_feedback
                ],
                "insights": insights
            }
            
        except Exception as e:
            self.logger.error(f"Feedback analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_feedback_trends(
        self,
        model_type: str,
        period: str,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get feedback trends
        
        Args:
            model_type: Type of model
            period: Trend period
            categories: Optional trend categories
            
        Returns:
            Dictionary containing trend data
        """
        try:
            if period not in self.trend_periods:
                return {
                    "success": False,
                    "error": f"Invalid period: {period}"
                }
            
            # Get trend categories
            categories_to_analyze = (
                categories or list(self.trend_categories.keys())
            )
            
            # Collect trend data
            trends = {}
            for category in categories_to_analyze:
                if category in self.trend_categories:
                    trends[category] = await self.trend_categories[category](
                        model_type,
                        period
                    )
            
            # Generate trend analysis
            analysis = await self._analyze_trend_patterns(
                trends,
                model_type,
                period
            )
            
            return {
                "success": True,
                "trends": trends,
                "analysis": analysis,
                "period": period
            }
            
        except Exception as e:
            self.logger.error(f"Trend analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _process_feedback(self) -> None:
        """Process feedback continuously"""
        while True:
            try:
                # Process new feedback
                new_feedback = [
                    f_id for f_id, feedback in self.feedback_items.items()
                    if feedback.status == FeedbackStatus.NEW
                ]
                
                for feedback_id in new_feedback:
                    # Analyze feedback
                    await self.analyze_feedback(feedback_id)
                
                # Wait before next processing
                await asyncio.sleep(60)  # Process every minute
                
            except Exception as e:
                self.logger.error(f"Error in feedback processing: {str(e)}")
                await asyncio.sleep(60)

    async def _analyze_trends(self) -> None:
        """Analyze feedback trends"""
        while True:
            try:
                current_time = datetime.now()
                
                # Update trend data
                for category, tracker in self.trend_categories.items():
                    for period in self.trend_periods:
                        # Update period data
                        await self._update_trend_data(
                            category,
                            period,
                            current_time
                        )
                
                # Generate trend reports
                await self._generate_trend_reports()
                
                # Wait before next analysis
                await asyncio.sleep(3600)  # Analyze every hour
                
            except Exception as e:
                self.logger.error(f"Error in trend analysis: {str(e)}")
                await asyncio.sleep(3600)

    async def _update_clusters(self) -> None:
        """Update feedback clusters"""
        while True:
            try:
                # Collect feedback texts
                texts = [
                    f.content
                    for f in self.feedback_items.values()
                ]
                
                if texts:
                    # Vectorize texts
                    vectors = self.vectorizer.fit_transform(texts)
                    
                    # Update clusters
                    self.clusterer.fit(vectors)
                    
                    # Update feedback clusters
                    await self._update_feedback_clusters(
                        texts,
                        self.clusterer.labels_
                    )
                
                # Wait before next update
                await asyncio.sleep(3600)  # Update every hour
                
            except Exception as e:
                self.logger.error(f"Error in cluster update: {str(e)}")
                await asyncio.sleep(3600)

# Global feedback agent instance
feedback_agent = ModelFeedbackAgent()
