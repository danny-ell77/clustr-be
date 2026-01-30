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


## populate_residents_children.py

Populates the database with residents and children mock data specifically for testing the resident management and child management features.

### What Gets Created

- **30 Residents** - Non-staff users with realistic Nigerian names and addresses
- **50 Children** - Linked to residents with ages 1-17
- **20 Exit Requests** - For children with various statuses (approved, pending, rejected)
- **100 Entry/Exit Logs** - Historical entry and exit records for children
- **100 Resident Bills** - Various bill types (electricity, water, security, etc.) with mixed payment statuses

### Usage

```bash
# Activate your virtual environment first
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Run the script
python manage.py shell < scripts/populate_residents_children.py
```

Or with django-extensions:

```bash
python manage.py runscript populate_residents_children
```

### Data Details

**Residents:**
- All created as non-staff users (`is_staff=False`)
- Mix of verified and unverified users
- Mix of approved and pending approval statuses
- Assigned to various blocks (A-F) and unit numbers
- Different property types (Flat, Duplex, Bungalow, etc.)

**Children:**
- Realistic Nigerian names (both male and female)
- Ages range from 1 to 17 years
- Each has emergency contacts including parent
- Linked to parent's unit address
- Active status

**Exit Requests:**
- Various purposes (school pickup, medical, family outing, etc.)
- Mix of approved, pending, and rejected statuses
- Realistic destinations within Lagos area
- Expected return times

**Entry/Exit Logs:**
- Historical logs spanning 60 days
- Most entries have corresponding exits
- Some exits without entries (still out)
- Authorized by parents

**Bills:**
- Various types: electricity, water, security, maintenance, utilities
- Amounts range from ₦3,000 to ₦100,000
- ~70% paid, ~30% unpaid for realistic testing
- Due dates spread across past and future
- All linked to specific residents

### Prerequisites

Same as `populate_mock_data.py`:
1. User `vilofansky@gmail.com` must exist
2. User must have a `primary_cluster` set
3. Django environment properly configured

### Notes

- Residents are created as regular users (not staff/admin)
- Children are distributed across residents (some residents may have multiple children)
- Bills include both paid and unpaid statuses for realistic dashboard testing
- All data uses Nigerian context (names, phone numbers, locations)
- Default password for created residents: `password123`
