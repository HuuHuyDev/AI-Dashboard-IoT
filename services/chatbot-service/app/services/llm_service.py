"""
LLM Service - Google Gemini Integration with Function Calling
Generates SQL queries from natural language using function calling
"""
import logging
import json
import hashlib
from typing import Optional
import google.generativeai as genai

from app.models.schemas import SQLResponse, ChartConfig
from app.core.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service for SQL generation using Google Gemini with function calling"""
    
    # Database schema information for context
    SCHEMA_CONTEXT = """
    Available Tables:
    
    1. devices (device_id, device_name, device_type, location, status, metadata, created_at, updated_at)
    2. logs (log_id, device_id, timestamp, temperature, humidity, pressure, battery_level, signal_strength, status, metadata, created_at)
    3. daily_stats (stat_id, device_id, date, avg_temperature, min_temperature, max_temperature, avg_humidity, min_humidity, max_humidity, avg_pressure, min_pressure, max_pressure, avg_battery_level, min_battery_level, max_battery_level, record_count, created_at, updated_at)
    4. alerts (alert_id, device_id, alert_type, severity, message, threshold_value, actual_value, timestamp, acknowledged, resolved, metadata, created_at)
    
    Common Queries:
    - Temperature, humidity, pressure readings from logs table
    - Device information from devices table
    - Aggregated statistics from daily_stats table
    - Alert information from alerts table
    """
    
    SYSTEM_PROMPT = f"""You are an expert SQL query generator for an IoT dashboard system.
    
    {SCHEMA_CONTEXT}
    
    Rules:
    1. ONLY generate SELECT statements (no INSERT, UPDATE, DELETE, DROP, etc.)
    2. Use PostgreSQL syntax
    3. Always include proper WHERE clauses for time-based queries
    4. Use appropriate JOINs when querying multiple tables
    5. Use aggregate functions (AVG, MIN, MAX, COUNT, SUM) when appropriate
    6. Always use proper date/time functions (NOW(), INTERVAL, DATE_TRUNC, etc.)
    7. Limit results to reasonable amounts (use LIMIT clause)
    8. Use proper column aliases for readability
    
    When generating queries:
    - For "last X hours/days": Use WHERE timestamp > NOW() - INTERVAL 'X hours/days'
    - For "today": Use WHERE DATE(timestamp) = CURRENT_DATE
    - For "yesterday": Use WHERE DATE(timestamp) = CURRENT_DATE - INTERVAL '1 day'
    - For averages: Use AVG() with GROUP BY
    - For trends: Include timestamp in results and ORDER BY timestamp
    
    Also determine the best chart type:
    - line: Time series data, trends over time
    - bar: Comparisons between categories, aggregated values by device
    - pie: Proportions, percentages, distribution
    - scatter: Correlation between two variables
    """
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL
        self.temperature = settings.GEMINI_TEMPERATURE
        self.max_tokens = settings.GEMINI_MAX_TOKENS
        
        # Initialize model with generation config
        self.generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        
        # Define function declaration for Gemini
        self.generate_sql_function = {
            "name": "generate_sql",
            "description": "Generate a SQL query based on natural language input",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The generated SQL SELECT query"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of what the query does"
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["line", "bar", "pie", "scatter", "table"],
                        "description": "Recommended chart type for visualization"
                    },
                    "x_axis": {
                        "type": "string",
                        "description": "Column name for X-axis (if applicable)"
                    },
                    "y_axis": {
                        "type": "string",
                        "description": "Column name for Y-axis (if applicable)"
                    },
                    "chart_title": {
                        "type": "string",
                        "description": "Suggested title for the chart"
                    }
                },
                "required": ["sql", "explanation", "chart_type"]
            }
        }
        
        # Initialize model with tools
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            tools=[self.generate_sql_function]
        )
    
    async def generate_sql(self, prompt: str) -> SQLResponse:
        """
        Generate SQL query from natural language prompt using Gemini function calling
        
        Args:
            prompt: User's natural language query
            
        Returns:
            SQLResponse with SQL query and chart configuration
        """
        try:
            # Check cache first
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            cache_key = f"sql_cache:{prompt_hash}"
            
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for prompt: {prompt[:50]}...")
                cached_data = json.loads(cached_result)
                return SQLResponse(**cached_data)
            
            # Prepare the full prompt with system context
            full_prompt = f"{self.SYSTEM_PROMPT}\n\nUser Query: {prompt}"
            
            # Start chat session
            chat = self.model.start_chat(enable_automatic_function_calling=False)
            
            # Send message
            response = chat.send_message(full_prompt)
            
            # Check if function call was made
            if not response.candidates:
                logger.warning("No candidates in response")
                return SQLResponse(
                    sql="",
                    chart=None,
                    explanation="Could not generate SQL query"
                )
            
            candidate = response.candidates[0]
            
            # Check for function calls in the response
            if not candidate.content.parts:
                logger.warning("No parts in candidate content")
                return SQLResponse(
                    sql="",
                    chart=None,
                    explanation="Could not generate SQL query"
                )
            
            # Extract function call
            function_call = None
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                    break
            
            if not function_call:
                logger.warning("No function call in response")
                return SQLResponse(
                    sql="",
                    chart=None,
                    explanation="Could not generate SQL query"
                )
            
            # Extract function arguments
            function_args = {}
            for key, value in function_call.args.items():
                function_args[key] = value
            
            # Validate SQL (basic check)
            sql = function_args.get("sql", "").strip()
            if not sql.upper().startswith("SELECT"):
                logger.error(f"Invalid SQL generated: {sql}")
                raise ValueError("Only SELECT queries are allowed")
            
            # Build chart configuration
            chart = None
            if function_args.get("chart_type") != "table":
                chart = ChartConfig(
                    type=function_args.get("chart_type", "bar"),
                    x=function_args.get("x_axis"),
                    y=function_args.get("y_axis"),
                    title=function_args.get("chart_title")
                )
            
            response = SQLResponse(
                sql=sql,
                chart=chart,
                explanation=function_args.get("explanation")
            )
            
            # Cache the result
            try:
                cache_data = response.model_dump()
                await redis_client.set(
                    cache_key,
                    json.dumps(cache_data, default=str),
                    ttl=settings.SQL_CACHE_TTL
                )
                logger.info(f"Cached SQL for prompt: {prompt[:50]}...")
            except Exception as cache_error:
                logger.warning(f"Failed to cache result: {cache_error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating SQL with Gemini: {str(e)}", exc_info=True)
            raise Exception(f"Failed to generate SQL: {str(e)}")
