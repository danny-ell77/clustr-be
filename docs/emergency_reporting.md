# Emergency Reporting System

## Overview

The emergency reporting system provides comprehensive post-emergency reporting capabilities for the ClustR estate management system. This system allows administrators to generate detailed reports about emergency incidents, analyze response patterns, and export data for further analysis.

## Features

### 1. Emergency Cancellation and Resolution

#### Cancellation Mechanism
- **User Cancellation**: Members can cancel their own SOS alerts if triggered accidentally
- **Admin Cancellation**: Management can cancel any SOS alert with appropriate reason
- **Cancellation Tracking**: All cancellations are logged with timestamp, user, and reason

#### Resolution Workflow
- **Acknowledgment**: Emergency responders can acknowledge alerts
- **Response Initiation**: Track when response begins
- **Resolution**: Mark alerts as resolved with detailed notes
- **Timeline Tracking**: Complete timeline of all emergency response activities

### 2. Post-Emergency Reporting

#### Comprehensive Emergency Reports
- **Summary Statistics**: Total alerts, response times, resolution rates
- **Status Breakdown**: Distribution of alerts by status (active, resolved, cancelled)
- **Type Analysis**: Emergency types and their frequency
- **Time Analysis**: Patterns by hour, day, and month
- **Responder Analysis**: Performance metrics for emergency responders

#### Incident Reports
- **Detailed Timeline**: Complete chronological sequence of events
- **Response Metrics**: Response time, resolution time, number of responders
- **Involved Contacts**: Emergency contacts that were notified
- **Response Summary**: All response activities and their outcomes

#### Export Capabilities
- **JSON Format**: Structured data for API consumption
- **CSV Export**: Tabular data for spreadsheet analysis
- **PDF Reports**: Formatted reports for documentation

## API Endpoints

### Management App Endpoints

#### Generate Emergency Report
```
POST /management/sos-alerts/generate_report/
```

**Request Body:**
```json
{
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z",
    "emergency_type": "health",
    "status": "resolved"
}
```

**Response:**
```json
{
    "report_generated_at": "2024-01-15T10:30:00Z",
    "filters": {
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z",
        "emergency_type": "health",
        "status": "resolved"
    },
    "summary": {
        "total_alerts": 25,
        "status_breakdown": {
            "Active": 2,
            "Resolved": 20,
            "Cancelled": 3
        },
        "type_breakdown": {
            "Health Emergency": 15,
            "Theft/Robbery": 8,
            "Fire Emergency": 2
        },
        "average_response_time_minutes": 4.5,
        "average_resolution_time_minutes": 18.2
    },
    "time_analysis": {
        "alerts_by_hour": {
            "09:00": 3,
            "14:00": 5,
            "22:00": 8
        },
        "alerts_by_day": {
            "Monday": 4,
            "Tuesday": 3,
            "Wednesday": 6
        },
        "alerts_by_month": {
            "January 2024": 12,
            "February 2024": 13
        }
    },
    "responder_analysis": {
        "Security Team": {
            "total_responses": 15,
            "response_types": {
                "Acknowledged": 15,
                "Dispatched": 12,
                "Resolved": 10
            }
        }
    },
    "recent_alerts": [
        {
            "alert_id": "SOS-ABC123",
            "emergency_type": "Health Emergency",
            "status": "Resolved",
            "user_name": "John Doe",
            "created_at": "2024-01-15T09:30:00Z",
            "response_time_minutes": 3,
            "resolution_time_minutes": 15
        }
    ]
}
```

#### Get Incident Report
```
GET /management/sos-alerts/{alert_id}/incident_report/
```

