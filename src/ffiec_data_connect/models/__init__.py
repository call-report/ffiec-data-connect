"""
FFIEC REST API Response Models

This module contains Pydantic models auto-generated from the validated OpenAPI schema.
These models ensure type safety and runtime validation for all REST API responses.

Generated models provide:
- Runtime validation of API responses
- Type safety with proper hint support
- Schema compliance verification
- Clear error messages for data issues
"""

from .api_models import (  # Core data models; Response models; Binary data models
    Error,
    Institution,
    InstitutionsResponse,
    PDFData,
    ReportingPeriod,
    ReportingPeriodsResponse,
    RSSDIDsResponse,
    SDFData,
    SubmissionInfo,
    SubmissionsResponse,
    UBPRReportingPeriodsResponse,
    XBRLData,
)

__all__ = [
    # Core data models
    "Error",
    "Institution",
    "ReportingPeriod",
    "SubmissionInfo",
    # Response models
    "ReportingPeriodsResponse",
    "UBPRReportingPeriodsResponse",
    "InstitutionsResponse",
    "RSSDIDsResponse",
    "SubmissionsResponse",
    # Binary data models
    "XBRLData",
    "PDFData",
    "SDFData",
]
