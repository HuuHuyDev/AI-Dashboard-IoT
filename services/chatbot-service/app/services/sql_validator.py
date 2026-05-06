"""
SQL Validator Service - Security and Validation
Validates SQL queries to prevent dangerous operations and SQL injection
"""
import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


class SQLValidator:
    """
    SQL Validator để kiểm tra tính hợp lệ và bảo mật của SQL queries
    Ngăn chặn các câu lệnh nguy hiểm như DELETE, UPDATE, DROP, etc.
    """
    
    # Danh sách các từ khóa SQL nguy hiểm không được phép
    DANGEROUS_KEYWORDS = [
        'DELETE', 'DROP', 'UPDATE', 'INSERT', 'ALTER', 
        'TRUNCATE', 'GRANT', 'REVOKE', 'CREATE', 'EXECUTE',
        'EXEC', 'REPLACE', 'MERGE', 'CALL', 'RENAME'
    ]
    
    # Các pattern SQL injection phổ biến
    INJECTION_PATTERNS = [
        r'--',           # SQL comment
        r'/\*',          # Multi-line comment start
        r'\*/',          # Multi-line comment end
        r';.*',          # Multiple statements
        r'xp_',          # SQL Server extended procedures
        r'sp_',          # SQL Server stored procedures
        r'0x[0-9a-f]+',  # Hexadecimal values (potential injection)
    ]
    
    def __init__(self):
        """Initialize SQL Validator"""
        self.dangerous_keywords_pattern = '|'.join(
            [rf'\b{keyword}\b' for keyword in self.DANGEROUS_KEYWORDS]
        )
    
    def validate(self, sql: str) -> Tuple[bool, str]:
        """
        Validate SQL query cho security và correctness
        
        Args:
            sql: SQL query cần validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
                - is_valid: True nếu SQL hợp lệ, False nếu không
                - error_message: Thông báo lỗi nếu không hợp lệ, empty string nếu hợp lệ
        """
        try:
            # Kiểm tra SQL không rỗng
            if not sql or not sql.strip():
                return False, "SQL query cannot be empty"
            
            sql_normalized = sql.strip().upper()
            
            # 1. Kiểm tra SQL phải bắt đầu bằng SELECT
            if not self._is_select_statement(sql_normalized):
                logger.warning(f"Non-SELECT statement detected: {sql[:100]}")
                return False, "Only SELECT statements are allowed"
            
            # 2. Kiểm tra các từ khóa nguy hiểm
            dangerous_keyword = self._check_dangerous_keywords(sql_normalized)
            if dangerous_keyword:
                logger.error(f"Dangerous keyword detected: {dangerous_keyword} in SQL: {sql[:100]}")
                return False, f"Dangerous SQL keyword detected: {dangerous_keyword}. Only SELECT queries are allowed."
            
            # 3. Kiểm tra SQL injection patterns
            injection_pattern = self._check_injection_patterns(sql)
            if injection_pattern:
                logger.error(f"SQL injection pattern detected: {injection_pattern} in SQL: {sql[:100]}")
                return False, f"Potential SQL injection detected. Query rejected for security reasons."
            
            # 4. Kiểm tra multiple statements (phân tách bởi dấu ;)
            if self._has_multiple_statements(sql):
                logger.error(f"Multiple statements detected in SQL: {sql[:100]}")
                return False, "Multiple SQL statements are not allowed"
            
            # 5. Kiểm tra độ dài SQL (tránh queries quá dài)
            if len(sql) > 5000:
                logger.warning(f"SQL query too long: {len(sql)} characters")
                return False, "SQL query is too long (max 5000 characters)"
            
            # SQL hợp lệ
            logger.info(f"SQL validation passed: {sql[:100]}...")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error during SQL validation: {str(e)}", exc_info=True)
            return False, f"SQL validation error: {str(e)}"
    
    def _is_select_statement(self, sql_normalized: str) -> bool:
        """
        Kiểm tra SQL có phải là SELECT statement không
        
        Args:
            sql_normalized: SQL đã được normalize (uppercase, stripped)
            
        Returns:
            bool: True nếu là SELECT statement
        """
        # Loại bỏ whitespace và newlines ở đầu
        sql_clean = re.sub(r'^\s+', '', sql_normalized)
        return sql_clean.startswith('SELECT')
    
    def _check_dangerous_keywords(self, sql_normalized: str) -> str:
        """
        Kiểm tra các từ khóa SQL nguy hiểm
        
        Args:
            sql_normalized: SQL đã được normalize (uppercase)
            
        Returns:
            str: Từ khóa nguy hiểm nếu tìm thấy, empty string nếu không
        """
        # Sử dụng regex để tìm các từ khóa nguy hiểm (word boundary)
        match = re.search(self.dangerous_keywords_pattern, sql_normalized, re.IGNORECASE)
        if match:
            return match.group(0)
        return ""
    
    def _check_injection_patterns(self, sql: str) -> str:
        """
        Kiểm tra các pattern SQL injection phổ biến
        
        Args:
            sql: SQL query gốc
            
        Returns:
            str: Pattern injection nếu tìm thấy, empty string nếu không
        """
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                return pattern
        return ""
    
    def _has_multiple_statements(self, sql: str) -> bool:
        """
        Kiểm tra SQL có chứa nhiều statements không (phân tách bởi ;)
        
        Args:
            sql: SQL query
            
        Returns:
            bool: True nếu có nhiều statements
        """
        # Loại bỏ semicolon ở cuối (hợp lệ)
        sql_trimmed = sql.rstrip().rstrip(';')
        
        # Kiểm tra còn semicolon nào khác không
        return ';' in sql_trimmed
    
    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input trước khi đưa vào LLM prompt
        Loại bỏ các ký tự đặc biệt có thể gây prompt injection
        
        Args:
            user_input: Input từ user
            
        Returns:
            str: Sanitized input
        """
        # Loại bỏ các ký tự điều khiển
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_input)
        
        # Giới hạn độ dài
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
            logger.warning("User input truncated to 1000 characters")
        
        return sanitized.strip()
    
    def get_validation_summary(self) -> dict:
        """
        Lấy thông tin về các rules validation
        
        Returns:
            dict: Summary của validation rules
        """
        return {
            "allowed_statements": ["SELECT"],
            "blocked_keywords": self.DANGEROUS_KEYWORDS,
            "max_query_length": 5000,
            "injection_checks": [
                "SQL comments (-- and /* */)",
                "Multiple statements (;)",
                "Extended procedures (xp_, sp_)",
                "Hexadecimal injection"
            ]
        }


# Singleton instance
sql_validator = SQLValidator()
