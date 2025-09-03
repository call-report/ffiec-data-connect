# FFIEC REST API Endpoint Mapping

## Python Function to REST Endpoint Mapping

This document maps our Python functions to the corresponding FFIEC REST API endpoints.
Based on official FFIEC document: CDR-PDD-SIS-611 v1.10

### Currently Implemented Mappings

There are exactly **7 REST endpoints** per the official PDF specification:

| Python Function | REST Endpoint | HTTP Method | Status |
|----------------|---------------|-------------|---------|
| `collect_reporting_periods()` | `/RetrieveReportingPeriods` | GET | ✅ Working |
| `collect_filers_on_reporting_period()` | `/RetrievePanelOfReporters` | GET | ✅ Working |
| `collect_filers_since_date()` | `/RetrieveFilersSinceDate` | GET | ✅ Working |
| `collect_filers_submission_date_time()` | `/RetrieveFilersSubmissionDateTime` | GET | ✅ Working |
| `collect_data()` | `/RetrieveFacsimile` | GET | ✅ Working |
| N/A (UBPR specific) | `/RetrieveUBPRReportingPeriods` | GET | ✅ Working |
| N/A (UBPR specific) | `/RetrieveUBPRXBRLFacsimile` | GET | ✅ Working |

### CRITICAL: All Parameters are Headers!

**IMPORTANT**: The FFIEC REST API passes ALL parameters as HTTP headers, NOT query parameters!

### Endpoint Details

#### 1. RetrieveReportingPeriods
- **Python**: `collect_reporting_periods()`
- **REST Path**: `/RetrieveReportingPeriods`
- **Method**: GET
- **Headers Required**:
  - `UserID`: FFIEC username (capital 'ID')
  - `Authentication`: Bearer {token}
  - `dataSeries`: "Call"
- **Response**: JSON array of date strings

#### 2. RetrievePanelOfReporters
- **Python**: `collect_filers_on_reporting_period()`
- **REST Path**: `/RetrievePanelOfReporters`
- **Method**: GET
- **Headers Required**:
  - `UserID`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: "Call"
  - `reportingPeriodEndDate`: MM/DD/YYYY format
- **Response**: JSON array of filer objects

#### 3. RetrieveFilersSinceDate
- **Python**: `collect_filers_since_date()`
- **REST Path**: `/RetrieveFilersSinceDate`
- **Method**: GET
- **Headers Required**:
  - `UserID`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: "Call"
  - `reportingPeriodEndDate`: MM/DD/YYYY format
  - `lastUpdateDateTime`: MM/DD/YYYY or "MM/DD/YYYY HH:MM PM"
- **Response**: JSON array of RSSD IDs (integers)

#### 4. RetrieveFilersSubmissionDateTime
- **Python**: `collect_filers_submission_date_time()`
- **REST Path**: `/RetrieveFilersSubmissionDateTime`
- **Method**: GET
- **Headers Required**:
  - `UserID`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: "Call"
  - `reportingPeriodEndDate`: MM/DD/YYYY format
  - `lastUpdateDateTime`: MM/DD/YYYY or "MM/DD/YYYY HH:MM PM"
- **Response**: JSON array of objects with ID_RSSD and DateTime

#### 5. RetrieveFacsimile
- **Python**: `collect_data()`
- **REST Path**: `/RetrieveFacsimile`
- **Method**: GET
- **Headers Required**:
  - `UserID`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: "Call"
  - `reportingPeriodEndDate`: MM/DD/YYYY format
  - `fiIdType`: "ID_RSSD" (or "FDICCertNumber", "OCCChartNumber", "OTSDockNumber")
  - `fiId`: Institution identifier
  - `facsimileFormat`: "XBRL" (or "PDF", "SDF")
- **Response**: Binary data (XBRL/PDF/SDF file)

#### 6. RetrieveUBPRReportingPeriods
- **Python**: N/A (UBPR specific)
- **REST Path**: `/RetrieveUBPRReportingPeriods`
- **Method**: GET
- **Headers Required**:
  - `UserID`: FFIEC username
  - `Authentication`: Bearer {token}
  - **Note**: NO dataSeries header needed!
- **Response**: JSON array of date strings

#### 7. RetrieveUBPRXBRLFacsimile
- **Python**: N/A (UBPR specific)
- **REST Path**: `/RetrieveUBPRXBRLFacsimile`
- **Method**: GET
- **Headers Required**:
  - `UserID`: FFIEC username
  - `Authentication`: Bearer {token}
  - `reportingPeriodEndDate`: MM/DD/YYYY format
  - `fiIdType`: "ID_RSSD" (or other types)
  - `fiId`: Institution identifier
  - **Note**: NO dataSeries header needed!
- **Response**: Binary XBRL data

### SOAP to REST Comparison

| SOAP Method | REST Endpoint | Key Differences |
|------------|---------------|-----------------|
| `TestUserAccess` | N/A | No REST equivalent |
| `RetrieveReportingPeriods` | `/RetrieveReportingPeriods` | Headers instead of SOAP envelope |
| `RetrievePanelOfReporters` | `/RetrievePanelOfReporters` | All params as headers |
| `RetrieveFilersSinceDate` | `/RetrieveFilersSinceDate` | All params as headers |
| `RetrieveFilersSubmissionDateTime` | `/RetrieveFilersSubmissionDateTime` | All params as headers |
| `RetrieveFacsimile` | `/RetrieveFacsimile` | All params as headers |
| `RetrieveUBPRReportingPeriods` | `/RetrieveUBPRReportingPeriods` | No dataSeries header |
| `RetrieveUBPRXBRLFacsimile` | `/RetrieveUBPRXBRLFacsimile` | No dataSeries header |

### Implementation Notes

1. **Authentication**: REST uses OAuth2 Bearer tokens in `Authentication` header (NOT `Authorization`)
2. **Case Sensitivity CRITICAL**: 
   - `UserID` (capital 'ID', not 'UserId' or 'UserID')
   - `dataSeries` value is "Call" (capital 'C', not "call")
   - `Authentication` (not `Authorization`)
3. **Headers vs Query Params**: ALL parameters are passed as headers, NEVER as query parameters
4. **Date Formats**: MM/DD/YYYY for reporting periods
5. **Response Format**: JSON for metadata, binary for XBRL/PDF/SDF data
6. **Rate Limiting**: 2500 requests/hour for REST vs 1000 for SOAP
7. **UBPR Endpoints**: Do NOT require dataSeries header (it's implicit)

### Common Mistakes to Avoid

1. ❌ Using query parameters instead of headers
2. ❌ Using "UserId" instead of "UserID"
3. ❌ Using "Authorization" instead of "Authentication"
4. ❌ Using lowercase "call" instead of "Call" for dataSeries
5. ❌ Adding dataSeries header to UBPR endpoints
6. ❌ Assuming endpoints exist that aren't in the PDF (like RetrieveFacsimileExt)