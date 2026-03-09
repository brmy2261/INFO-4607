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
    update,
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

profiles_table = Table(
    "profiles",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("display_name", String, nullable=False),
    Column("bio", String, nullable=False),
    Column("avatar_url", String, nullable=False),
)

services_table = Table(
    "services",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("title", String, nullable=False),
    Column("genre", String, nullable=False),
    Column("description", String, nullable=False),
    Column("price", String, nullable=False),
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

    def profile_row_to_dict(self, row):
        return {
            "userId": row.user_id,
            "displayName": row.display_name,
            "bio": row.bio,
            "avatarUrl": row.avatar_url,
        }

    def service_row_to_dict(self, row):
        profile = self.get_profile_by_user_id(row.user_id)
        user = self.get_user_by_id(row.user_id)

        display_name = "Student"
        if profile is not None:
            display_name = profile["displayName"]
        elif user is not None:
            display_name = user["email"].split("@")[0]

        return {
            "id": row.id,
            "userId": row.user_id,
            "title": row.title,
            "genre": row.genre,
            "description": row.description,
            "price": row.price,
            "displayName": display_name,
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

        return {"success": True}

    def ensure_profile_for_user(self, user_id, email):
        with self.engine.connect() as conn:
            statement = select(profiles_table).where(profiles_table.c.user_id == user_id)
            row = conn.execute(statement).fetchone()

        if row is not None:
            return self.profile_row_to_dict(row)

        default_name = email.split("@")[0] if email else "student"
        default_avatar = "https://i.pravatar.cc/200?u=" + str(user_id)

        with self.engine.connect() as conn:
            stmt = insert(profiles_table).values(
                user_id=user_id,
                display_name=default_name,
                bio="",
                avatar_url=default_avatar,
            )
            conn.execute(stmt)
            conn.commit()

        return self.get_profile_by_user_id(user_id)

    def get_profile_by_user_id(self, user_id):
        with self.engine.connect() as conn:
            statement = select(profiles_table).where(profiles_table.c.user_id == user_id)
            row = conn.execute(statement).fetchone()

        if row is None:
            return None

        return self.profile_row_to_dict(row)

    def get_profile_by_token(self, token):
        user = self.get_user_by_token(token)
        if user is None:
            return None

        profile = self.get_profile_by_user_id(user["id"])
        if profile is None:
            profile = self.ensure_profile_for_user(user["id"], user["email"])

        return profile

    def update_profile_by_token(self, token, profile_data):
        user = self.get_user_by_token(token)
        if user is None:
            return {"error": "Invalid token."}

        existing = self.get_profile_by_user_id(user["id"])
        if existing is None:
            self.ensure_profile_for_user(user["id"], user["email"])

        display_name = (profile_data.get("displayName") or "").strip()
        bio = (profile_data.get("bio") or "").strip()
        avatar_url = (profile_data.get("avatarUrl") or "").strip()

        if display_name == "":
            return {"error": "Display name is required."}

        if avatar_url == "":
            avatar_url = "https://i.pravatar.cc/200?u=" + str(user["id"])

        with self.engine.connect() as conn:
            stmt = (
                update(profiles_table)
                .where(profiles_table.c.user_id == user["id"])
                .values(
                    display_name=display_name,
                    bio=bio,
                    avatar_url=avatar_url,
                )
            )
            conn.execute(stmt)
            conn.commit()

        return self.get_profile_by_user_id(user["id"])

    def get_services(self, genre=""):
        with self.engine.connect() as conn:
            if genre.strip() == "":
                statement = select(services_table).order_by(services_table.c.id.desc())
            else:
                statement = (
                    select(services_table)
                    .where(services_table.c.genre.ilike("%" + genre.strip() + "%"))
                    .order_by(services_table.c.id.desc())
                )

            rows = conn.execute(statement).fetchall()

        services = []
        for row in rows:
            services.append(self.service_row_to_dict(row))
        return services

    def create_service_by_token(self, token, service_data):
        user = self.get_user_by_token(token)
        if user is None:
            return {"error": "Invalid token."}

        title = (service_data.get("title") or "").strip()
        genre = (service_data.get("genre") or "").strip()
        description = (service_data.get("description") or "").strip()
        price = (service_data.get("price") or "").strip()

        if title == "":
            return {"error": "Service title is required."}

        if genre == "":
            return {"error": "Genre is required."}

        if description == "":
            return {"error": "Description is required."}

        if price == "":
            return {"error": "Price is required."}

        with self.engine.connect() as conn:
            stmt = insert(services_table).values(
                user_id=user["id"],
                title=title,
                genre=genre,
                description=description,
                price=price,
            )
            result = conn.execute(stmt)
            conn.commit()
            new_id = result.inserted_primary_key[0]

        with self.engine.connect() as conn:
            statement = select(services_table).where(services_table.c.id == new_id)
            row = conn.execute(statement).fetchone()

        return self.service_row_to_dict(row)

    def add_user(self, user_data):
        email = (user_data.get("email") or "").strip().lower()
        password = user_data.get("password") or ""

        if email == "" or password == "":
            return {"error": "Email and password are required."}

        if len(password) < 6:
            return {"error": "Password must be at least 6 characters."}

        existing = self.get_user_by_email(email)
        if existing is not None:
            return {"error": "Email already registered."}

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
        self.ensure_profile_for_user(user["id"], user["email"])

        token = self.create_session(user["id"])
        return {"token": token, "user": user}

    def login_user(self, user_data):
        email = (user_data.get("email") or "").strip().lower()
        password = user_data.get("password") or ""

        if email == "" or password == "":
            return {"error": "Email and password are required."}

        row = self.get_user_by_email(email)
        if row is None:
            return {"error": "Invalid email or password."}

        password_hash = self.hash_password(password)
        if row.password_hash != password_hash:
            return {"error": "Invalid email or password."}

        user = self.user_row_to_dict(row)
        self.ensure_profile_for_user(user["id"], user["email"])

        token = self.create_session(user["id"])
        return {"token": token, "user": user}


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
        return {"error": "Missing token."}

    user = users_db.get_user_by_token(token)
    if user is None:
        return {"error": "Invalid token."}

    return user


@app.post("/logout")
def logout(payload: dict = Body(...)):
    token = payload.get("token") or ""
    if token == "":
        return {"error": "Missing token."}

    return users_db.logout(token)


@app.get("/profile")
def get_profile(token: str = ""):
    if token == "":
        return {"error": "Missing token."}

    profile = users_db.get_profile_by_token(token)
    if profile is None:
        return {"error": "Invalid token."}

    return profile


@app.post("/profile")
def update_profile(payload: dict = Body(...)):
    token = payload.get("token") or ""
    profile_data = payload.get("profile") or {}

    if token == "":
        return {"error": "Missing token."}

    return users_db.update_profile_by_token(token, profile_data)


@app.get("/services")
def get_services(genre: str = ""):
    return users_db.get_services(genre)


@app.post("/services")
def create_service(payload: dict = Body(...)):
    token = payload.get("token") or ""
    service_data = payload.get("service") or {}

    if token == "":
        return {"error": "Missing token."}

    return users_db.create_service_by_token(token, service_data)