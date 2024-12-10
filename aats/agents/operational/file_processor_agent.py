"""
File Processor Agent Implementation
This agent handles reading, processing, and analyzing large files of various formats
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
import json
import pandas as pd
import numpy as np
import docx
import PyPDF2
import csv
import xml.etree.ElementTree as ET
import yaml
import aiofiles
import magic
import chardet
from pathlib import Path
import dask.dataframe as dd
import pyarrow as pa
import pyarrow.parquet as pq

from ..base_agent import BaseAgent, AgentConfig
from ...config.settings.base_config import config
from ...integration.databases.utils import db_utils

class FileFormat(str):
    """File format definitions"""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    EXCEL = "excel"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    XML = "xml"
    YAML = "yaml"
    BINARY = "binary"

class ProcessingMode(str):
    """Processing mode definitions"""
    STREAMING = "streaming"
    BATCH = "batch"
    PARALLEL = "parallel"
    DISTRIBUTED = "distributed"

class FileProcessorAgent(BaseAgent):
    """
    File Processor Agent responsible for handling reading,
    processing, and analyzing large files.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="FileProcessor",
            description="Handles file processing and analysis",
            capabilities=[
                "large_file_processing",
                "format_conversion",
                "content_extraction",
                "data_analysis"
            ],
            required_tools=[
                "file_processor",
                "format_converter",
                "content_analyzer"
            ],
            max_concurrent_tasks=5,
            priority_level=2
        ))
        self.processing_stats: Dict[str, Dict] = {}
        self.format_handlers: Dict[str, callable] = {}
        self.chunk_size: int = 1024 * 1024  # 1MB default chunk size

    async def initialize(self) -> bool:
        """Initialize the File Processor Agent"""
        try:
            self.logger.info("Initializing File Processor Agent...")
            
            # Initialize format handlers
            await self._initialize_format_handlers()
            
            # Initialize processing stats
            await self._initialize_processing_stats()
            
            # Initialize processing queues
            await self._initialize_processing_queues()
            
            self.logger.info("File Processor Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize File Processor Agent: {str(e)}")
            return False

    async def _initialize_format_handlers(self) -> None:
        """Initialize format handlers"""
        try:
            self.format_handlers = {
                FileFormat.CSV: self._process_csv,
                FileFormat.JSON: self._process_json,
                FileFormat.PARQUET: self._process_parquet,
                FileFormat.EXCEL: self._process_excel,
                FileFormat.PDF: self._process_pdf,
                FileFormat.DOCX: self._process_docx,
                FileFormat.TXT: self._process_text,
                FileFormat.XML: self._process_xml,
                FileFormat.YAML: self._process_yaml,
                FileFormat.BINARY: self._process_binary
            }
            
            # Initialize format-specific configurations
            self.format_configs = {
                FileFormat.CSV: {
                    "chunk_size": 10000,  # rows
                    "encoding": "utf-8",
                    "compression": None
                },
                FileFormat.PARQUET: {
                    "row_group_size": 100000,
                    "compression": "snappy"
                },
                FileFormat.EXCEL: {
                    "sheet_size": 1000000,  # cells
                    "concurrent_sheets": 3
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize format handlers: {str(e)}")

    async def _initialize_processing_stats(self) -> None:
        """Initialize processing statistics"""
        try:
            self.processing_stats = {
                format_type: {
                    "files_processed": 0,
                    "total_bytes": 0,
                    "processing_time": 0.0,
                    "error_count": 0,
                    "last_processed": None
                }
                for format_type in FileFormat.__dict__.keys()
                if not format_type.startswith('_')
            }
            
            # Load historical stats
            stored_stats = await db_utils.get_agent_state(
                self.id,
                "processing_stats"
            )
            
            if stored_stats:
                self._merge_stats(stored_stats)
                
        except Exception as e:
            raise Exception(f"Failed to initialize processing stats: {str(e)}")

    async def _initialize_processing_queues(self) -> None:
        """Initialize processing queues"""
        try:
            # Set up queue configuration
            self.queue_config = {
                "max_queue_size": 1000,
                "batch_size": 10,
                "processing_timeout": 3600,  # 1 hour
                "retry_limit": 3
            }
            
            # Initialize queues
            self.processing_queues = {
                ProcessingMode.STREAMING: asyncio.Queue(),
                ProcessingMode.BATCH: asyncio.Queue(),
                ProcessingMode.PARALLEL: asyncio.Queue(),
                ProcessingMode.DISTRIBUTED: asyncio.Queue()
            }
            
        except Exception as e:
            raise Exception(f"Failed to initialize processing queues: {str(e)}")

    async def process_file(
        self,
        file_path: str,
        processing_mode: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a file
        
        Args:
            file_path: Path to the file
            processing_mode: Optional processing mode
            options: Optional processing options
            
        Returns:
            Dictionary containing processing results
        """
        try:
            # Detect file format
            file_format = await self._detect_format(file_path)
            
            # Get appropriate handler
            handler = self.format_handlers.get(file_format)
            if not handler:
                return {
                    "success": False,
                    "error": f"Unsupported format: {file_format}"
                }
            
            # Determine processing mode
            mode = processing_mode or self._determine_processing_mode(
                file_path,
                file_format
            )
            
            # Process file
            start_time = datetime.now()
            result = await handler(
                file_path,
                mode,
                options or {}
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update statistics
            await self._update_processing_stats(
                file_format,
                file_path,
                duration
            )
            
            return {
                "success": True,
                "format": file_format,
                "mode": mode,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"File processing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def convert_format(
        self,
        source_path: str,
        target_format: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Convert file format
        
        Args:
            source_path: Path to source file
            target_format: Target format
            options: Optional conversion options
            
        Returns:
            Dictionary containing conversion results
        """
        try:
            # Detect source format
            source_format = await self._detect_format(source_path)
            
            # Generate target path
            target_path = self._generate_target_path(
                source_path,
                target_format
            )
            
            # Convert file
            start_time = datetime.now()
            result = await self._convert_file(
                source_path,
                target_path,
                source_format,
                target_format,
                options or {}
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "source_format": source_format,
                "target_format": target_format,
                "target_path": target_path,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Format conversion failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_content(
        self,
        file_path: str,
        analysis_type: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze file content
        
        Args:
            file_path: Path to the file
            analysis_type: Type of analysis to perform
            options: Optional analysis options
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Detect format
            file_format = await self._detect_format(file_path)
            
            # Perform analysis
            start_time = datetime.now()
            result = await self._analyze_file(
                file_path,
                file_format,
                analysis_type,
                options or {}
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "format": file_format,
                "analysis_type": analysis_type,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Content analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _detect_format(self, file_path: str) -> str:
        """Detect file format"""
        try:
            # Use libmagic for initial detection
            mime_type = magic.from_file(file_path, mime=True)
            
            # Map mime types to formats
            format_mapping = {
                "text/csv": FileFormat.CSV,
                "application/json": FileFormat.JSON,
                "application/x-parquet": FileFormat.PARQUET,
                "application/vnd.ms-excel": FileFormat.EXCEL,
                "application/pdf": FileFormat.PDF,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileFormat.DOCX,
                "text/plain": FileFormat.TXT,
                "application/xml": FileFormat.XML,
                "application/x-yaml": FileFormat.YAML
            }
            
            return format_mapping.get(mime_type, FileFormat.BINARY)
            
        except Exception as e:
            self.logger.error(f"Format detection failed: {str(e)}")
            return FileFormat.BINARY

    async def _process_csv(
        self,
        file_path: str,
        mode: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process CSV file"""
        try:
            if mode == ProcessingMode.STREAMING:
                return await self._stream_csv(file_path, options)
            elif mode == ProcessingMode.BATCH:
                return await self._batch_process_csv(file_path, options)
            elif mode == ProcessingMode.PARALLEL:
                return await self._parallel_process_csv(file_path, options)
            else:
                return await self._distributed_process_csv(file_path, options)
                
        except Exception as e:
            raise Exception(f"CSV processing failed: {str(e)}")

    async def _process_parquet(
        self,
        file_path: str,
        mode: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Parquet file"""
        try:
            # Use PyArrow for efficient processing
            table = pq.read_table(file_path)
            
            if mode == ProcessingMode.STREAMING:
                return await self._stream_parquet(table, options)
            elif mode == ProcessingMode.BATCH:
                return await self._batch_process_parquet(table, options)
            else:
                return await self._parallel_process_parquet(table, options)
                
        except Exception as e:
            raise Exception(f"Parquet processing failed: {str(e)}")

    async def _process_pdf(
        self,
        file_path: str,
        mode: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process PDF file"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if mode == ProcessingMode.STREAMING:
                    return await self._stream_pdf(reader, options)
                else:
                    return await self._batch_process_pdf(reader, options)
                    
        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")

    async def _process_docx(
        self,
        file_path: str,
        mode: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process DOCX file"""
        try:
            doc = docx.Document(file_path)
            
            if mode == ProcessingMode.STREAMING:
                return await self._stream_docx(doc, options)
            else:
                return await self._batch_process_docx(doc, options)
                
        except Exception as e:
            raise Exception(f"DOCX processing failed: {str(e)}")

    async def _stream_csv(
        self,
        file_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stream process CSV file"""
        try:
            chunk_size = options.get('chunk_size', self.format_configs[FileFormat.CSV]["chunk_size"])
            results = []
            
            # Use pandas for chunked reading
            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                processed_chunk = await self._process_chunk(chunk, options)
                results.append(processed_chunk)
            
            return {
                "chunks_processed": len(results),
                "results": results
            }
            
        except Exception as e:
            raise Exception(f"CSV streaming failed: {str(e)}")

    async def _stream_parquet(
        self,
        table: pa.Table,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stream process Parquet file"""
        try:
            batch_size = options.get('batch_size', 10000)
            results = []
            
            # Process record batches
            for batch in table.to_batches(batch_size):
                processed_batch = await self._process_batch(batch, options)
                results.append(processed_batch)
            
            return {
                "batches_processed": len(results),
                "results": results
            }
            
        except Exception as e:
            raise Exception(f"Parquet streaming failed: {str(e)}")

    async def _update_processing_stats(
        self,
        format_type: str,
        file_path: str,
        duration: float
    ) -> None:
        """Update processing statistics"""
        try:
            stats = self.processing_stats[format_type]
            
            # Update counters
            stats["files_processed"] += 1
            stats["total_bytes"] += Path(file_path).stat().st_size
            stats["processing_time"] += duration
            stats["last_processed"] = datetime.now().isoformat()
            
            # Store updated stats
            await db_utils.record_metric(
                agent_id=self.id,
                metric_type="file_processing",
                value=duration,
                tags={
                    "format": format_type,
                    "file_size": Path(file_path).stat().st_size
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update processing stats: {str(e)}")

# Global file processor instance
file_processor = FileProcessorAgent()
