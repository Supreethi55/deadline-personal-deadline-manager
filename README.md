# Deadline

Deadline is a personal deadline manager for students. It turns natural-language reminders such as `TCS placement registration closes tomorrow at 5 PM` into structured, reviewable deadlines before saving them to a local SQLite database.

## Problem
Important academic and career dates arrive as scattered messages, notes, and thoughts. Manually turning each reminder into a title, category, priority, and due date is slow and easy to forget.

## Solution
Deadline uses Gemini to interpret natural language, presents the extracted result for confirmation, and keeps all confirmed work in a focused dashboard with Today, Upcoming, Overdue, and Completed views.

## Features
- Natural-language deadline analysis with Gemini
- Confirmation and editing before saving
- SQLite persistence through SQLAlchemy
- Today, upcoming, overdue, and completed statistics
- Category and priority labels
- Complete, edit, and delete actions
- Responsive dashboard for desktop and mobile
- API health endpoint and clear error states

## Architecture
The Flask application serves the HTML shell and JSON API. `ai_service.py` is the only module that talks to Gemini. `database.py` owns the SQLAlchemy extension, while `app.py` defines the model, validation, and routes. The browser uses vanilla JavaScript to call the API and update the dashboard without a page reload.

## AI workflow
1. The browser posts the reminder text to `/api/deadlines/analyze`.
2. The backend supplies Gemini with the current timezone-aware date and time.
3. Gemini returns only the requested JSON fields.
4. The backend validates the object, category, priority, and ISO-8601 date.
5. The browser shows a confirmation preview.
6. A separate POST saves only the user-confirmed values.

## Tech stack
Python, Flask, SQLite, SQLAlchemy, Gemini API, HTML, CSS, and vanilla JavaScript.

## Project structure
```text
Deadline/
├── app.py              # Flask app, model, validation, and routes
├── database.py         # SQLAlchemy extension
├── ai_service.py       # Gemini integration and response validation
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Local files excluded from Git
├── README.md           # Project documentation
├── templates/index.html
└── static/
    ├── style.css
    └── script.js
```

## Installation
PowerShell on Windows:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace `your_api_key_here` with your Gemini API key. The key is read only by the Flask backend and is never sent to frontend JavaScript.

Start the application:

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Environment variables
- `GEMINI_API_KEY`: required for natural-language analysis. Get a key from Google AI Studio.

## API endpoints
- `GET /`: dashboard page
- `GET /health`: service health check
- `POST /api/deadlines/analyze`: analyze `{ "text": "..." }`
- `POST /api/deadlines`: create a confirmed deadline
- `GET /api/deadlines`: list deadlines
- `PUT /api/deadlines/<id>`: update a deadline
- `DELETE /api/deadlines/<id>`: delete a deadline
- `PATCH /api/deadlines/<id>/complete`: toggle or set completion

## Testing examples
With the app running:

```powershell
Invoke-WebRequest http://127.0.0.1:5000/health
Invoke-RestMethod http://127.0.0.1:5000/api/deadlines
Invoke-RestMethod http://127.0.0.1:5000/api/deadlines/analyze -Method Post -ContentType 'application/json' -Body '{"text":"Submit DBMS assignment by Monday"}'
```

You can also test the complete flow from the dashboard: enter a reminder, review the preview, save it, then try the filters and card actions.

## Future improvements
- Calendar export and notifications
- Recurring deadlines
- User accounts and cloud sync
- More robust timezone preferences
- Automated unit and browser tests
