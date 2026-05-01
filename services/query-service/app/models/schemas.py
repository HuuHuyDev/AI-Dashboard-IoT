"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime


class QueryRequest(BaseModel):
    """Query request model"""
    sql: str = Field(..., min_length=1, description="SQL query to execute")
    use_cache: bool = Field(True, description="Whether to use cache")
    
    @validator('sql')
    def validate_sql(cls, v):
        """Validate SQL query"""
        sql_upper = v.strip().upper()
        
        # Only allow SELECT statements
        if not sql_upper.startswith('SELECT'):
            raise ValueError("Only SELECT statements are allowed")
        
        # Prevent dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise ValueError(f"Dangerous keyword '{keyword}' is not allowed")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT device_id, AVG(temperature) as avg_temp FROM logs WHERE timestamp > NOW() - INTERVAL '24 hours' GROUP BY device_id",
                "use_cache": True
            }
        }


class QueryResponse(BaseModel):
    """Query response model"""
    data: List[Dict[str, Any]] = Field(..., description="Query results")
    row_count: int = Field(..., description="Number of rows returned")
    source: str = Field(..., description="Data source: cache or database")
    execution_time: Optional[float] = Field(None, description="Query execution time in seconds")
    cached: bool = Field(False, description="Whether result was cached")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {"device_id": "SENSOR_001", "avg_temp": 22.5},
                    {"device_id": "SENSOR_002", "avg_temp": 23.1}
                ],
                "row_count": 2,
                "source": "cache",
                "execution_time": 0.015,
                "cached": True
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
