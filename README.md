# Patient Management System (PMS)

A production-grade, multi-branch patient management system built with Django.

## Features
- Multi-branch support
- Secure patient data management
- Medical file upload system
- Role-based access control

## Setup
1. Create PostgreSQL database
2. Copy `.env.example` to `.env` and update values
3. Run `pip install -r requirements-dev.txt`
4. Run `python manage.py migrate`
5. Run `python manage.py runserver`

## Architecture
Modular Django apps for isolation and future extensibility.