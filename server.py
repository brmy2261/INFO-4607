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
    UniqueConstraint,
    select,
    insert,
    delete,
    func,
    text,
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import Optional
import hashlib
import uuid




from database import engine, test_connection

schema_name = "third_iteration"
metadata = MetaData(schema=schema_name)

users_table = Table("users", metadata, autoload_with=engine)
domains_table = Table("domains", metadata, autoload_with=engine)
categories_table = Table("categories", metadata, autoload_with=engine)
posts_table = Table("posts", metadata, autoload_with=engine)
post_images_table = Table("post_images", metadata, autoload_with=engine)
messages_table = Table("messages", metadata, autoload_with=engine)
ratings_table = Table("ratings", metadata, autoload_with=engine)



sessions_table = Table(
    "sessions",
    metadata,
    Column("session_id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("token", String, nullable=False, unique=True),
    Column("created_at", String, nullable=False),
    extend_existing=True,
)

post_likes_table = Table(
    "post_likes",
    metadata,
    Column("like_id", Integer, primary_key=True),
    Column("post_id", Integer, nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("created_at", String, nullable=False),
    UniqueConstraint("post_id", "user_id", name="uq_post_likes_post_user"),
    extend_existing=True,
)

metadata.create_all(engine, tables=[sessions_table, post_likes_table])


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LogoutRequest(BaseModel):
    token: str

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


class RatingCreate(BaseModel):
    token: str
    post_id: int
    rated_user_id: int
    score: int
    comment: Optional[str] = None


class LikeRequest(BaseModel):
    token: str




class AppDB:
    def __init__(self):
        self.engine = engine

    def now_dt(self):
        return datetime.now(timezone.utc)

    def now_iso(self):
        return self.now_dt().isoformat()

    def hash_password(self, password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def test_connection(self):
        with self.engine.connect() as conn:
            conn.execute(text("select 1"))
            return conn.execute(select(func.count()).select_from(domains_table)).scalar_one()

    


    def user_to_dict(self, row):
        return {
            "user_id": row.user_id,
            "email": row.email,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "created_at": row.created_at,
            "is_active": bool(row.is_active),
        }

    def get_user_by_id(self, user_id: int):
        with self.engine.connect() as conn:
            row = conn.execute(
                select(users_table).where(users_table.c.user_id == user_id)
            ).fetchone()
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
            result = conn.execute(
                insert(sessions_table).values(
                    user_id=user_id,
                    token=token,
                    created_at=self.now_iso(),
                )
            )
            session_id = result.inserted_primary_key[0]
        return {"session_id": session_id, "token": token}


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

        if not first_name or not last_name:
            return{"error": "First and last name are required."}

        if len(password) < 6:
            return {"error": "Password must be at least 6 characters."}
        if not email.endswith("colorado.edu"):
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
        session = self.create_session(user_id)
        return {"message": "user created", "token": session["token"], "user": user}

    def login(self, payload):
        row = self.get_user_row_by_email(payload.email)
        if row is None:
            return {"error": "Invalid email or password."}
        if row.password_hash != self.hash_password(payload.password):
            return {"error": "Invalid email or password."}
        session = self.create_session(row.user_id)
        return {"token": session["token"], "user": self.user_to_dict(row)}

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

    def list_categories(self, domain_id=None):
        query = select(categories_table).order_by(categories_table.c.category_id)

        if domain_id is not None:
            query = query.where(categories_table.c.domain_id == domain_id)
        with self.engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        return [
            {
                "category_id": row.category_id,
                "domain_id": row.domain_id,
                "name": row.name,
            }
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
                select(post_images_table).where(post_images_table.c.post_id == post_id)
            ).fetchall()
        return [
            {
                "image_id": row.image_id,
                "post_id": row.post_id,
                "image_url": row.image_url,
                "uploaded_at": row.uploaded_at,
            }
            for row in rows
        ]

    def get_post_details(self, post_id, user_id=None):
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
            like_count = conn.execute(
                select(func.count()).select_from(post_likes_table).where(
                    post_likes_table.c.post_id == post_id
                )
            ).scalar_one()
            user_has_liked = False
            if user_id is not None:
                user_has_liked = conn.execute(
                    select(post_likes_table.c.like_id).where(
                        (post_likes_table.c.post_id == post_id) &
                        (post_likes_table.c.user_id == user_id)
                    )
                ).fetchone() is not None
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
            "like_count": like_count,
            "user_has_liked": user_has_liked,
            "images": self.get_post_images(row.post_id),
        }

    def get_user_posts(self, user_id, viewer_user_id=None):
        query = select(posts_table.c.post_id).where(
            posts_table.c.creator_user_id == user_id
        ).order_by(
            posts_table.c.created_at.desc(),
            posts_table.c.post_id.desc(),
        )
        with self.engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        return [self.get_post_details(row.post_id, user_id=viewer_user_id) for row in rows]

    def list_posts(self, category_id=None, domain_id=None, user_id=None):
        query = (select(posts_table.c.post_id).select_from(
            posts_table.join(
                categories_table,
                posts_table.c.category_id == categories_table.c.category_id,
            )
        ).order_by(
            posts_table.c.created_at.desc(),
            posts_table.c.post_id.desc(),
        )
    )
        if domain_id is not None:
            query = query.where(categories_table.c.domain_id == domain_id)
        if category_id is not None:
            query = query.where(posts_table.c.category_id == category_id)
        with self.engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        return [self.get_post_details(row.post_id, user_id=user_id) for row in rows]

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
                insert(post_images_table).values(
                    post_id=post_id,
                    image_url=payload.image_url.strip(),
                    uploaded_at=uploaded_at,
                )
            )
            image_id = result.inserted_primary_key[0]

        return {
            "success": True,
            "image": {
                "image_id": image_id,
                "post_id": post_id,
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

        sent_at = self.now_iso()
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(messages_table).values(
                    sender_user_id=sender["user_id"],
                    receiver_user_id=payload.receiver_user_id,
                    content=payload.content.strip(),
                    sent_at=sent_at,
                )
            )
            message_id = result.inserted_primary_key[0]

        return {
            "success": True,
            "message": {
                "message_id": message_id,
                "sender_user_id": sender["user_id"],
                "receiver_user_id": payload.receiver_user_id,
                "content": payload.content.strip(),
                "sent_at": sent_at,
            },
        }

    def get_messages(self, token, other_user_id=None):
        user, error = self.require_user(token)
        if error is not None:
            return error
        uid = user["user_id"]
        if other_user_id is not None:
            with self.engine.connect() as conn:
                rows = conn.execute(
                    select(messages_table)
                    .where(
                        (
                            (messages_table.c.sender_user_id == uid) &
                            (messages_table.c.receiver_user_id == other_user_id)
                        ) |
                        (
                            (messages_table.c.sender_user_id == other_user_id) &
                            (messages_table.c.receiver_user_id == uid)
                        )
                    )
                    .order_by(messages_table.c.sent_at.asc())
                ).fetchall()
            return {
                "thread": [
                    {
                        "message_id": row.message_id,
                        "sender_user_id": row.sender_user_id,
                        "receiver_user_id": row.receiver_user_id,
                        "content": row.content,
                        "sent_at": row.sent_at,
                    }
                    for row in rows
                ]
            }
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(messages_table)
                .where(
                    (messages_table.c.sender_user_id == uid) |
                    (messages_table.c.receiver_user_id == uid)
                )
                .order_by(messages_table.c.sent_at.desc())
            ).fetchall()
        seen = {}
        for row in rows:
            other_id = row.receiver_user_id if row.sender_user_id == uid else row.sender_user_id
            if other_id not in seen:
                seen[other_id] = row
        conversations = []
        for other_id, row in seen.items():
            other_user = self.get_user_by_id(other_id)
            if other_user:
                conversations.append({
                    "other_user_id": other_id,
                    "first_name": other_user["first_name"],
                    "last_name": other_user["last_name"],
                    "last_message": row.content,
                    "last_sent_at": row.sent_at,
                })
        return {"conversations": conversations}

    def delete_post(self, post_id, token):
        user, error = self.require_user(token)
        if error is not None:
            return error
        post_row = self.get_post_row(post_id)
        if post_row is None:
            return {"error": "Post not found."}
        if post_row.creator_user_id != user["user_id"]:
            return {"error": "You can only delete your own posts."}
        with self.engine.begin() as conn:
            conn.execute(delete(posts_table).where(posts_table.c.post_id == post_id))
        return {"success": True}

    def toggle_like(self, post_id, token):
        user, error = self.require_user(token)
        if error is not None:
            return error
        if self.get_post_row(post_id) is None:
            return {"error": "Post not found."}
        uid = user["user_id"]
        with self.engine.connect() as conn:
            existing = conn.execute(
                select(post_likes_table.c.like_id).where(
                    (post_likes_table.c.post_id == post_id) &
                    (post_likes_table.c.user_id == uid)
                )
            ).fetchone()
        if existing:
            with self.engine.begin() as conn:
                conn.execute(
                    delete(post_likes_table).where(
                        (post_likes_table.c.post_id == post_id) &
                        (post_likes_table.c.user_id == uid)
                    )
                )
            liked = False
        else:
            with self.engine.begin() as conn:
                conn.execute(
                    insert(post_likes_table).values(
                        post_id=post_id,
                        user_id=uid,
                        created_at=self.now_iso(),
                    )
                )
            liked = True
        with self.engine.connect() as conn:
            like_count = conn.execute(
                select(func.count()).select_from(post_likes_table).where(
                    post_likes_table.c.post_id == post_id
                )
            ).scalar_one()
        return {"liked": liked, "like_count": like_count}

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
def logout(payload: LogoutRequest):
    return db.logout(payload.token)


@app.get("/domains")
def list_domains():
    return {"domains": db.list_domains()}


@app.get("/categories")
def list_categories(domain_id:int | None = None):
    return {"categories": db.list_categories(domain_id)}


@app.get("/posts")
def list_posts(category_id: int | None = None, domain_id: int | None = None, token: str | None = None):
    user_id = None
    if token:
        user = db.get_user_by_token(token)
        if user:
            user_id = user["user_id"]
    return {"posts": db.list_posts(category_id=category_id, domain_id=domain_id, user_id=user_id)}


@app.post("/posts")
def create_post(payload: CreatePostRequest):
    return db.create_post(payload)


@app.post("/posts/{post_id}/images")
def add_post_image(post_id: int, payload: AddImageRequest):
    return db.add_post_image(post_id, payload)


@app.post("/posts/{post_id}/like")
def toggle_like(post_id: int, payload: LikeRequest):
    return db.toggle_like(post_id, payload.token)


@app.post("/messages")
def create_message(payload: MessageCreate):
    return db.create_message(payload)


@app.post("/ratings")
def create_rating(payload: RatingCreate):
    return db.create_rating(payload)


@app.get("/messages")
def get_messages(token: str):
    return db.get_messages(token)


@app.get("/messages/thread")
def get_message_thread(token: str, other_user_id: int):
    return db.get_messages(token, other_user_id=other_user_id)


@app.get("/users/{user_id}/posts")
def get_user_posts(user_id: int):
    return {"posts": db.get_user_posts(user_id)}


class DeletePostRequest(BaseModel):
    token: str

@app.delete("/posts/{post_id}")
def delete_post(post_id: int, payload: DeletePostRequest):
    return db.delete_post(post_id, payload.token)