**Response:**
```json
{
    "alert_info": {
        "alert_id": "SOS-ABC123",
        "emergency_type": "Health Emergency",
        "status": "Resolved",
        "priority": "High",
        "description": "Medical emergency in apartment 4B",
        "location": "Building A, Floor 4",
        "created_by": "John Doe",
        "created_at": "2024-01-15T09:30:00Z"
    },
    "timeline": [
        {
            "timestamp": "2024-01-15T09:30:00Z",
            "event": "Alert Created",
            "description": "SOS alert created by John Doe",
            "user": "John Doe",
            "details": {
                "emergency_type": "Health Emergency",
                "priority": "High",
                "location": "Building A, Floor 4",
                "description": "Medical emergency in apartment 4B"
            }
        },
        {
            "timestamp": "2024-01-15T09:33:00Z",
            "event": "Alert Acknowledged",
            "description": "Alert acknowledged by Security Team",
            "user": "Security Team",
            "details": {}
        },
        {
            "timestamp": "2024-01-15T09:35:00Z",
            "event": "Response Started",
            "description": "Response started by Security Team",
            "user": "Security Team",
            "details": {}
        },
        {
            "timestamp": "2024-01-15T09:45:00Z",
            "event": "Alert Resolved",
            "description": "Alert resolved by Security Team",
            "user": "Security Team",
            "details": {
                "resolution_notes": "Paramedics arrived and patient stabilized"
            }
        }
    ],
    "metrics": {
        "response_time_minutes": 3,
        "resolution_time_minutes": 15,
        "total_responders": 2,
        "total_responses": 4
    },
    "involved_contacts": [
        {
            "name": "Estate Security",
            "phone_number": "+1234567890",
            "email": "security@estate.com",
            "contact_type": "Estate-wide Contact",
            "is_primary": true
        }
    ],
    "responses_summary": {
        "total_responses": 4,
        "response_types": ["acknowledged", "dispatched", "on_scene", "resolved"]
    },
    "report_generated_at": "2024-01-15T10:30:00Z"
}
```

#### Export Report
```
GET /management/sos-alerts/export_report/?format=csv&start_date=2024-01-01T00:00:00Z
```

**Query Parameters:**
- `format`: Export format (json, csv, pdf)
- `start_date`: Filter start date
- `end_date`: Filter end date
- `emergency_type`: Filter by emergency type
- `status`: Filter by status

### Members App Endpoints

#### Cancel Alert
```
POST /members/sos-alerts/{alert_id}/cancel/
```

**Request Body:**
```json
{
    "reason": "Accidental trigger - false alarm"
}
```

#### Get Incident Report (Own Alerts Only)
```
GET /members/sos-alerts/{alert_id}/incident_report/
```

## Usage Examples

### Generating Monthly Emergency Report

```python
from core.common.utils.emergency_utils import EmergencyManager
from datetime import datetime, timedelta

# Generate report for last month
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

report = EmergencyManager.generate_emergency_report(
    cluster=cluster,
    start_date=start_date,
    end_date=end_date
)

print(f"Total alerts: {report['summary']['total_alerts']}")
print(f"Average response time: {report['summary']['average_response_time_minutes']} minutes")
```

### Generating Incident Report

```python
from core.common.utils.emergency_utils import EmergencyManager
from core.common.models.emergency import SOSAlert

alert = SOSAlert.objects.get(alert_id="SOS-ABC123")
incident_report = EmergencyManager.generate_alert_incident_report(alert)

print(f"Alert timeline has {len(incident_report['timeline'])} events")
print(f"Response time: {incident_report['metrics']['response_time_minutes']} minutes")
```

### Cancelling an Alert

```python
from core.common.utils.emergency_utils import EmergencyManager

# User cancelling their own alert
result = EmergencyManager.cancel_alert(
    alert=alert,
    user=user,
    reason="False alarm - accidental trigger"
)

if result:
    print("Alert cancelled successfully")
```

## Security Considerations

1. **Access Control**: Only authorized users can access emergency reports
2. **Data Privacy**: Personal information is protected in reports
3. **Audit Trail**: All cancellations and resolutions are logged
4. **Permission Checks**: Users can only cancel their own alerts

## Performance Considerations

1. **Report Caching**: Large reports may be cached for performance
2. **Pagination**: Large datasets are paginated in API responses
3. **Async Processing**: Complex reports may be processed asynchronously
4. **Database Indexing**: Proper indexes on emergency tables for fast queries

## Future Enhancements

1. **Real-time Dashboards**: Live emergency monitoring dashboards
2. **Automated Reporting**: Scheduled report generation and distribution
3. **Advanced Analytics**: Machine learning for emergency pattern analysis
4. **Integration**: Integration with external emergency services
5. **Mobile Notifications**: Push notifications for emergency updates