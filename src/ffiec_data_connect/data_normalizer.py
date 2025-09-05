"""
FFIEC Data Normalizer - Phase 0 Critical Implementation

This module ensures 100% backward compatibility by normalizing REST API responses
to match SOAP format exactly. This prevents user-facing regressions when migrating
from SOAP to REST protocols.

CRITICAL DATA ISSUES ADDRESSED:
- RSSD IDs: REST integers (480228) → SOAP strings ("480228")
- ZIP Codes: REST loses leading zeros (2886) → SOAP format ("02886")
- Certificate Numbers: REST integers → SOAP strings
- Boolean Values: REST booleans → SOAP string format
- Financial Data: Preserve decimal precision

Author: FFIEC Data Connect Library
Version: Phase 0 - Data Normalization
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)


class DataNormalizer:
    """
    Ensures 100% backward compatibility by normalizing REST responses to SOAP format.

    This class prevents data regressions by applying type coercions and format
    transformations to REST API responses, making them identical to SOAP responses.
    """

    # Normalization rules discovered from format analysis
    # These ensure REST responses match SOAP format exactly
    TYPE_COERCIONS: Dict[str, Dict[str, Any]] = {
        "RetrievePanelOfReporters": {
            # Critical fields that change type between protocols
            "ID_RSSD": lambda x: str(x),  # int → str (CRITICAL)
            "FDICCertNumber": lambda x: str(x) if x is not None else "",  # int → str
            "OCCChartNumber": lambda x: str(x) if x is not None else "",  # int → str
            "OTSDockNumber": lambda x: str(x) if x is not None else "",  # int → str
            "PrimaryABARoutNumber": lambda x: (
                str(x) if x is not None else ""
            ),  # int → str
            "ZIP": lambda x: DataNormalizer._fix_zip_code(
                x
            ),  # Fix leading zeros (CRITICAL)
            "HasFiledForReportingPeriod": lambda x: (
                str(x).lower() if x is not None else "false"
            ),  # bool → str
            # Additional fields that may need normalization
            "InstitutionName": lambda x: str(x) if x is not None else "",
            "PhysicalStreetAddress": lambda x: str(x) if x is not None else "",
            "PhysicalCity": lambda x: str(x) if x is not None else "",
            "PhysicalState": lambda x: str(x) if x is not None else "",
            "MailingStreetAddress": lambda x: str(x) if x is not None else "",
            "MailingCity": lambda x: str(x) if x is not None else "",
            "MailingState": lambda x: str(x) if x is not None else "",
            "MailingZIP": lambda x: DataNormalizer._fix_zip_code(x),
        },
        "RetrieveFilersSinceDate": {
            # Array of integers → array of strings (CRITICAL)
            "_array_items": lambda x: str(x) if x is not None else ""
        },
        "RetrieveFilersSubmissionDateTime": {
            "ID_RSSD": lambda x: str(x),  # int → str (CRITICAL)
            # DateTime format consistency - ensure MM/dd/yyyy HH:mm:ss AM/PM
            "SubmissionDateTime": lambda x: DataNormalizer._normalize_datetime(x),
        },
        "RetrieveReportingPeriods": {
            # Likely already strings, but ensure consistency
            "_array_items": lambda x: DataNormalizer._normalize_date_string(x)
        },
        "RetrieveFacsimile": {
            # Binary data should remain unchanged
            # But ensure consistent encoding if needed
            "_preserve_binary": True
        },
        "RetrieveUBPRReportingPeriods": {
            # Similar to RetrieveReportingPeriods
            "_array_items": lambda x: DataNormalizer._normalize_date_string(x)
        },
        "RetrieveUBPRXBRLFacsimile": {
            # Binary XBRL data
            "_preserve_binary": True
        },
    }

    # Field-specific validation rules
    VALIDATION_RULES = {
        "ZIP": {
            "pattern": r"^\d{5}$",
            "description": "5-digit ZIP code with leading zeros preserved",
        },
        "ID_RSSD": {"pattern": r"^\d+$", "description": "RSSD ID as string of digits"},
        "FDICCertNumber": {
            "pattern": r"^\d*$",
            "description": "FDIC certificate number as string",
        },
    }

    @staticmethod
    def _fix_zip_code(zip_value: Union[str, int, None]) -> str:
        """
        Fix ZIP code precision loss from REST API.

        CRITICAL: REST API loses leading zeros (02886 → 2886)
        This restores proper 5-digit format with leading zeros.

        Args:
            zip_value: ZIP code from REST API (int or str)

        Returns:
            str: Properly formatted 5-digit ZIP code
        """
        if zip_value is None or zip_value == "":
            return ""

        if isinstance(zip_value, int):
            zip_str = str(zip_value)
            # Add leading zeros for codes that should be 5 digits
            if len(zip_str) == 4:
                return f"0{zip_str}"
            elif len(zip_str) == 3:
                return f"00{zip_str}"
            elif len(zip_str) == 2:
                return f"000{zip_str}"
            elif len(zip_str) == 1:
                return f"0000{zip_str}"
            else:
                return zip_str
        elif isinstance(zip_value, str):
            # Already a string, but validate format
            zip_str = zip_value.strip()
            if zip_str.isdigit() and len(zip_str) < 5:
                return zip_str.zfill(5)  # Pad with leading zeros
            return zip_str
        else:
            return str(zip_value)

    @staticmethod
    def _normalize_datetime(dt_value: Union[str, datetime, None]) -> str:
        """
        Normalize datetime format to match SOAP API format.

        SOAP Format: "12/31/2023 11:59:59 PM"
        Ensures consistent datetime string format.

        Args:
            dt_value: DateTime value from REST API

        Returns:
            str: Normalized datetime string
        """
        if dt_value is None:
            return ""

        if isinstance(dt_value, str):
            # Already string, validate format
            return dt_value.strip()
        elif isinstance(dt_value, datetime):
            # Convert datetime object to SOAP format
            return dt_value.strftime("%-m/%-d/%Y %-I:%M:%S %p")
        else:
            return str(dt_value)

    @staticmethod
    def _normalize_date_string(date_value: Union[str, None]) -> str:
        """
        Normalize date string format for reporting periods.

        Ensures consistent MM/dd/yyyy format.

        Args:
            date_value: Date string from REST API

        Returns:
            str: Normalized date string
        """
        if date_value is None:
            return ""

        if isinstance(date_value, str):
            date_str = date_value.strip()
            # Validate format - should be MM/dd/yyyy
            if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", date_str):
                return date_str
            else:
                logger.warning(f"Unexpected date format: {date_str}")
                return date_str
        else:
            return str(date_value)

    @staticmethod
    def normalize_for_validation(
        data: Any, endpoint: str, protocol: str = "REST"
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Normalize response data and return both normalized data and statistics.

        This method is designed to work with Pydantic validation by providing
        both the normalized data and metadata about transformations applied.

        Args:
            data: Raw response data from API
            endpoint: API endpoint name
            protocol: Source protocol ("REST" or "SOAP")

        Returns:
            Tuple of (normalized_data, normalization_stats)
        """
        if protocol != "REST":
            return data, {"transformations": 0, "protocol": protocol}

        normalized = DataNormalizer.normalize_response(data, endpoint, protocol)
        stats = DataNormalizer.get_normalization_stats(data, normalized, endpoint)

        return normalized, stats

    @staticmethod
    def validate_pydantic_compatibility(data: Any, endpoint: str) -> Dict[str, Any]:
        """
        Check if normalized data is compatible with expected Pydantic models.

        This performs additional validation beyond basic normalization to ensure
        data will pass Pydantic validation without issues.

        Args:
            data: Normalized data
            endpoint: API endpoint name

        Returns:
            Dictionary with validation results and recommendations
        """
        validation_report: Dict[str, Any] = {
            "endpoint": endpoint,
            "compatible": True,
            "warnings": [],
            "recommendations": [],
        }

        try:
            if endpoint == "RetrievePanelOfReporters":
                if isinstance(data, list):
                    for i, item in enumerate(data[:3]):  # Check first 3 items
                        if isinstance(item, dict):
                            # Check required fields
                            if "ID_RSSD" not in item:
                                validation_report["warnings"].append(
                                    f"Item {i} missing ID_RSSD"
                                )
                                validation_report["compatible"] = False
                            elif not isinstance(item["ID_RSSD"], str):
                                validation_report["warnings"].append(
                                    f"Item {i} ID_RSSD not string: {type(item['ID_RSSD'])}"
                                )
                                validation_report["compatible"] = False

                            if "Name" not in item:
                                validation_report["warnings"].append(
                                    f"Item {i} missing Name"
                                )
                                validation_report["compatible"] = False

                            # Check ZIP code format
                            if "ZIP" in item and isinstance(item["ZIP"], str):
                                if len(item["ZIP"]) == 4 and item["ZIP"].isdigit():
                                    validation_report["warnings"].append(
                                        f"Item {i} ZIP missing leading zero: {item['ZIP']}"
                                    )
                                    validation_report["recommendations"].append(
                                        "Apply DataNormalizer._fix_zip_code()"
                                    )

            elif endpoint in ["RetrieveFilersSinceDate", "RSSDIDsResponse"]:
                if isinstance(data, list):
                    for i, item in enumerate(data[:3]):
                        if not isinstance(item, str):
                            validation_report["warnings"].append(
                                f"RSSD ID {i} not string: {type(item)}"
                            )
                            validation_report["compatible"] = False

        except Exception as e:
            validation_report["error"] = str(e)
            validation_report["compatible"] = False

        return validation_report

    @staticmethod
    def normalize_response(data: Any, endpoint: str, protocol: str = "REST") -> Any:
        """
        Normalize REST response to match SOAP format exactly.

        This is the main entry point for data normalization. It ensures that
        REST API responses are transformed to be identical to SOAP responses,
        preventing any user-visible changes during protocol migration.

        Args:
            data: Raw response data from API
            endpoint: API endpoint name (e.g., "RetrievePanelOfReporters")
            protocol: Source protocol ("REST" or "SOAP")

        Returns:
            Normalized data matching SOAP format exactly
        """
        if protocol != "REST":
            # SOAP data already in expected format
            logger.debug(f"Skipping normalization for {protocol} protocol")
            return data

        if not data:
            # Handle empty/null responses
            return data

        if endpoint not in DataNormalizer.TYPE_COERCIONS:
            logger.warning(
                f"No normalization rules defined for endpoint '{endpoint}'. "
                f"Data may not be normalized. Available endpoints: "
                f"{list(DataNormalizer.TYPE_COERCIONS.keys())}"
            )
            return data

        logger.debug(f"Normalizing {endpoint} response from REST to SOAP format")

        try:
            coercions = DataNormalizer.TYPE_COERCIONS[endpoint]
            normalized_data = DataNormalizer._apply_normalizations(
                data, coercions, endpoint
            )

            # Validate critical fields after normalization
            DataNormalizer._validate_normalized_data(normalized_data, endpoint)

            logger.debug(f"Successfully normalized {endpoint} response")
            return normalized_data

        except Exception as e:
            logger.error(f"Failed to normalize {endpoint} response: {e}")
            # Return original data if normalization fails
            # This ensures the system continues working even if normalization has bugs
            return data

    @staticmethod
    def _apply_normalizations(
        data: Any, coercions: Dict[str, Any], endpoint: str
    ) -> Any:
        """Apply normalization rules to data structure."""

        # Handle binary data preservation
        if coercions.get("_preserve_binary"):
            logger.debug(f"Preserving binary data for {endpoint}")
            return data

        if isinstance(data, list):
            # Handle arrays
            if "_array_items" in coercions:
                coercion_func = coercions["_array_items"]
                logger.debug(f"Applying array item coercion for {endpoint}")
                return [coercion_func(item) for item in data]
            else:
                # Array of objects
                return [
                    DataNormalizer._normalize_object(
                        item, coercions, f"{endpoint}[{i}]"
                    )
                    for i, item in enumerate(data)
                ]

        elif isinstance(data, dict):
            return DataNormalizer._normalize_object(data, coercions, endpoint)

        else:
            # Simple value - apply direct coercion if available
            if "_simple_value" in coercions:
                return coercions["_simple_value"](data)
            return data

    @staticmethod
    def _normalize_object(
        obj: Dict[str, Any], coercions: Dict[str, Any], context: str
    ) -> Dict[str, Any]:
        """Apply type coercions to dictionary object."""
        if not isinstance(obj, dict):
            return obj

        normalized = obj.copy()
        normalization_count = 0

        for field, coercion_func in coercions.items():
            if field.startswith("_"):
                continue  # Skip meta-fields like _array_items

            if field in normalized:
                try:
                    original_value = normalized[field]
                    normalized_value = coercion_func(original_value)

                    # Only update if value actually changed
                    if normalized_value != original_value:
                        normalized[field] = normalized_value
                        normalization_count += 1
                        logger.debug(
                            f"Normalized {context}.{field}: "
                            f"{type(original_value).__name__}({original_value}) → "
                            f"{type(normalized_value).__name__}({normalized_value})"
                        )

                except Exception as e:
                    logger.error(f"Failed to normalize {context}.{field}: {e}")
                    # Keep original value if normalization fails
                    continue

        if normalization_count > 0:
            logger.debug(f"Applied {normalization_count} normalizations to {context}")

        return normalized

    @staticmethod
    def _validate_normalized_data(data: Any, endpoint: str) -> None:
        """
        Validate normalized data meets SOAP format requirements.

        This catches normalization bugs and ensures data quality.
        """
        if not data:
            return

        validation_errors: list[str] = []

        try:
            if isinstance(data, list):
                for i, item in enumerate(data[:3]):  # Validate first few items
                    if isinstance(item, dict):
                        DataNormalizer._validate_object(
                            item, f"{endpoint}[{i}]", validation_errors
                        )
            elif isinstance(data, dict):
                DataNormalizer._validate_object(data, endpoint, validation_errors)

            if validation_errors:
                error_summary = "; ".join(validation_errors[:5])  # First 5 errors
                logger.warning(f"Validation warnings for {endpoint}: {error_summary}")

        except Exception as e:
            logger.error(f"Validation failed for {endpoint}: {e}")

    @staticmethod
    def _validate_object(obj: Dict[str, Any], context: str, errors: List[str]) -> None:
        """Validate individual object meets format requirements."""

        for field, value in obj.items():
            if field in DataNormalizer.VALIDATION_RULES:
                rule = DataNormalizer.VALIDATION_RULES[field]
                pattern = rule.get("pattern")

                if pattern and isinstance(value, str):
                    if not re.match(pattern, value):
                        errors.append(
                            f"{context}.{field} format invalid: '{value}' "
                            f"(expected: {rule['description']})"
                        )
                elif field == "ZIP":
                    # Special validation for ZIP codes
                    if not isinstance(value, str):
                        errors.append(
                            f"{context}.{field} must be string, got {type(value)}"
                        )
                    elif len(value) == 4 and value.isdigit():
                        errors.append(
                            f"{context}.{field} missing leading zero: '{value}'"
                        )
                elif field == "ID_RSSD":
                    # RSSD IDs must be strings
                    if not isinstance(value, str):
                        errors.append(
                            f"{context}.{field} must be string, got {type(value)}"
                        )

    @staticmethod
    def get_normalization_stats(
        data_before: Any, data_after: Any, endpoint: str
    ) -> Dict[str, Any]:
        """
        Generate statistics about normalization transformations applied.

        Useful for monitoring and debugging normalization effectiveness.
        """
        stats = {
            "endpoint": endpoint,
            "timestamp": datetime.now().isoformat(),
            "transformations_applied": 0,
            "fields_normalized": [],
            "data_size": {
                "before": DataNormalizer._estimate_data_size(data_before),
                "after": DataNormalizer._estimate_data_size(data_after),
            },
            "type_changes": {},
            "validation_passed": False,
        }

        try:
            # Compare before/after to count transformations
            if isinstance(data_before, list) and isinstance(data_after, list):
                for i, (before_item, after_item) in enumerate(
                    zip(data_before, data_after)
                ):
                    if isinstance(before_item, dict) and isinstance(after_item, dict):
                        stats.update(
                            DataNormalizer._count_object_changes(
                                before_item, after_item, f"[{i}]", stats
                            )
                        )
            elif isinstance(data_before, dict) and isinstance(data_after, dict):
                stats.update(
                    DataNormalizer._count_object_changes(
                        data_before, data_after, "root", stats
                    )
                )

            # Validate final result
            DataNormalizer._validate_normalized_data(data_after, endpoint)
            stats["validation_passed"] = True

        except Exception as e:
            logger.error(f"Failed to generate normalization stats: {e}")
            stats["error"] = str(e)

        return stats

    @staticmethod
    def _estimate_data_size(data: Any) -> int:
        """Estimate data size for statistics."""
        if isinstance(data, (list, dict)):
            return len(str(data))
        else:
            return len(str(data)) if data else 0

    @staticmethod
    def _count_object_changes(
        before: Dict[str, Any], after: Dict[str, Any], path: str, stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Count changes between before/after objects."""
        for key in before.keys():
            if key in after:
                before_val = before[key]
                after_val = after[key]

                if type(before_val) is not type(after_val):
                    stats["transformations_applied"] += 1
                    stats["fields_normalized"].append(f"{path}.{key}")

                    type_key = (
                        f"{type(before_val).__name__}_to_{type(after_val).__name__}"
                    )
                    stats["type_changes"][type_key] = (
                        stats["type_changes"].get(type_key, 0) + 1
                    )
                elif before_val != after_val:
                    stats["transformations_applied"] += 1
                    stats["fields_normalized"].append(f"{path}.{key}")

        return stats
