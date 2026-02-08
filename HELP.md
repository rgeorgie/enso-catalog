# Karate Club Management System - User Guide

## Overview

The Karate Club Management System is a comprehensive web application designed to manage all aspects of a karate club's operations. It handles player registration, training session tracking, payment management, event organization, and reporting.

## Kiosk Mode

For quick session recording without admin login, use the **Kiosk Mode** (`/kiosk`):
- Displays active players as large, clickable cards with semi-transparent backgrounds
- Athletes click their name to open a session recording modal
- Enter Player Number to confirm and record the training session
- Automatic payment status based on player type (monthly vs per-session)
- Prevents duplicate sessions for the same day
- **Card Reader Support**: Automatically detects and connects to USB card readers
- **Inactivity Timer**: On kiosk page, goes to screensaver after 10 minutes; on other public pages, returns to kiosk after 2 minutes
- **Streamlined Interface**: Clean, touch-friendly design without search filters

### Card Reader Setup
The system automatically detects card readers on startup. For manual configuration:
- Set `CARD_READER_DEVICE` environment variable to the correct device path
- Supported readers appear as HID keyboard devices
- Cards are read as keyboard input and processed automatically

## Getting Started

### Installation & Setup

1. **Prerequisites**: Python 3.8+ and pip
2. **Clone/Download** the application files
3. **Create Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Set Environment Variables**:
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export ADMIN_USER="admin"
   export ADMIN_PASS="your-admin-password"
   ```
6. **Run the Application**:
   ```bash
   python app.py
   ```
7. **Access**: Open http://127.0.0.1:5000 in your browser

### Production Deployment (Systemd)

For production use with automatic startup and kiosk mode:

1. **Install Chromium Browser** (for kiosk mode):
   ```bash
   sudo apt update && sudo apt install chromium-browser
   ```

2. **Run Systemd Setup**:
   ```bash
   sudo ./setup-systemd.sh
   ```

3. **Services Created**:
   - `enso-catalog.service`: Runs the Flask application
   - `enso-kiosk.service`: Starts browser in full-screen kiosk mode

4. **Service Management**:
   ```bash
   sudo systemctl start enso-catalog    # Start Flask app
   sudo systemctl start enso-kiosk      # Start kiosk browser
   sudo systemctl status enso-catalog   # Check status
   sudo journalctl -u enso-catalog -f   # View logs
   ```

The system will boot directly into kiosk mode with automatic card reader detection and inactivity timeout. Public pages automatically return to kiosk after 2 minutes of inactivity. The setup script automatically detects your project location and user and configures the services accordingly.

To remove the services later:
```bash
sudo ./remove-systemd.sh
```

### Language Support

The application supports Bulgarian (default) and English. Use the language switcher in the top navigation to change languages.

## User Roles & Access

### Regular Users
- View public player profiles
- Access basic information

### Administrators
- Full access to all features
- Login required for sensitive operations
- Use the admin login form with credentials set in environment variables

## Core Features

### 1. Player Management

#### Adding New Players
1. Navigate to **Players** → **+ Add Player**
2. Fill in required information:
   - **First Name & Last Name**: Player's full name
   - **PN (Personal Number)**: Mandatory 10-digit Bulgarian ID number (ЕГН)
   - **Gender**: Male/Female/Other
   - **Birthdate**: Date of birth
   - **Belt Rank**: Current karate belt level
   - **Grade Level**: Kyu/Dan ranking
   - **Payment Type**: Monthly or per-session
3. Optional information:
   - Contact details (phone, email)
   - Parent contacts (for minors)
   - Medical examination and insurance expiry dates
   - Photo upload (JPG/PNG/GIF/WEBP, max 2MB)

#### Managing Players
- **Search & Filter**: Use the search bar and filters for belt rank, active status
- **Edit Player**: Click the edit button on any player profile
- **View Profile**: Click on a player's name to see detailed information
- **Record Sessions**: For all players, record training attendance
- **Payment Management**: Track fees, generate receipts, mark payments

#### Player Profile Features
- **Training Calendar**: Interactive calendar showing sessions and events
- **Payment History**: View all payments and receipts
- **Event Registrations**: See registered events and payment status
- **Quick Actions**: Print due fees, export profile data

### 2. Training Session Tracking

#### Recording Sessions
1. Go to a player's profile
2. Click **"Record Session"** button
3. Sessions are automatically marked as paid/unpaid based on payment type:
   - **Monthly payers**: Sessions are free (marked as paid)
   - **Per-session payers**: Sessions require payment

#### Viewing Attendance
- **Calendar View**: Visual calendar with session indicators
- **List View**: Detailed chronological list of all sessions
- **Main Calendar**: Club-wide calendar showing daily attendance numbers and **events with registered players displaying club logos and participant counts**

### 3. Payment & Fee Management

#### Payment Types
- **Monthly Training**: Fixed monthly fee for unlimited sessions
- **Per-Session Training**: Pay per individual training session

#### Managing Payments
1. **From Player Profile**: Use quick action buttons to record payments
2. **Payment Forms**: Create receipts for training, events, or outstanding debts
3. **Toggle Payment Status**: Mark payments as paid/unpaid
4. **Print Receipts**: Generate printable payment receipts

#### Fee Tracking
- **Outstanding Debts**: View unpaid fees across all players
- **Payment History**: Complete transaction history
- **Due Fee Reports**: Generate reports for unpaid amounts

### 4. Event Management

#### Creating Events
1. **Admin Access Required**
2. Navigate to **Calendar** → **New Event**
3. Event Details:
   - Title, date range, location
   - Sportdata URL (external registration system)
   - Categories with fees and requirements

#### Event Categories
- Define competition categories (age, weight, belt requirements)
- Set registration fees per category
- Configure team size limits and registration cut-off dates

#### Player Registration
1. Go to event details
2. Click **"Add Registration"**
3. Select categories and fee overrides if needed
4. Mark payments and track registration status

#### Event Reporting
- **Registration Lists**: View all registered athletes
- **Payment Tracking**: Monitor paid/unpaid registrations
- **Grouped Payment Report**: View payments grouped by player, showing all categories and total fees per athlete
- **Export Data**: CSV exports for external systems
- **Medal Tracking**: Record competition results

### 5. Reporting & Exports

#### Available Reports
- **Fee Reports**: Monthly payment summaries
- **Medal Reports**: Competition results by year
- **Event Payment Reports**: Grouped payments by player with categories and totals
- **Player Lists**: Filtered player directories
- **Payment Exports**: Complete transaction history

#### Export Formats
- **CSV**: Comma-separated values for spreadsheets
- **ZIP**: Complete data packages with photos
- **PDF Receipts**: Printable payment documents

#### Admin Export/Import Tools
- **Bulk Operations**: Import multiple players/events
- **Data Backup**: Full system backups
- **Migration Tools**: Database schema updates

### 6. Admin Settings

#### Customizing the Application
1. **Access Settings**: Admin → Settings (login required)
2. **Logo Upload**: Upload a custom club logo (JPG/PNG/GIF/WEBP, max 2MB)
3. **Background Image**: Set a custom background watermark for the app
4. **Color Theme**: Choose primary and secondary colors for the interface
5. **Admin Password**: Change the admin login password (securely hashed)

#### Settings Effects
- **Logo**: Appears in navigation bar and on calendar events with registrations
- **Background**: Shows as a faint watermark on all pages
- **Colors**: Updates primary/secondary theme colors throughout the app
- **Password**: Securely stored and used for admin login verification

## Daily Operations

### Morning Routine
1. **Check Calendar**: Review scheduled events and training sessions
2. **Record Attendance**: Mark players present for training
3. **Monitor Payments**: Check for overdue fees

### Weekly Tasks
1. **Process Payments**: Record weekly/monthly fee collections
2. **Update Medical Records**: Verify insurance and medical exam validity
3. **Event Preparation**: Check upcoming event registrations

### Monthly Procedures
1. **Generate Fee Reports**: Identify outstanding payments
2. **Process Monthly Dues**: Record monthly training fees
3. **Update Insurance**: Renew expiring medical/insurance records
4. **Backup Data**: Export important data for safekeeping

## Advanced Features

### Calendar Integration
- **Interactive Calendar**: Click dates to create events (admin)
- **Event Details**: Click events for full information
- **Attendance Tracking**: Daily participation numbers
- **Event Registration Indicators**: Events with registered players show club logo and participant count
- **BNFK Events**: External Bulgarian National Karate Federation events (informational only, cached daily)
- **Multi-language Support**: Localized date formats

### Card Reader Integration
- **Automatic Detection**: System automatically finds and connects to USB card readers on startup
- **HID Support**: Works with card readers that emulate keyboard input
- **Kiosk Integration**: Card scans automatically trigger session recording in kiosk mode
- **Manual Configuration**: Set CARD_READER_DEVICE environment variable for custom device paths

### Data Validation
- **PN Validation**: 10-digit Bulgarian ID format checking
- **File Upload Security**: Type and size restrictions
- **Duplicate Prevention**: Automatic duplicate detection

### Backup & Recovery
- **Automatic Backups**: Export critical data regularly
- **Data Integrity**: Foreign key relationships maintained
- **Recovery Procedures**: Restore from backups if needed

## Troubleshooting

### Common Issues

**Login Problems**
- Verify ADMIN_USER and ADMIN_PASS environment variables
- Check for special characters in passwords

**File Upload Errors**
- Ensure files are under 2MB
- Check supported formats: JPG, PNG, GIF, WEBP

**Calendar Display Issues**
- Clear browser cache
- Check JavaScript is enabled
- Verify date formats are correct

**Payment Calculation Errors**
- Verify player payment type settings
- Check session payment status
- Review fee amounts and calculations

### Data Recovery
1. **Database Backup**: Regular exports of karate_club.db
2. **Photo Backup**: Backup uploads/ directory
3. **CSV Exports**: Keep exported data for reference

## Security Best Practices

- **Strong Passwords**: Use complex admin passwords
- **Regular Backups**: Backup data before major changes
- **Access Control**: Limit admin access to authorized personnel
- **File Validation**: Only upload trusted files
- **Session Management**: Log out when not using the system

## Support & Maintenance

### Regular Maintenance
- **Database Cleanup**: Remove old temporary files
- **Photo Organization**: Organize uploaded images
- **Performance Monitoring**: Check for slow operations
- **Update Dependencies**: Keep Python packages current

### Getting Help
- **Documentation**: Refer to this guide and inline help
- **Error Logs**: Check application logs for issues
- **Data Validation**: Use export features to verify data integrity
- **Report Issues**: [GitHub Issues](https://github.com/rgeorgie/enso-catalog/issues) - Report bugs and request features

---

**Note**: This application stores all data locally in SQLite. For production use, consider additional security measures and regular backups.</content>
<parameter name="filePath">/Users/rgeorgiev/Desktop/GiT/enso-catalog/HELP.md