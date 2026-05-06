"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ChatRequest(BaseModel):
    """Chat request model"""
    prompt: str = Field(..., min_length=1, max_length=1000, description="User query")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Show me the average temperature for all sensors in the last 24 hours",
                "session_id": "user-123-session-456"
            }
        }


class ChartConfig(BaseModel):
    """Chart configuration model"""
    type: str = Field(..., description="Chart type: line, bar, pie, scatter")
    x: Optional[str] = Field(None, description="X-axis field")
    y: Optional[str] = Field(None, description="Y-axis field")
    title: Optional[str] = Field(None, description="Chart title")
    labels: Optional[List[str]] = Field(None, description="Labels for pie charts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "line",
                "x": "timestamp",
                "y": "temperature",
                "title": "Temperature Over Time"
            }
        }


class SQLResponse(BaseModel):
    """SQL generation response model"""
    sql: str = Field(..., description="Generated SQL query")
    chart: Optional[ChartConfig] = Field(None, description="Chart configuration")
    explanation: Optional[str] = Field(None, description="Query explanation")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query results from MCP tool")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    source: Optional[str] = Field(None, description="Data source: cache or database")
    cached: Optional[bool] = Field(None, description="Whether data was cached")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT device_id, AVG(temperature) as avg_temp FROM logs WHERE timestamp > NOW() - INTERVAL '24 hours' GROUP BY device_id",
                "chart": {
                    "type": "bar",
                    "x": "device_id",
                    "y": "avg_temp",
                    "title": "Average Temperature by Device"
                },
                "explanation": "This query calculates the average temperature for each device in the last 24 hours",
                "data": [{"device_id": "SENSOR_001", "avg_temp": 22.5}],
                "row_count": 2,
                "source": "database",
                "cached": False
            }
        }


class ChatResponse(BaseModel):
    """Chat response model"""
    message: str = Field(..., description="Response message")
    sql: Optional[str] = Field(None, description="Generated SQL query")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query results")
    chart: Optional[ChartConfig] = Field(None, description="Chart configuration")
    source: Optional[str] = Field(None, description="Data source: cache or database")
    execution_time: Optional[float] = Field(None, description="Query execution time in seconds")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    explanation: Optional[str] = Field(None, description="Explanation of the query results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Here are the average temperatures for all sensors in the last 24 hours",
                "sql": "SELECT device_id, AVG(temperature) as avg_temp FROM logs WHERE timestamp > NOW() - INTERVAL '24 hours' GROUP BY device_id",
                "data": [
                    {"device_id": "SENSOR_001", "avg_temp": 22.5},
                    {"device_id": "SENSOR_002", "avg_temp": 23.1}
                ],
                "chart": {
                    "type": "bar",
                    "x": "device_id",
                    "y": "avg_temp",
                    "title": "Average Temperature by Device"
                },
                "source": "database",
                "execution_time": 0.125
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid SQL query",
                "detail": "Only SELECT statements are allowed",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
