import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from ai_service import ALLOWED_CATEGORIES, ALLOWED_PRIORITIES, analyze_text
from database import db

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///deadlines.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


class Deadline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    priority = db.Column(db.String(10), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
        }


with app.app_context():
    db.create_all()


def parse_deadline(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("Deadline must be an ISO-8601 string or null.")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_payload(data):
    required = {"title", "description", "category", "priority", "deadline"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise ValueError("title, description, category, priority, and deadline are required.")
    if not isinstance(data["title"], str) or not data["title"].strip():
        raise ValueError("Title is required.")
    if data["category"] not in ALLOWED_CATEGORIES or data["priority"] not in ALLOWED_PRIORITIES:
        raise ValueError("Unsupported category or priority.")
    return {
        "title": data["title"].strip()[:160],
        "description": str(data["description"]).strip()[:1000],
        "category": data["category"],
        "priority": data["priority"],
        "deadline": parse_deadline(data["deadline"]),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/deadlines/analyze")
def analyze_deadline():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Please enter a reminder to analyze."}), 400
    try:
        return jsonify(analyze_text(text))
    except (RuntimeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        app.logger.exception("Gemini analysis failed: %s", exc)
        return jsonify({"error": "The AI service is unavailable right now."}), 502


@app.get("/api/deadlines")
def list_deadlines():
    deadlines = Deadline.query.order_by(Deadline.completed.asc(), Deadline.deadline.asc().nullslast(), Deadline.created_at.desc()).all()
    return jsonify([deadline.to_dict() for deadline in deadlines])


@app.post("/api/deadlines")
def create_deadline():
    try:
        deadline = Deadline(**validate_payload(request.get_json(silent=True) or {}))
        db.session.add(deadline)
        db.session.commit()
        return jsonify(deadline.to_dict()), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.put("/api/deadlines/<int:deadline_id>")
def update_deadline(deadline_id):
    deadline = db.get_or_404(Deadline, deadline_id)
    try:
        values = validate_payload(request.get_json(silent=True) or {})
        for key, value in values.items():
            setattr(deadline, key, value)
        db.session.commit()
        return jsonify(deadline.to_dict())
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.delete("/api/deadlines/<int:deadline_id>")
def delete_deadline(deadline_id):
    deadline = db.get_or_404(Deadline, deadline_id)
    db.session.delete(deadline)
    db.session.commit()
    return jsonify({"message": "Deadline deleted."})


@app.patch("/api/deadlines/<int:deadline_id>/complete")
def complete_deadline(deadline_id):
    deadline = db.get_or_404(Deadline, deadline_id)
    data = request.get_json(silent=True) or {}
    deadline.completed = bool(data.get("completed", not deadline.completed))
    db.session.commit()
    return jsonify(deadline.to_dict())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)