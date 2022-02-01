from crypt import methods
import email
from flask import (
    Blueprint,
    make_response,
    render_template,
    redirect,
    url_for,
    request,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Task
from flask_login import login_user, current_user, logout_user
from app import db

import binascii
import os
import random

auth = Blueprint("auth", __name__)


def generate_key():
    return binascii.hexlify(os.urandom(20)).decode()


@auth.route("/login")
def login():
    return render_template("login.html")


@auth.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False

    user = User.query.filter_by(email=email).first()

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not check_password_hash(user.password, password):
        return render_template("login.html", login_failed=True)

    login_user(user, remember=remember)
    csrf_token = generate_key()
    user.csrf_token = csrf_token
    user.otp_code = int(random.randint(1111, 9999))
    db.session.commit()

    resp = make_response(redirect(url_for("auth.login2")))
    resp.set_cookie("user", current_user.email)
    return resp


@auth.route("/login2", methods=["GET"])
def login2():
    user = User.query.filter_by(id=current_user.id).first()
    return render_template("login2.html", otp_code=user.otp_code)


@auth.route("/login2", methods=["POST"])
def login2_post():
    otp_code = request.form.get("otp_code")
    cookie_user = request.cookies.get("user")
    user = User.query.filter_by(email=cookie_user).first()

    if int(otp_code) != user.otp_code:
        return render_template("login2.html", login_failed=True, otp_code=user.otp_code)

    login_user(user, remember=True)

    return redirect(url_for("main.dashboard"))


@auth.route("/forgotPassword")
def forgotPassword():
    return render_template("forgot-password.html")


@auth.route("/forgotPassword", methods=["POST"])
def forgotPassword_post():
    email = request.form.get("email")

    user = User.query.filter_by(email=email).first()

    if not user:
        return render_template("forgot-password.html", reset_failed=True)

    user.reset_token = generate_key()
    db.session.commit()

    return render_template(
        "reset-password.html", email=email, reset_token=user.reset_token
    )


@auth.route("/resetPassword", methods=["POST"])
def resetPassword_post():
    email = request.form.get("email")
    reset_token = request.form.get("token")
    newpassword = request.form.get("newpassword")
    newpassword2 = request.form.get("newpassword2")

    user = User.query.filter_by(reset_token=reset_token).first()
    if not user:
        return render_template("reset-password", reset_failed=True)

    user = User.query.filter_by(email=email).first()
    user.password = generate_password_hash(newpassword, method="sha256")
    user.reset_token = generate_key()
    db.session.commit()

    return redirect(url_for("auth.login"))


@auth.route("/register")
def register():
    return render_template("register.html")


@auth.route("/register", methods=["POST"])
def register_post():
    email = request.form.get("email")
    name = request.form.get("name")
    password = request.form.get("password")

    user = User.query.filter_by(
        email=email
    ).first()  # if this returns a user, then the email already exists in database

    if (
        user
    ):  # if a user is found, we want to redirect back to register page so user can try again
        return redirect(url_for("auth.register"))

    # create new user with the form data. Hash the password so plaintext version isn't saved.
    new_user = User(
        email=email,
        name=name,
        password=generate_password_hash(password, method="sha256"),
        otp_code=0000,
        reset_token=generate_key(),
        done_tasks=0,
        avatar_name="profile.png",
    )

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    if user:
        flash("Email address already exists")
        return redirect(url_for("auth.register"))

    return redirect(url_for("auth.login"))


@auth.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
