# Requirements Document - MCP LLM Integration

## Introduction

Tính năng MCP LLM Integration cho phép chatbot-service sử dụng nhiều LLM providers (DeepSeek, Gemini) thông qua Model Context Protocol (MCP). Điều này giúp hệ thống linh hoạt hơn trong việc chọn provider miễn phí hoặc có chi phí thấp, đồng thời duy trì khả năng generate SQL từ natural language với function calling.

## Glossary

- **MCP_Client**: Component quản lý kết nối và giao tiếp với MCP servers
- **LLM_Provider**: Nhà cung cấp dịch vụ LLM (DeepSeek, Gemini)
- **Function_Calling**: Khả năng của LLM để gọi các function được định nghĩa trước
- **Provider_Adapter**: Component chuyển đổi giữa các format function calling của các providers khác nhau
- **Chatbot_Service**: Service xử lý natural language queries và generate SQL
- **LLM_Service**: Service hiện tại quản lý tương tác với Gemini API
- **SQL_Generator**: Component chịu trách nhiệm generate SQL từ natural language
- **Schema_Context**: Thông tin về database schema được cung cấp cho LLM
- **Cache_Manager**: Component quản lý caching của SQL queries trong Redis
- **SQL_Validator**: Component kiểm tra tính hợp lệ và bảo mật của SQL queries
- **Security_Logger**: Component ghi log các vi phạm bảo mật
- **Dangerous_Keywords**: Danh sách các SQL keywords không được phép (DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE, GRANT, REVOKE, CREATE, EXECUTE)

## Requirements

### Requirement 1: MCP Client Integration

**User Story:** As a developer, I want to integrate MCP client into the chatbot service, so that I can connect to multiple LLM providers through a unified protocol.

#### Acceptance Criteria

1. THE MCP_Client SHALL establish connections to MCP servers for LLM providers
2. WHEN a connection fails, THE MCP_Client SHALL log the error and attempt reconnection with exponential backoff
3. THE MCP_Client SHALL maintain connection health checks with 30-second intervals
4. THE MCP_Client SHALL support configuration of multiple MCP server endpoints through environment variables
5. WHEN the service starts, THE MCP_Client SHALL initialize all configured provider connections

### Requirement 2: Multi-Provider Support

**User Story:** As a system administrator, I want to configure multiple LLM providers, so that I can choose between DeepSeek and Gemini based on cost and availability.

#### Acceptance Criteria

1. THE Provider_Adapter SHALL support DeepSeek API integration
2. THE Provider_Adapter SHALL support Gemini API integration
3. WHERE a provider is configured, THE Provider_Adapter SHALL validate the API key on initialization
4. THE Provider_Adapter SHALL allow runtime switching between providers through configuration
5. WHEN a provider is unavailable, THE Provider_Adapter SHALL fallback to the next configured provider

### Requirement 3: Function Calling Abstraction

**User Story:** As a developer, I want a unified function calling interface, so that SQL generation works consistently across different LLM providers.

#### Acceptance Criteria

1. THE Provider_Adapter SHALL normalize function calling requests to a common format
2. THE Provider_Adapter SHALL convert provider-specific function calling responses to a unified format
3. THE SQL_Generator SHALL define function schema for SQL generation that works across all providers
4. WHEN a provider does not support function calling, THE Provider_Adapter SHALL use structured prompting as fallback
5. THE Provider_Adapter SHALL validate function calling responses before returning to the caller

### Requirement 4: SQL Generation with MCP

**User Story:** As a user, I want to query data using natural language, so that I can get insights without writing SQL.

#### Acceptance Criteria

1. WHEN a natural language query is received, THE SQL_Generator SHALL send it to the configured LLM provider through MCP
2. THE SQL_Generator SHALL include Schema_Context in every LLM request
3. THE SQL_Generator SHALL validate that generated SQL is a SELECT statement only
4. THE SQL_Generator SHALL extract SQL query, explanation, and chart configuration from LLM response
5. WHEN SQL generation fails, THE SQL_Generator SHALL return a descriptive error message
6. THE SQL_Generator SHALL perform security validation on generated SQL before returning results
7. WHEN generated SQL contains dangerous keywords, THE SQL_Generator SHALL reject the query and log the security violation
8. THE SQL_Generator SHALL validate SQL syntax before execution
9. WHEN a malicious prompt is detected, THE SQL_Generator SHALL reject the request and return a security error message
10. THE SQL_Generator SHALL sanitize all user inputs before including them in LLM prompts

### Requirement 5: Provider Configuration Management

**User Story:** As a system administrator, I want to configure LLM providers through environment variables, so that I can easily switch providers without code changes.

#### Acceptance Criteria

1. THE Chatbot_Service SHALL read provider configuration from environment variables on startup
2. THE Chatbot_Service SHALL support configuration of provider priority order
3. THE Chatbot_Service SHALL support configuration of provider-specific parameters (model name, temperature, max tokens)
4. WHERE no provider is configured, THE Chatbot_Service SHALL fail startup with a clear error message
5. THE Chatbot_Service SHALL validate all provider configurations before accepting requests

### Requirement 6: Caching Compatibility

**User Story:** As a developer, I want to maintain existing caching functionality, so that repeated queries remain fast and cost-effective.

#### Acceptance Criteria

1. THE Cache_Manager SHALL generate cache keys based on normalized prompts regardless of provider
2. WHEN a cached result exists, THE SQL_Generator SHALL return it without calling the LLM provider
3. THE Cache_Manager SHALL store provider name with cached results for debugging
4. THE Cache_Manager SHALL respect the configured SQL_CACHE_TTL value
5. WHEN cache operations fail, THE SQL_Generator SHALL continue with LLM provider without caching

