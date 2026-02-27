from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    insert,
    delete,
)
import hashlib
import uuid

DATABASE_URL = "sqlite:///studentquest.db"
metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, nullable=False),
    Column("password_hash", String, nullable=False),
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("token", String, nullable=False),
)


class UsersDB:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        metadata.create_all(self.engine)

    def user_row_to_dict(self, row):
        return {
            "id": row.id,
            "email": row.email,
        }

    def hash_password(self, password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def get_all_users(self):
        with self.engine.connect() as conn:
            statement = select(users_table)
            rows = conn.execute(statement).fetchall()

        users = []
        for row in rows:
            users.append(self.user_row_to_dict(row))
        return users

    def get_user_by_id(self, user_id):
        with self.engine.connect() as conn:
            statement = select(users_table).where(users_table.c.id == user_id)
            row = conn.execute(statement).fetchone()

        if row is None:
            return None
        return self.user_row_to_dict(row)

    def get_user_by_email(self, email):
        with self.engine.connect() as conn:
            statement = select(users_table).where(users_table.c.email == email)
            row = conn.execute(statement).fetchone()

        return row

    def add_user(self, user_data):
        email = (user_data.get("email") or "").strip().lower()
        password = user_data.get("password") or ""

        if email == "" or password == "":
            return { "error": "Email and password are required." }

        if len(password) < 6:
            return { "error": "Password must be at least 6 characters." }

        existing = self.get_user_by_email(email)
        if existing is not None:
            return { "error": "Email already registered." }

        password_hash = self.hash_password(password)

        with self.engine.connect() as conn:
            stmt = insert(users_table).values(
                email=email,
                password_hash=password_hash,
            )
            result = conn.execute(stmt)
            conn.commit()
            new_id = result.inserted_primary_key[0]

        user = self.get_user_by_id(new_id)
        token = self.create_session(user["id"])
        return { "token": token, "user": user }

    def login_user(self, user_data):
        email = (user_data.get("email") or "").strip().lower()
        password = user_data.get("password") or ""

        if email == "" or password == "":
            return { "error": "Email and password are required." }

        row = self.get_user_by_email(email)
        if row is None:
            return { "error": "Invalid email or password." }

        password_hash = self.hash_password(password)
        if row.password_hash != password_hash:
            return { "error": "Invalid email or password." }

        user = self.user_row_to_dict(row)
        token = self.create_session(user["id"])
        return { "token": token, "user": user }

    def create_session(self, user_id):
        token = str(uuid.uuid4())

        with self.engine.connect() as conn:
            stmt = insert(sessions_table).values(
                user_id=user_id,
                token=token,
            )
            conn.execute(stmt)
            conn.commit()

        return token

    def get_user_by_token(self, token):
        with self.engine.connect() as conn:
            statement = select(sessions_table).where(sessions_table.c.token == token)
            session_row = conn.execute(statement).fetchone()

        if session_row is None:
            return None

        return self.get_user_by_id(session_row.user_id)

    def logout(self, token):
        with self.engine.connect() as conn:
            stmt = delete(sessions_table).where(sessions_table.c.token == token)
            conn.execute(stmt)
            conn.commit()

        return { "success": True }


app = FastAPI()
users_db = UsersDB()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/users")
def get_users():
    return users_db.get_all_users()


@app.post("/register")
def create_user(user: dict = Body(...)):
    return users_db.add_user(user)


@app.post("/login")
def login(user: dict = Body(...)):
    return users_db.login_user(user)


@app.get("/me")
def me(token: str = ""):
    if token == "":
        return { "error": "Missing token." }

    user = users_db.get_user_by_token(token)
    if user is None:
        return { "error": "Invalid token." }

    return user


@app.post("/logout")
def logout(payload: dict = Body(...)):
    token = payload.get("token") or ""
    if token == "":
        return { "error": "Missing token." }

    return users_db.logout(token)
