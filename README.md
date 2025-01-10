# Task Management API

tiny FastAPI thing I built for a class. users sign up, log in, and get their own tasks. admin can peek at everything. probably overkill for a homework but here we are.

## Features (ish)
- JWT auth + bcrypt hashing
- tasks CRUD tied to the logged-in user
- simple RBAC (user/admin) w/ `/tasks/all` for admins
- alembic + postgres (or sqlite if you're just testing)
- pytest + coverage (75% fail gate because why not)
- docker + render blueprint
- error handlers so it doesn't just explode

## Quick start
- Docker: `docker-compose up --build` then check http://localhost:8000/docs
- Local: `python -m venv venv && source venv/bin/activate` then `pip install -r requirements.txt`
  - set envs: `cp .env.example .env` and tweak `DATABASE_URL`/`SECRET_KEY`
  - run `alembic upgrade head` once and then `uvicorn main:app --reload`
- If stuff looks broken, delete your test.db and try again (worked for me)

## Endpoints (tl;dr)
| Method | Path | Auth | Role | What it does |
| --- | --- | --- | --- | --- |
| GET | `/` | no | - | health ping |
| POST | `/auth/signup` | no | - | create user (role optional, default user) |
| POST | `/auth/login` | no | - | get token |
| GET | `/tasks` | yes | user/admin | list my tasks |
| POST | `/tasks` | yes | user/admin | make a task |
| PATCH | `/tasks/{id}` | yes | user/admin | update my task |
| DELETE | `/tasks/{id}` | yes | user/admin | delete my task |
| GET | `/tasks/all` | yes | admin | see everything |

More examples live at `/docs` (Swagger) and `/redoc`.

## Testing
- `pytest --cov=. --cov-report=term-missing --cov-fail-under=75`
- yeah the coverage flag is annoying but it caught a bug once so I'm leaving it

## Deploy to Render
1. push to GitHub
2. in Render pick **Blueprint** -> point at repo (reads `render.yaml`)
3. for first deploy open shell and `alembic upgrade head`
4. if Render yells about SECRET_KEY, set it in the dashboard

## Stuff to fix later
- split `main.py` into modules
- pagination on `/tasks`
- docs could be less stiff / more screenshots maybe

## Random notes
- `NOTES.md` is just a scratchpad
- if you find a better way to do admin checks, lmk
