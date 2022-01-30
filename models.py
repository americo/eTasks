from flask_login import UserMixin

# from db.sqlite import *
from app import db


class User(UserMixin, db.Model):
    id = db.Column(
        db.Integer, primary_key=True
    )  # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    otp_code = db.Column(db.Integer)
    reset_token = db.Column(db.String(256))
    done_tasks = db.Column(db.Integer)
    csrf_token = db.Column(db.String(100))
    avatar_name = db.Column(db.String(100))


class Task(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    title = db.Column(db.String(1000))
