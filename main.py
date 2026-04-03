from fastapi import FastAPI, Query
from database import test_connection
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from database import engine
import hashlib
from typing import Optional, List, Literal
from datetime import datetime

app = FastAPI()


@app.get("/health/db")
def health_db():
    return{"db":"ok", "select_1": test_connection()}

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

@app.post("/users")

def create_user(payload: UserCreate):
    pw_hash = hashlib.sha256(payload.password.encode("utf-8")).hexdigest()

    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("""
                    INSERT INTO users (email, password_hash, first_name, last_name)
                    VALUES (:email, :password_hash, :first_name, :last_name)
                    RETURNING user_id, email, first_name, last_name
                    """),
                    {
                        "email":payload.email, 
                        "password_hash":pw_hash,
                        "first_name":payload.first_name,
                        "last_name": payload.last_name
                        },
            ).mappings().one()

        return {"message":"user created", "user": dict(row)}
    
    except IntegrityError:
        raise HTTPException(status_code=409, detail="email already exists") #409 = duplicate resource

# open db connection, selects all users, 
# converts each row to a dict and returns JSON
@app.get("/users")
def list_users():
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                    select user_id, first_name, last_name, email, created_at, password_hash
                    from users
                 """)
        ).mappings().all()

    return{"users": [dict(row) for row in rows]}

class login_request(BaseModel):
    email: EmailStr
    password: str

@app.post("/login")
def create_login(payload: login_request):
    pw_hash = hashlib.sha256(payload.password.encode("utf-8")).hexdigest()

    with engine.begin() as conn:
        row = conn.execute(
            text("""
                select user_id, email, first_name, last_name, created_at
                 from users
                 where email = :email
                 and password_hash = :password_hash
                 """),

                 {
                     "email": payload.email,
                     "password_hash": pw_hash,
                 },

        ). mappings().first()

    if row is None:
        raise HTTPException(status_code = 401, detail = "invalid email or password")
    
    return {"user": dict(row)}

# figure out this and how it works with having constrained tables in postgres
# class DomainCreate(BaseModel):
#     domain_name: str

class DomainOut(BaseModel):
    domain_id: int
    domain_name: str

@app.get("/domains")
def list_domains():
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                select domain_id, domain_name
                 from domains
                 order by domain_id
                """
            ).mappings().all()
        )
    return {"domains": [dict(r) for r in rows]}

@app.get("/categories")
def list_categories():
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                select category_id, domain_id, name
                 from categories
                 order by category_id 
                """)
        ).mappings().all()
    return{"categories": [dict(r) for r in rows]}


# POSTS: returning to this

# RequestStatus = Literal["open","pending","closed","expired"]

# class CreatePost(BaseModel):
#     creator_user_id: int
#     category_id: int
#     domain_id: int
#     title: str
#     description: str
#     desired_payout: Optional[float]
#     created_at: Optional[datetime]
#     expires_at: Optional[datetime]





