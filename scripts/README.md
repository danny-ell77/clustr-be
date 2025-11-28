# Mock Data Population Script

This directory contains scripts for populating the ClustR backend with mock/test data.

## populate_mock_data.py

Populates the database with realistic mock data for:
- **Announcements** - Estate news, issues, and general announcements
- **Maintenance Logs** - Equipment servicing, repairs, and maintenance records
- **Helpdesk Issues** - Resident-reported problems and support tickets
- **Emergency Alerts** - SOS alerts and emergency incidents
- **Wallets** - User wallet accounts with balances
- **Bills** - Both cluster-wide and user-specific bills
- **Transactions** - Payment transactions, deposits, and withdrawals

## Usage

### Option 1: Using Django Shell (Recommended)

```bash
# Activate your virtual environment first
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Run the script
python manage.py shell < scripts/populate_mock_data.py
```

### Option 2: Using django-extensions (if installed)

```bash
python manage.py runscript populate_mock_data
```

### Option 3: Direct Python execution

```bash
python scripts/populate_mock_data.py
```

## What Gets Created

### User & Cluster
- Uses **existing user**: `vilofansky@gmail.com`
- Uses the user's **primary cluster** (does not create a new cluster)
- Creates additional test users if needed for variety

### Users
- Primary user: `vilofansky@gmail.com` (existing)
- Additional admin (if primary user is not admin)
- 10 additional residents with various unit addresses

### Data Volumes
- 15 announcements covering various categories
- 20 maintenance logs with different priorities and statuses
- 25 helpdesk issues of various types
- 10 emergency alerts (mostly resolved)
- 15 wallets (one per user) with random balances
- 30+ bills (cluster-wide and user-specific)
- 50 transactions with different types and statuses

## Notes

- **Requires existing user**: Script expects `vilofansky@gmail.com` to exist in the database with a primary cluster set
- The script uses the existing user's primary cluster - no new cluster is created
- Additional users are created for variety in data (maintenance staff, other residents, etc.)
- All mock data uses realistic Nigerian context (currency: NGN, phone numbers, etc.)
- Timestamps are randomized to simulate data over a 90-day period
- Default password for created test users: `password123`
- Additional users will be created only if needed (e.g., admin if primary user is not admin)

## Prerequisites

1. User `vilofansky@gmail.com` must exist in the database
2. The user must have a `primary_cluster` set
3. Django environment must be properly configured

## Resetting Data

To clear all data and start fresh:

```bash
python manage.py flush --noinput
python manage.py shell < scripts/populate_mock_data.py
```

⚠️ **Warning**: This will delete ALL data in your database!
