"""
Application-wide constants.

Centralizes magic numbers and configuration values used across the application.
"""

# Pagination and Query Limits
MAX_LIMIT = 1000
MIN_LIMIT = 1
MIN_OFFSET = 0

# Confidence Score Range
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0

# String Validation
EMPTY_WHITESPACE_THRESHOLD = 0  # Characters to consider empty after strip

# Risk Assessment Thresholds
RISK_SCORE_CRITICAL = 0.7
RISK_SCORE_HIGH = 0.5
RISK_SCORE_MEDIUM = 0.3

# Data Size Thresholds (bytes)
LARGE_PAYLOAD_THRESHOLD = 10000
