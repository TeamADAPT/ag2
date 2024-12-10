"""
Data Extraction Agent Implementation
This agent handles extracting structured and unstructured data from various sources
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
import json
import re
import bs4
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
import tabula
import camelot
import pdfplumber
import spacy
import nltk
from transformers import pipeline
import pandas as pd
import numpy as np

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class DataType(str):
    """Data type definitions"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    FORM = "form"
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"

class ExtractionMethod(str):
    """Extraction method definitions"""
    OCR = "ocr"
    PARSING = "parsing"
    NLP = "nlp"
    REGEX = "regex"
    ML = "machine_learning"

class DataExtractionAgent(BaseAgent):
    """
    Data Extraction Agent responsible for extracting data
    from various sources and formats.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="DataExtractor",
            description="Handles data extraction from various sources",
            capabilities=[
                "text_extraction",
                "table_extraction",
                "image_extraction",
                "form_extraction",
                "pattern_extraction"
            ],
            required_tools=[
                "text_extractor",
                "table_extractor",
                "image_processor",
                "pattern_matcher"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.extraction_stats: Dict[str, Dict] = {}
        self.extraction_methods: Dict[str, callable] = {}
        self.nlp_models: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the Data Extraction Agent"""
        try:
            self.logger.info("Initializing Data Extraction Agent...")
            
            # Initialize extraction methods
            await self._initialize_extraction_methods()
            
            # Initialize NLP models
            await self._initialize_nlp_models()
            
            # Initialize extraction stats
            await self._initialize_extraction_stats()
            
            self.logger.info("Data Extraction Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Data Extraction Agent: {str(e)}")
            return False

    async def _initialize_extraction_methods(self) -> None:
        """Initialize extraction methods"""
        try:
            self.extraction_methods = {
                DataType.TEXT: {
                    "basic": self._extract_text_basic,
                    "nlp": self._extract_text_nlp,
                    "ml": self._extract_text_ml
                },
                DataType.TABLE: {
                    "structured": self._extract_table_structured,
                    "unstructured": self._extract_table_unstructured,
                    "image": self._extract_table_from_image
                },
                DataType.IMAGE: {
                    "ocr": self._extract_image_ocr,
                    "ml": self._extract_image_ml,
                    "hybrid": self._extract_image_hybrid
                },
                DataType.FORM: {
                    "template": self._extract_form_template,
                    "ml": self._extract_form_ml,
                    "hybrid": self._extract_form_hybrid
                }
            }
            
            # Initialize extraction configurations
            self.extraction_configs = {
                "ocr": {
                    "engine": "tesseract",
                    "lang": "eng",
                    "config": "--oem 3 --psm 6"
                },
                "nlp": {
                    "models": ["en_core_web_sm", "en_core_web_lg"],
                    "pipeline": ["ner", "dependency_parsing"]
                },
                "table": {
                    "flavor": "lattice",
                    "guess": True,
                    "line_scale": 40
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize extraction methods: {str(e)}")

    async def _initialize_nlp_models(self) -> None:
        """Initialize NLP models"""
        try:
            # Load spaCy models
            self.nlp_models["spacy"] = {
                "small": spacy.load("en_core_web_sm"),
                "large": spacy.load("en_core_web_lg")
            }
            
            # Initialize NLTK
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            nltk.download('maxent_ne_chunker')
            nltk.download('words')
            
            # Initialize transformers
            self.nlp_models["transformers"] = {
                "ner": pipeline("ner"),
                "qa": pipeline("question-answering"),
                "summarization": pipeline("summarization")
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize NLP models: {str(e)}")

    async def _initialize_extraction_stats(self) -> None:
        """Initialize extraction statistics"""
        try:
            self.extraction_stats = {
                data_type: {
                    "extractions_performed": 0,
                    "successful_extractions": 0,
                    "failed_extractions": 0,
                    "average_duration": 0.0,
                    "last_extraction": None
                }
                for data_type in DataType.__dict__.keys()
                if not data_type.startswith('_')
            }
            
            # Load historical stats
            stored_stats = await db_utils.get_agent_state(
                self.id,
                "extraction_stats"
            )
            
            if stored_stats:
                self._merge_stats(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize extraction stats: {str(e)}")

    async def extract_data(
        self,
        source: Union[str, bytes],
        data_type: str,
        method: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract data from source
        
        Args:
            source: Data source (file path or bytes)
            data_type: Type of data to extract
            method: Optional extraction method
            options: Optional extraction options
            
        Returns:
            Dictionary containing extraction results
        """
        try:
            # Validate data type
            if data_type not in DataType.__dict__.keys():
                return {
                    "success": False,
                    "error": f"Invalid data type: {data_type}"
                }
            
            # Get extraction method
            method = method or self._determine_extraction_method(
                source,
                data_type
            )
            
            # Get extraction function
            extractor = self.extraction_methods[data_type].get(method)
            if not extractor:
                return {
                    "success": False,
                    "error": f"Unsupported extraction method: {method}"
                }
            
            # Extract data
            start_time = datetime.now()
            result = await extractor(
                source,
                options or {}
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            await self._update_extraction_stats(
                data_type,
                True,
                duration
            )
            
            return {
                "success": True,
                "data_type": data_type,
                "method": method,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            # Update statistics
            await self._update_extraction_stats(
                data_type,
                False,
                0.0
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def extract_pattern(
        self,
        source: str,
        pattern: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract data using pattern matching
        
        Args:
            source: Text source
            pattern: Regex pattern
            options: Optional extraction options
            
        Returns:
            Dictionary containing extraction results
        """
        try:
            # Compile pattern
            compiled_pattern = re.compile(
                pattern,
                re.MULTILINE | re.DOTALL
            )
            
            # Extract matches
            matches = compiled_pattern.findall(source)
            
            # Process matches
            processed_matches = await self._process_matches(
                matches,
                options or {}
            )
            
            return {
                "success": True,
                "pattern": pattern,
                "matches": processed_matches,
                "count": len(processed_matches)
            }
            
        except Exception as e:
            self.logger.error(f"Pattern extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract named entities from text
        
        Args:
            text: Input text
            entity_types: Optional list of entity types to extract
            options: Optional extraction options
            
        Returns:
            Dictionary containing extraction results
        """
        try:
            # Use spaCy for entity extraction
            model_size = options.get('model_size', 'small')
            nlp = self.nlp_models["spacy"][model_size]
            
            # Process text
            doc = nlp(text)
            
            # Extract entities
            entities = []
            for ent in doc.ents:
                if not entity_types or ent.label_ in entity_types:
                    entities.append({
                        "text": ent.text,
                        "type": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char
                    })
            
            return {
                "success": True,
                "entities": entities,
                "count": len(entities)
            }
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _extract_text_basic(
        self,
        source: Union[str, bytes],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Basic text extraction"""
        try:
            if isinstance(source, str):
                with open(source, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                text = source.decode('utf-8')
            
            # Clean text
            cleaned_text = self._clean_text(text, options)
            
            return {
                "text": cleaned_text,
                "length": len(cleaned_text)
            }
            
        except Exception as e:
            raise Exception(f"Basic text extraction failed: {str(e)}")

    async def _extract_table_structured(
        self,
        source: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract structured tables"""
        try:
            # Read tables using pandas
            tables = pd.read_html(source)
            
            processed_tables = []
            for idx, table in enumerate(tables):
                processed_table = await self._process_table(
                    table,
                    options
                )
                processed_tables.append({
                    "index": idx,
                    "data": processed_table
                })
            
            return {
                "tables": processed_tables,
                "count": len(processed_tables)
            }
            
        except Exception as e:
            raise Exception(f"Structured table extraction failed: {str(e)}")

    async def _extract_image_ocr(
        self,
        source: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract text from images using OCR"""
        try:
            # Load image
            image = Image.open(source)
            
            # Configure OCR
            config = options.get(
                'config',
                self.extraction_configs["ocr"]["config"]
            )
            lang = options.get(
                'lang',
                self.extraction_configs["ocr"]["lang"]
            )
            
            # Perform OCR
            text = pytesseract.image_to_string(
                image,
                lang=lang,
                config=config
            )
            
            # Extract additional data if requested
            data = {
                "text": text,
                "length": len(text)
            }
            
            if options.get('extract_boxes', False):
                boxes = pytesseract.image_to_boxes(image)
                data["boxes"] = boxes
                
            if options.get('extract_data', False):
                data["data"] = pytesseract.image_to_data(image)
            
            return data
            
        except Exception as e:
            raise Exception(f"OCR extraction failed: {str(e)}")

    async def _update_extraction_stats(
        self,
        data_type: str,
        success: bool,
        duration: float
    ) -> None:
        """Update extraction statistics"""
        try:
            stats = self.extraction_stats[data_type]
            
            # Update counters
            stats["extractions_performed"] += 1
            if success:
                stats["successful_extractions"] += 1
            else:
                stats["failed_extractions"] += 1
            
            # Update average duration
            total_extractions = stats["extractions_performed"]
            current_avg = stats["average_duration"]
            stats["average_duration"] = (
                (current_avg * (total_extractions - 1) + duration) /
                total_extractions
            )
            
            stats["last_extraction"] = datetime.now().isoformat()
            
            # Store metrics
            await db_utils.record_metric(
                agent_id=self.id,
                metric_type="data_extraction",
                value=duration,
                tags={
                    "data_type": data_type,
                    "success": success
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update extraction stats: {str(e)}")

# Global data extractor instance
data_extractor = DataExtractionAgent()
