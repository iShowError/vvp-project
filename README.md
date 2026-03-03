# Issue Management System 🏫🔧

A Django-based complaint and issue management system for VVP Engineering College. Department Heads can raise IT infrastructure complaints, Engineers track and resolve them, and Admins oversee everything from a dedicated panel.

---

## Features

- **Role-based Access**: Separate dashboards for Department Heads, Engineers, and Admins
- **Issue Tracking**: Raise, update, and close complaints for devices like computers, printers, projectors, and network equipment
- **Comments System**: Engineers can comment on issues to communicate progress; comments are locked once an issue is closed
- **Status Workflow**: Issues move through `Open → In Progress → Resolved → Completed/Closed`
- **Google OAuth**: Sign in with your college Google account (`@vvpedulink.ac.in`)
- **Audit History**: Every change to every record is tracked with full history via `django-simple-history`
- **Admin Panel**: Jazzmin-themed Django admin for full system oversight
- **Login Protection**: Brute-force protection — 5 failed attempts locks an account for 15 minutes
- **Email Notifications**: Email alerts on new comments and status changes

---

## Technology Stack

### Backend
- **Django 5.1.7**: Web framework
- **SQLite**: Database (development)
- **Python 3.13**: Programming language

### Frontend
- **Plain HTML/CSS**: No frontend framework, custom styling per template

### Packages
- **django-allauth 65.11.0**: Google OAuth / social login
- **django-jazzmin 3.0.1**: Admin panel theme
- **django-simple-history 3.11.0**: Model change history and audit trail

---

## Project Structure

```
college_log/
├── manage.py
├── db.sqlite3
├── static/
│   └── admin/
│       └── css/
│           └── custom_admin.css       ← Jazzmin overrides
├── college_log/                       ← Project settings package
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── google_oauth_config.json       ← NOT committed (see setup)
└── logs/                              ← Main application
    ├── models.py                      ← Issue, Comment, Device, Log, UserProfile
    ├── views.py                       ← All view logic
    ├── forms.py                       ← Registration, Login, Issue, UpdateIssue forms
    ├── urls.py                        ← App URL patterns
    ├── admin.py                       ← Admin registrations with history
    ├── adapters.py                    ← Google OAuth custom adapter
    ├── migrations/
    └── templates/
        ├── index.html
        ├── login.html
        ├── register.html
        ├── engineer_dashboard.html
        └── dept_head_dashboard.html
```

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip
- Git (optional)

### Step 1: Clone or Download

```bash
git clone <your-repo-url>
cd college_log
```

### Step 2: Create Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install django==5.1.7 django-allauth==65.11.0 django-jazzmin==3.0.1 django-simple-history==3.11.0
```

### Step 4: Run Migrations

```bash
python manage.py migrate
```

### Step 5: Create a Superuser (Admin)

```bash
python manage.py createsuperuser
```

### Step 6: Run the Development Server

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

---

## Google OAuth Setup (Optional)

If you want Google login to work, create the file `college_log/google_oauth_config.json` (this file is gitignored):

```json
{
  "client_id": "YOUR_GOOGLE_CLIENT_ID",
  "secret": "YOUR_GOOGLE_CLIENT_SECRET"
}
```

Then in the Django admin panel:
1. Go to **Sites** → change `example.com` to `localhost:8000`
2. Go to **Social Applications** → Add a Google app, paste your client ID and secret, link to the site above

If you skip this, the app works fine — only the "Sign in with Google" button will be broken.

---

## How It Works

### Issue Lifecycle

```
Dept Head submits issue
        │
        ▼
   Status: OPEN
        │
        │  Engineer picks it up
        ▼
Status: IN PROGRESS
        │
        │  Engineer resolves it
        ▼
 Status: RESOLVED
        │
        │  Dept Head confirms and closes
        ▼
Status: COMPLETED / CLOSED
   (no more edits allowed)
```

### Role Assignment from Email

```
Email: ithod@vvpedulink.ac.in   →  Dept Head  (prefix: ithod)
Email: cehod@vvpedulink.ac.in   →  Dept Head  (prefix: cehod)
Email: john@vvpedulink.ac.in    →  Engineer   (other @vvpedulink.ac.in)
Email: anyone@gmail.com         →  REJECTED   (wrong domain)
```

### Login Protection Flow

```
Failed login attempt
        │
        ▼
Failure count stored in cache (per email + IP)
        │
        ▼
  5th failure?
   ├── YES → Account locked for 15 minutes
   └── NO  → Show "Incorrect credentials" error
```

---

## Testing

### Manual Testing Checklist

- [ ] Register as Engineer with `@vvpedulink.ac.in` email
- [ ] Register as Dept Head with `{dept}hod@vvpedulink.ac.in` email
- [ ] Login and verify correct dashboard is shown
- [ ] Dept Head: Submit a new issue
- [ ] Engineer: Add a comment to the issue
- [ ] Engineer: Edit the comment
- [ ] Dept Head: Close the issue
- [ ] Engineer: Try to add/edit/delete comment on closed issue (should be blocked)
- [ ] Test 5 wrong login attempts → verify lockout message
- [ ] Login as superuser → verify admin panel access
- [ ] Try visiting `/engineer/dashboard/` while logged in as Dept Head (should redirect)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Test thoroughly using the checklist above
5. Submit a pull request

---

**Happy resolving! 🔧✅**