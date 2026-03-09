from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Boolean,
    create_engine,
    select,
    insert,
    delete,
    func,
    and_,
)
from sqlalchemy.exc import IntegrityError
import hashlib
import uuid
from datetime import datetime
from typing import Optional

DATABASE_URL = "sqlite:///studentquest.db"
metadata = MetaData()

schools_table = Table(
    "schools",
    metadata,
    Column("school_id", Integer, primary_key=True),
    Column("school_name", String, nullable=False),
    Column("domain", String, nullable=False, unique=True),
)

users_table = Table(
    "users",
    metadata,
    Column("user_id", Integer, primary_key=True),
    Column("email", String, nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
    Column("first_name", String, nullable=False),
    Column("last_name", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("session_id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("token", String, nullable=False, unique=True),
    Column("created_at", String, nullable=False),
)

domains_table = Table(
    "domains",
    metadata,
    Column("domain_id", Integer, primary_key=True),
    Column("domain_name", String, nullable=False, unique=True),
)

categories_table = Table(
    "categories",
    metadata,
    Column("category_id", Integer, primary_key=True),
    Column("domain_id", Integer, nullable=False),
    Column("name", String, nullable=False),
)

posts_table = Table(
    "posts",
    metadata,
    Column("post_id", Integer, primary_key=True),
    Column("creator_user_id", Integer, nullable=False),
    Column("category_id", Integer, nullable=False),
    Column("title", String, nullable=False),
    Column("description", String, nullable=False),
    Column("desired_payout", Float, nullable=True),
    Column("status", String, nullable=False, default="open"),
    Column("created_at", String, nullable=False),
    Column("expires_at", String, nullable=True),
)

posts_images_table = Table(
    "posts_images",
    metadata,
    Column("image_id", Integer, primary_key=True),
    Column("posts_id", Integer, nullable=False),
    Column("image_url", String, nullable=False),
    Column("uploaded_at", String, nullable=False),
)

messages_table = Table(
    "messages",
    metadata,
    Column("message_id", Integer, primary_key=True),
    Column("sender_user_id", Integer, nullable=False),
    Column("receiver_user_id", Integer, nullable=False),
    Column("request_id", Integer, nullable=True),
    Column("content", String, nullable=False),
    Column("sent_at", String, nullable=False),
    Column("is_read", Boolean, nullable=False, default=False),
)

ratings_table = Table(
    "ratings",
    metadata,
    Column("rating_id", Integer, primary_key=True),
    Column("post_id", Integer, nullable=False),
    Column("rater_user_id", Integer, nullable=False),
    Column("rated_user_id", Integer, nullable=False),
    Column("score", Integer, nullable=False),
    Column("comment", String, nullable=True),
    Column("created_at", String, nullable=False),
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreatePostRequest(BaseModel):
    token: str
    category_id: int
    title: str
    description: str
    desired_payout: Optional[float] = None
    expires_at: Optional[str] = None


class AddImageRequest(BaseModel):
    token: str
    image_url: str


class MessageCreate(BaseModel):
    token: str
    receiver_user_id: int
    content: str
    request_id: Optional[int] = None


class RatingCreate(BaseModel):
    token: str
    post_id: int
    rated_user_id: int
    score: int
    comment: Optional[str] = None


class AppDB:
    def __init__(self):
        self.engine = create_engine(
            DATABASE_URL,
            future=True,
            connect_args={"check_same_thread": False})
        metadata.create_all(self.engine)
        self.seed_reference_data()

    def now_iso(self):
        return datetime.utcnow().isoformat()

    def hash_password(self, password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def test_connection(self):
        with self.engine.connect() as conn:
            return conn.execute(select(func.count()).select_from(domains_table)).scalar_one()

    def seed_reference_data(self):
        starter_domains = ["Academic", "Services", "Social"]
        starter_categories = [
            ("Academic", "Tutoring"),
            ("Academic", "Study Group"),
            ("Academic", "Notes"),
            ("Services", "Moving Help"),
            ("Services", "Errands"),
            ("Services", "Tech Help"),
            ("Social", "Events"),
            ("Social", "Clubs"),
            ("Social", "Roommates"),
        ]
        starter_schools = [
            ("University of Colorado Boulder", "colorado.edu"),
            ("University of Colorado Colorado Springs", "uccs.edu"),
        ]

        with self.engine.begin() as conn:
            existing_domains = conn.execute(select(domains_table.c.domain_id)).fetchone()
            if existing_domains is None:
                for name in starter_domains:
                    conn.execute(insert(domains_table).values(domain_name=name))

            existing_categories = conn.execute(select(categories_table.c.category_id)).fetchone()
            if existing_categories is None:
                domain_rows = conn.execute(select(domains_table)).fetchall()
                domain_lookup = {row.domain_name: row.domain_id for row in domain_rows}
                for domain_name, category_name in starter_categories:
                    conn.execute(
                        insert(categories_table).values(
                            domain_id=domain_lookup[domain_name],
                            name=category_name,
                        )
                    )

            existing_schools = conn.execute(select(schools_table.c.school_id)).fetchone()
            if existing_schools is None:
                for school_name, domain in starter_schools:
                    conn.execute(
                        insert(schools_table).values(
                            school_name=school_name,
                            domain=domain,
                        )
                    )

    def user_to_dict(self, row):
        return {
            "user_id": row.user_id,
            "email": row.email,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "created_at": row.created_at,
            "is_active": bool(row.is_active),
        }

    def get_user_by_id(self, user_id):
        with self.engine.connect() as conn:
            row = conn.execute(select(users_table).where(users_table.c.user_id == user_id)).fetchone()
        if row is None:
            return None
        return self.user_to_dict(row)

    def get_user_row_by_email(self, email):
        with self.engine.connect() as conn:
            return conn.execute(
                select(users_table).where(users_table.c.email == email.lower().strip())
            ).fetchone()

    def create_session(self, user_id):
        token = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                insert(sessions_table).values(
                    user_id=user_id,
                    token=token,
                    created_at=self.now_iso(),
                )
            )
        return token

    def get_user_by_token(self, token):
        if not token:
            return None
        with self.engine.connect() as conn:
            session_row = conn.execute(
                select(sessions_table).where(sessions_table.c.token == token)
            ).fetchone()
        if session_row is None:
            return None
        return self.get_user_by_id(session_row.user_id)

    def require_user(self, token):
        user = self.get_user_by_token(token)
        if user is None:
            return None, {"error": "Invalid or missing token."}
        return user, None

    def create_user(self, payload):
        email = payload.email.lower().strip()
        password = payload.password.strip()
        first_name = payload.first_name.strip()
        last_name = payload.last_name.strip()

        if len(password) < 6:
            return {"error": "Password must be at least 6 characters."}
        if not email.endswith(".edu"):
            return {"error": "Email must be a .edu address."}

        password_hash = self.hash_password(password)

        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    insert(users_table).values(
                        email=email,
                        password_hash=password_hash,
                        first_name=first_name,
                        last_name=last_name,
                        created_at=self.now_iso(),
                        is_active=True,
                    )
                )
                user_id = result.inserted_primary_key[0]
        except IntegrityError:
            return {"error": "Email already exists."}

        user = self.get_user_by_id(user_id)
        token = self.create_session(user_id)
        return {"message": "user created", "token": token, "user": user}

    def login(self, payload):
        row = self.get_user_row_by_email(payload.email)
        if row is None:
            return {"error": "Invalid email or password."}
        if row.password_hash != self.hash_password(payload.password):
            return {"error": "Invalid email or password."}
        token = self.create_session(row.user_id)
        return {"token": token, "user": self.user_to_dict(row)}

    def logout(self, token):
        with self.engine.begin() as conn:
            conn.execute(delete(sessions_table).where(sessions_table.c.token == token))
        return {"success": True}

    def list_users(self):
        with self.engine.connect() as conn:
            rows = conn.execute(select(users_table).order_by(users_table.c.user_id)).fetchall()
        return [self.user_to_dict(row) for row in rows]

    def list_domains(self):
        with self.engine.connect() as conn:
            rows = conn.execute(select(domains_table).order_by(domains_table.c.domain_id)).fetchall()
        return [
            {"domain_id": row.domain_id, "domain_name": row.domain_name}
            for row in rows
        ]

    def list_categories(self):
        with self.engine.connect() as conn:
            rows = conn.execute(select(categories_table).order_by(categories_table.c.category_id)).fetchall()
        return [
            {
                "category_id": row.category_id,
                "domain_id": row.domain_id,
                "name": row.name,
            }
            for row in rows
        ]

    def list_schools(self):
        with self.engine.connect() as conn:
            rows = conn.execute(select(schools_table).order_by(schools_table.c.school_id)).fetchall()
        return [
            {"school_id": row.school_id, "school_name": row.school_name, "domain": row.domain}
            for row in rows
        ]

    def get_category(self, category_id):
        with self.engine.connect() as conn:
            return conn.execute(
                select(categories_table).where(categories_table.c.category_id == category_id)
            ).fetchone()

    def get_post_row(self, post_id):
        with self.engine.connect() as conn:
            return conn.execute(select(posts_table).where(posts_table.c.post_id == post_id)).fetchone()

    def get_post_images(self, post_id):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(posts_images_table).where(posts_images_table.c.posts_id == post_id)
            ).fetchall()
        return [
            {
                "image_id": row.image_id,
                "posts_id": row.posts_id,
                "image_url": row.image_url,
                "uploaded_at": row.uploaded_at,
            }
            for row in rows
        ]

    def get_post_details(self, post_id):
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    posts_table.c.post_id,
                    posts_table.c.creator_user_id,
                    posts_table.c.category_id,
                    posts_table.c.title,
                    posts_table.c.description,
                    posts_table.c.desired_payout,
                    posts_table.c.status,
                    posts_table.c.created_at,
                    posts_table.c.expires_at,
                    users_table.c.email.label("creator_email"),
                    users_table.c.first_name.label("creator_first_name"),
                    users_table.c.last_name.label("creator_last_name"),
                    categories_table.c.name.label("category_name"),
                    domains_table.c.domain_id,
                    domains_table.c.domain_name,
                )
                .select_from(
                    posts_table.join(users_table, posts_table.c.creator_user_id == users_table.c.user_id)
                    .join(categories_table, posts_table.c.category_id == categories_table.c.category_id)
                    .join(domains_table, categories_table.c.domain_id == domains_table.c.domain_id)
                )
                .where(posts_table.c.post_id == post_id)
            ).fetchone()
        if row is None:
            return None
        return {
            "post_id": row.post_id,
            "creator_user_id": row.creator_user_id,
            "creator_email": row.creator_email,
            "creator_first_name": row.creator_first_name,
            "creator_last_name": row.creator_last_name,
            "category_id": row.category_id,
            "category_name": row.category_name,
            "domain_id": row.domain_id,
            "domain_name": row.domain_name,
            "title": row.title,
            "description": row.description,
            "desired_payout": row.desired_payout,
            "status": row.status,
            "created_at": row.created_at,
            "expires_at": row.expires_at,
            "images": self.get_post_images(row.post_id),
        }

    def list_posts(self):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(posts_table.c.post_id)
                .order_by(posts_table.c.created_at.desc(), posts_table.c.post_id.desc())
            ).fetchall()
        return [self.get_post_details(row.post_id) for row in rows]

    def create_post(self, payload):
        user, error = self.require_user(payload.token)
        if error is not None:
            return error

        category_row = self.get_category(payload.category_id)
        if category_row is None:
            return {"error": "Category not found."}

        title = payload.title.strip()
        description = payload.description.strip()
        if title == "" or description == "":
            return {"error": "title and description are required."}

        status = "open"
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(posts_table).values(
                    creator_user_id=user["user_id"],
                    category_id=payload.category_id,
                    title=title,
                    description=description,
                    desired_payout=payload.desired_payout,
                    status=status,
                    created_at=self.now_iso(),
                    expires_at=payload.expires_at,
                )
            )
            post_id = result.inserted_primary_key[0]

        return {"success": True, "post": self.get_post_details(post_id)}

    def add_post_image(self, post_id, payload):
        user, error = self.require_user(payload.token)
        if error is not None:
            return error

        post_row = self.get_post_row(post_id)
        if post_row is None:
            return {"error": "Post not found."}
        if post_row.creator_user_id != user["user_id"]:
            return {"error": "You can only add images to your own posts."}
        if payload.image_url.strip() == "":
            return {"error": "image_url is required."}

        uploaded_at = self.now_iso()
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(posts_images_table).values(
                    posts_id=post_id,
                    image_url=payload.image_url.strip(),
                    uploaded_at=uploaded_at,
                )
            )
            image_id = result.inserted_primary_key[0]

        return {
            "success": True,
            "image": {
                "image_id": image_id,
                "posts_id": post_id,
                "image_url": payload.image_url.strip(),
                "uploaded_at": uploaded_at,
            },
        }

    def create_message(self, payload):
        sender, error = self.require_user(payload.token)
        if error is not None:
            return error
        if payload.content.strip() == "":
            return {"error": "content is required."}
        receiver = self.get_user_by_id(payload.receiver_user_id)
        if receiver is None:
            return {"error": "Receiver not found."}
        if payload.request_id is not None and self.get_post_row(payload.request_id) is None:
            return {"error": "Referenced post was not found."}

        sent_at = self.now_iso()
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(messages_table).values(
                    sender_user_id=sender["user_id"],
                    receiver_user_id=payload.receiver_user_id,
                    request_id=payload.request_id,
                    content=payload.content.strip(),
                    sent_at=sent_at,
                    is_read=False,
                )
            )
            message_id = result.inserted_primary_key[0]

        return {
            "success": True,
            "message": {
                "message_id": message_id,
                "sender_user_id": sender["user_id"],
                "receiver_user_id": payload.receiver_user_id,
                "request_id": payload.request_id,
                "content": payload.content.strip(),
                "sent_at": sent_at,
                "is_read": False,
            },
        }

    def create_rating(self, payload):
        rater, error = self.require_user(payload.token)
        if error is not None:
            return error
        if payload.score < 1 or payload.score > 5:
            return {"error": "score must be between 1 and 5."}
        if payload.rated_user_id == rater["user_id"]:
            return {"error": "You cannot rate yourself."}
        rated_user = self.get_user_by_id(payload.rated_user_id)
        if rated_user is None:
            return {"error": "User to rate was not found."}
        post_row = self.get_post_row(payload.post_id)
        if post_row is None:
            return {"error": "Post not found."}

        created_at = self.now_iso()
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(ratings_table).values(
                    post_id=payload.post_id,
                    rater_user_id=rater["user_id"],
                    rated_user_id=payload.rated_user_id,
                    score=payload.score,
                    comment=(payload.comment or "").strip() or None,
                    created_at=created_at,
                )
            )
            rating_id = result.inserted_primary_key[0]

        return {
            "success": True,
            "rating": {
                "rating_id": rating_id,
                "post_id": payload.post_id,
                "rater_user_id": rater["user_id"],
                "rated_user_id": payload.rated_user_id,
                "score": payload.score,
                "comment": (payload.comment or "").strip() or None,
                "created_at": created_at,
            },
        }


