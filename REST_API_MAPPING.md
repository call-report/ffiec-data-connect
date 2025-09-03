# FFIEC REST API Endpoint Mapping

## Python Function to REST Endpoint Mapping

This document maps our Python functions to the corresponding FFIEC REST API endpoints.

### Currently Implemented Mappings

| Python Function | REST Endpoint | HTTP Method | Status |
|----------------|---------------|-------------|---------|
| `collect_reporting_periods()` | `/RetrieveReportingPeriods` | GET | ✅ Working |
| `collect_filers_on_reporting_period()` | `/RetrievePanelOfReporters` | GET | ❓ Need to verify |
| `collect_filers_since_date()` | `/RetrieveFilersSinceDate` | GET | ❓ Need to verify |
| `collect_filers_submission_date_time()` | `/RetrieveFilersSubmissionDateTime` | GET | ❓ Need to verify |
| `collect_data()` | `/RetrieveFacsimile` | GET | ❌ Returns 500 error |

### Endpoint Details

#### 1. RetrieveReportingPeriods
- **Python**: `collect_reporting_periods()`
- **REST Path**: `/RetrieveReportingPeriods`
- **Method**: GET
- **Headers Required**:
  - `UserId`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: call or ubpr (lowercase)
- **Query Parameters**: None
- **Response**: JSON array of date strings

#### 2. RetrievePanelOfReporters
- **Python**: `collect_filers_on_reporting_period()`
- **REST Path**: `/RetrievePanelOfReporters`
- **Method**: GET
- **Headers Required**:
  - `UserId`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: call or ubpr
- **Query Parameters**:
  - `reportingPeriodEndDate`: MM/DD/YYYY format
- **Response**: JSON array of filer objects

#### 3. RetrieveFilersSinceDate
- **Python**: `collect_filers_since_date()`
- **REST Path**: `/RetrieveFilersSinceDate`
- **Method**: GET
- **Headers Required**:
  - `UserId`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: call or ubpr
- **Query Parameters**:
  - `reportingPeriodEndDate`: MM/DD/YYYY format
  - `lastUpdateDateTime`: ISO 8601 datetime
- **Response**: JSON array of RSSD IDs

#### 4. RetrieveFilersSubmissionDateTime
- **Python**: `collect_filers_submission_date_time()`
- **REST Path**: `/RetrieveFilersSubmissionDateTime`
- **Method**: GET
- **Headers Required**:
  - `UserId`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: call or ubpr
- **Query Parameters**:
  - `reportingPeriodEndDate`: MM/DD/YYYY format
- **Response**: JSON array of objects with rssd and submissionDateTime

#### 5. RetrieveFacsimile
- **Python**: `collect_data()`
- **REST Path**: `/RetrieveFacsimile`
- **Method**: GET (may need POST)
- **Headers Required**:
  - `UserId`: FFIEC username
  - `Authentication`: Bearer {token}
  - `dataSeries`: call or ubpr
- **Query Parameters**:
  - `fiIDType`: ID_RSSD
  - `fiID`: RSSD ID
  - `reportingPeriodEndDate`: MM/DD/YYYY format
  - `facsimileFormat`: XBRL or PDF
- **Response**: Binary XBRL or PDF data
- **Status**: ⚠️ Currently returns 500 error - may not be implemented in REST API

### SOAP to REST Comparison

| SOAP Method | REST Endpoint | Key Differences |
|------------|---------------|-----------------|
| `TestUserAccess` | N/A | No REST equivalent |
| `RetrieveReportingPeriods` | `/RetrieveReportingPeriods` | REST uses headers instead of SOAP envelope |
| `RetrievePanelOfReporters` | `/RetrievePanelOfReporters` | Same name, different auth |
| `RetrieveFilersSinceDate` | `/RetrieveFilersSinceDate` | Same name, different auth |
| `RetrieveFilersSubmissionDateTime` | `/RetrieveFilersSubmissionDateTime` | Same name, different auth |
| `RetrieveFacsimile` | `/RetrieveFacsimile` | May not be implemented in REST |
| `RetrieveUBPRXBRLFacsimile` | `/RetrieveUBPRXBRLFacsimile` | May not be implemented in REST |

### Implementation Notes

1. **Authentication**: REST uses OAuth2 Bearer tokens in `Authentication` header (not `Authorization`)
2. **Case Sensitivity**: 
   - `UserId` (lowercase 'd')
   - `dataSeries` (lowercase values: "call" not "Call")
   - `Authentication` (not `Authorization`)
3. **Date Formats**: MM/DD/YYYY for reporting periods
4. **Response Format**: JSON for metadata, binary for XBRL/PDF data
5. **Rate Limiting**: 2500 requests/hour for REST vs 1000 for SOAP

### TODO: Verify Actual Endpoints

Need to verify with actual API calls:
- [ ] Confirm `/RetrievePanelOfReporters` works
- [ ] Confirm `/RetrieveFilersSinceDate` works
- [ ] Confirm `/RetrieveFilersSubmissionDateTime` works
- [ ] Check if `/RetrieveFacsimile` will be implemented
- [ ] Check if `/RetrieveFacsimileExt` exists (POST version)
- [ ] Check if `/RetrieveUBPRXBRLFacsimile` exists