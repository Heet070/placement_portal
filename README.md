# 🎓 Placement Portal

A web-based placement management portal built with **Django**, designed to streamline the placement process for students and administrators.

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2 |
| Database | PostgreSQL (via psycopg2) |
| Static Files | WhiteNoise |
| Server | Gunicorn |
| Environment | python-dotenv |

---

## 📁 Project Structure

```
placement_portal/
├── placement_portal/   # Django project config (settings, urls, wsgi)
├── portal/             # Main application (models, views, templates)
├── static/             # Static assets (CSS, JS, images)
├── manage.py
├── requirements.txt
├── Procfile            # For deployment (Gunicorn)
├── runtime.txt         # Python version spec
└── backup.json         # Data fixture/backup
```

---

## ⚙️ Local Setup

### Prerequisites

- Python 3.x
- PostgreSQL

### 1. Clone the repository

```bash
git clone https://github.com/Heet070/placement_portal.git
cd placement_portal
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory:

```env
SECRET_KEY=your_django_secret_key
DEBUG=True
DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DB_NAME
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. (Optional) Load fixture data

```bash
python manage.py loaddata backup.json
```

### 7. Run the development server

```bash
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000`.

---

## 🌐 Deployment

This project includes a `Procfile` for platforms like **Heroku**:

```
web: gunicorn placement_portal.wsgi --log-file -
```

Make sure to set all environment variables (`SECRET_KEY`, `DATABASE_URL`, etc.) in your hosting platform's config.

Static files are served via **WhiteNoise** — no extra configuration needed.

---