### Requirement 7: Error Handling and Fallback

**User Story:** As a user, I want the system to handle provider failures gracefully, so that I can still get results even when one provider is down.

#### Acceptance Criteria

1. WHEN the primary provider fails, THE Provider_Adapter SHALL attempt the request with the fallback provider
2. THE Provider_Adapter SHALL log all provider failures with error details
3. IF all providers fail, THEN THE SQL_Generator SHALL return a user-friendly error message
4. THE Provider_Adapter SHALL track provider failure rates for monitoring
5. WHEN a provider returns invalid responses three consecutive times, THE Provider_Adapter SHALL temporarily disable that provider for 5 minutes

### Requirement 8: Response Format Compatibility

**User Story:** As a developer, I want to maintain backward compatibility with existing response formats, so that frontend applications continue to work without changes.

#### Acceptance Criteria

1. THE SQL_Generator SHALL return SQLResponse objects with the same structure as the current implementation
2. THE SQL_Generator SHALL generate ChartConfig objects compatible with existing chart rendering logic
3. THE Chatbot_Service SHALL return ChatResponse objects with the same structure as the current implementation
4. THE SQL_Generator SHALL preserve explanation text format for user display
5. THE SQL_Generator SHALL maintain support for all existing chart types (line, bar, pie, scatter, table)

### Requirement 9: DeepSeek API Integration

**User Story:** As a system administrator, I want to use DeepSeek API as a free alternative, so that I can reduce LLM costs.

#### Acceptance Criteria

1. THE Provider_Adapter SHALL support DeepSeek API authentication with API keys
2. THE Provider_Adapter SHALL use DeepSeek's function calling format when available
3. THE Provider_Adapter SHALL configure DeepSeek model name through environment variables
4. THE Provider_Adapter SHALL handle DeepSeek-specific rate limits with retry logic
5. WHEN DeepSeek API returns errors, THE Provider_Adapter SHALL parse and log error details

### Requirement 10: Monitoring and Observability

**User Story:** As a system administrator, I want to monitor LLM provider usage and performance, so that I can optimize costs and reliability.

#### Acceptance Criteria

1. THE LLM_Service SHALL log every LLM request with provider name, prompt length, and response time
2. THE LLM_Service SHALL track cache hit rate for SQL generation
3. THE Provider_Adapter SHALL log provider switching events with reasons
4. THE LLM_Service SHALL expose metrics for provider request counts and error rates
5. WHEN a provider response time exceeds 10 seconds, THE LLM_Service SHALL log a performance warning

### Requirement 11: Schema Context Management

**User Story:** As a developer, I want to manage database schema context efficiently, so that LLM providers have accurate information for SQL generation.

#### Acceptance Criteria

1. THE SQL_Generator SHALL load Schema_Context from a configuration file on startup
2. THE SQL_Generator SHALL include table names, column names, and data types in Schema_Context
3. THE SQL_Generator SHALL include common query patterns in Schema_Context
4. THE SQL_Generator SHALL support updating Schema_Context without service restart
5. THE Schema_Context SHALL be under 2000 tokens to optimize LLM context usage

### Requirement 12: Provider-Specific Prompt Engineering

**User Story:** As a developer, I want to optimize prompts for each provider, so that I get the best SQL generation quality from each LLM.

#### Acceptance Criteria

1. THE Provider_Adapter SHALL support provider-specific system prompts
2. THE Provider_Adapter SHALL support provider-specific few-shot examples
3. WHERE a provider has specific prompt requirements, THE Provider_Adapter SHALL apply them automatically
4. THE Provider_Adapter SHALL maintain a base prompt template shared across all providers
5. THE Provider_Adapter SHALL allow prompt customization through configuration files

### Requirement 13: SQL Security and Validation

**User Story:** As a system administrator, I want to protect the database from malicious queries, so that users cannot delete, modify, or corrupt data through the chatbot interface.

#### Acceptance Criteria

1. THE SQL_Validator SHALL maintain a blacklist of Dangerous_Keywords
2. WHEN validating SQL, THE SQL_Validator SHALL check for Dangerous_Keywords before execution
3. THE SQL_Validator SHALL reject SQL containing any of: DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE, GRANT, REVOKE, CREATE, EXECUTE
4. THE SQL_Validator SHALL perform case-insensitive keyword matching to detect obfuscated dangerous keywords
5. WHEN a dangerous keyword is detected, THE SQL_Validator SHALL immediately reject the query without execution
6. THE Security_Logger SHALL log all rejected queries with timestamp, user context, and detected violation
7. THE SQL_Validator SHALL verify that SQL starts with SELECT keyword after whitespace normalization
8. THE SQL_Validator SHALL detect and reject SQL injection patterns including comment sequences (-- and /* */)
9. THE SQL_Validator SHALL detect and reject queries with multiple statements separated by semicolons
10. WHEN SQL validation fails, THE SQL_Generator SHALL return an error message indicating security policy violation
11. THE SQL_Validator SHALL parse SQL syntax to detect nested dangerous keywords in subqueries
12. THE Security_Logger SHALL track violation attempts per session for rate limiting
13. WHEN a session exceeds 3 security violations within 5 minutes, THE Chatbot_Service SHALL temporarily block that session
14. THE SQL_Validator SHALL validate that all table names in generated SQL match tables in Schema_Context
15. THE SQL_Validator SHALL complete validation within 50 milliseconds to maintain response time performance