app = FastAPI(title="StudentQuest API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = AppDB()


@app.get("/")
def root():
    return {"message": "StudentQuest backend is running."}


@app.get("/health/db")
def health_db():
    return {"db": "ok", "select_1": 1, "domains_count": db.test_connection()}


@app.post("/users")
def create_user(payload: UserCreate):
    return db.create_user(payload)


@app.post("/register")
def register(payload: UserCreate):
    return db.create_user(payload)


@app.get("/users")
def list_users():
    return {"users": db.list_users()}


@app.post("/login")
def login(payload: LoginRequest):
    return db.login(payload)


@app.get("/me")
def me(token: str):
    user = db.get_user_by_token(token)
    if user is None:
        return {"error": "Invalid token."}
    return {"user": user}


@app.post("/logout")
def logout(token: str):
    return db.logout(token)


@app.get("/schools")
def list_schools():
    return {"schools": db.list_schools()}


@app.get("/domains")
def list_domains():
    return {"domains": db.list_domains()}


@app.get("/categories")
def list_categories():
    return {"categories": db.list_categories()}


@app.get("/posts")
def list_posts():
    return {"posts": db.list_posts()}


@app.post("/posts")
def create_post(payload: CreatePostRequest):
    return db.create_post(payload)


@app.post("/posts/{post_id}/images")
def add_post_image(post_id: int, payload: AddImageRequest):
    return db.add_post_image(post_id, payload)


@app.post("/messages")
def create_message(payload: MessageCreate):
    return db.create_message(payload)


@app.post("/ratings")
def create_rating(payload: RatingCreate):
    return db.create_rating(payload)
