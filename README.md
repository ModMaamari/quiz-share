# Quiz Sharing App

A web application for creating and sharing quizzes with password protection and participant threshold features.

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure email settings:
- Rename `.env.example` to `.env`
- Update the `.env` file with your Gmail credentials:
  - `MAIL_USERNAME`: Your Gmail address
  - `MAIL_PASSWORD`: Your Gmail App Password (Generate from Google Account settings)

4. Run the application:
```bash
python app.py
```

5. Access the application:
- Open your browser and go to: http://localhost:5000

## Features

- Create quizzes with multiple questions
- Password protection for quiz access
- Set minimum number of participants
- Optional questions
- Automatic email distribution of results
- Form data preservation on validation errors
