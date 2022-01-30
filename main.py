import os
import json
from flask import (
    Blueprint,
    render_template,
    render_template_string,
    request,
    url_for,
    redirect,
    flash,
    Flask,
    abort,
    send_from_directory,
)
from flask_login import login_required, current_user
from xml.dom import minidom
from itsdangerous import base64_decode, base64_encode
from lxml import etree
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import Admin, Task, User
from app import db
from auth import generate_key

main = Blueprint("main", __name__)

# Admin panel credentials
USERNAME = "admin"
PASSWORD = "admin"

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "svg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route("/")
def index():
    return redirect(url_for("auth.login"))


@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@main.route("/profile/edit", methods=["POST"])
@login_required
def profile_edit():
    email = request.form.get("email")
    name = request.form.get("name")
    csrf_token = request.form.get("csrf_token")
    user = User.query.filter_by(id=current_user.id).first()

    if not user.csrf_token == csrf_token:
        return "<h2>Token Anti-CSRF inválido.</h2>"

    user.name = name
    user.email = email
    db.session.commit()

    return redirect(url_for("main.profile"))


@main.route("/profile/security", methods=["POST"])
@login_required
def profile_security_edit():
    new_password = request.form.get("new_password")
    confirm_new_password = request.form.get("confirm_new_password")
    csrf_token = request.form.get("csrf_token")

    try:
        userForToken = User.query.filter_by(csrf_token=csrf_token).first()
    except:
        pass

    if not userForToken:
        return "<h2>Token Anti-CSRF inválido.</h2>"

    user = User.query.filter_by(id=current_user.id).first()

    if new_password != confirm_new_password:
        return render_template("profile.html", change_password_failed=True)

    user.password = generate_password_hash(new_password, method="sha256")
    db.session.commit()

    return render_template("profile.html", change_password_successfull=True)


@main.route("/delete-account", methods=["GET"])
@login_required
def delete_account():
    user = User.query.filter_by(id=current_user.id).first()

    if user.avatar_name != "profile.png":
        os.system(f"rm ./uploads/profile/{user.avatar_name}")

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for("auth.register"))


@main.route("/dashboard")
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id)
    all_tasks = []
    for task in tasks:
        all_tasks.append(task)

    total_tasks = len(all_tasks)

    return render_template("dashboard.html", tasks=all_tasks, total_tasks=total_tasks)


@main.route("/add-task", methods=["POST"])
@login_required
def add_task_post():
    # create new task with the form data.
    title = request.form.get("title")
    csrf_token = request.form.get("csrf_token")
    new_task = Task(title=title, user_id=current_user.id)

    user = User.query.filter_by(id=current_user.id).first()

    if isinstance(csrf_token, str) == False:
        # add the new task to the database
        db.session.add(new_task)
        db.session.commit()
    elif user.csrf_token != csrf_token:
        return "<h2>Token Anti-CSRF inválido.</h2>"
    else:
        # add the new task to the database
        db.session.add(new_task)
        db.session.commit()

    return redirect(url_for("main.dashboard"))


@main.route("/delete-task", methods=["GET", "POST"])
@login_required
def delete_task():
    if request.method == "GET":
        task_id = request.args.get("id", "")
        csrf_token = request.args.get("csrf_token", "")
        user = User.query.filter_by(id=current_user.id).first()
        if user.csrf_token != csrf_token:
            return "<h2>Token Anti-CSRF inválido.</h2>"
    elif request.method == "POST":
        task_id = request.form.get("id")

    task = Task.query.filter_by(id=task_id).first()
    if task:
        db.session.delete(task)
        db.session.commit()

    user = User.query.filter_by(id=current_user.id).first()
    user.done_tasks = user.done_tasks + 1
    db.session.commit()

    return redirect(url_for("main.dashboard"))


@main.route("/upload", methods=["POST"])
@login_required
def upload_file():
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join("./uploads/profile", filename))

            user = User.query.filter_by(id=current_user.id).first()

            if user.avatar_name != "profile.png":
                os.system(f"rm ./uploads/profile/{user.avatar_name}")

            user.avatar_name = filename
            db.session.commit()

            return redirect(url_for("main.profile"))


@main.route("/uploads/profile/<filename>")
def uploaded_file(filename):
    try:
        file = open(f"./uploads/profile/{filename}")
        file_data = file.read()
        xml = file_data
        parser = etree.XMLParser(no_network=False)
        doc = etree.tostring(etree.fromstring(str(xml), parser))
        return doc
    except Exception as e:
        return (
            send_from_directory("./uploads/profile", filename),
            200,
            {"Content-Type": "image/jpeg; charset=utf-8"},
        )


@main.route("/admin")
def admin():
    return render_template("admin.html")


@main.route("/admin/dashboard")
def adminDashboard():
    users = User.query.all()
    all_users = []
    for user in users:
        all_users.append(user)

    try:
        admin_session = request.cookies.get("admin_session")
        admin_session = base64_decode(admin_session)
        admin_session = json.loads(admin_session)
        username = admin_session["user"]
        admin_user = Admin.query.filter_by(username=username).first()
        if admin_user:
            return render_template(
                "adminDashboard.html", admin_user=admin_user, users=all_users
            )
    except:
        pass

    return "<h3>Você não tem a permissão para acessar a administração</h3>", 403


@main.route("/message")
def message():
    try:
        admin_session = request.cookies.get("admin_session")
        admin_session = base64_decode(admin_session)
        admin_session = json.loads(admin_session)
        username = admin_session["user"]
    except:
        username = ""

    return f"<result><code>1</code><msg>{username}</msg></result>"


@main.route("/doLogin", methods=["POST", "GET"])
def doLogin():
    result = None
    parsed_xml = None
    if request.method == "POST":
        try:
            xml = request.data.decode("utf-8")
            parser = etree.XMLParser(no_network=False)
            doc = etree.tostring(etree.fromstring(str(xml), parser))

            DOMTree = minidom.parseString(doc)
            username = DOMTree.getElementsByTagName("username")
            username = username[0].childNodes[0].nodeValue
            password = DOMTree.getElementsByTagName("password")
            password = password[0].childNodes[0].nodeValue
            if username == USERNAME and password == PASSWORD:
                result = "<result><code>%d</code><msg>%s</msg></result>" % (1, username)
            else:
                admin = Admin.query.filter_by(username=username).first()
                if not admin and not check_password_hash(admin.password, password):
                    result = "<result><code>%d</code><msg>%s</msg></result>" % (
                        2,
                        username,
                    )

                admin_session = {
                    "trackingId": f"{generate_key()}",
                    "user": f"{username}",
                }

                admin_session = json.dumps(admin_session)
                resp = redirect(url_for("main.message"))
                resp.set_cookie("admin_session", base64_encode(admin_session))
                return resp

        except Exception as e:
            result = "<result><code>%d</code><msg>%s</msg></result>" % (3, username)

    return result, {"Content-Type": "text/xml;charset=UTF-8"}


@main.route("/admin/forgotPassword")
def forgotPassword():
    return render_template("forgotPassword.html")


@main.route("/admin/doForgotPassword", methods=["POST", "GET"])
def doForgotPassword():
    result = None
    parsed_xml = None
    if request.method == "POST":
        try:
            xml = request.data.decode("utf-8")
            parser = etree.XMLParser(no_network=False)
            doc = etree.tostring(etree.fromstring(str(xml), parser))

            DOMTree = minidom.parseString(doc)
            email = DOMTree.getElementsByTagName("email")
            email = email[0].childNodes[0].nodeValue

            if email:
                result = (
                    "<result><code>%d</code><msg>Você receberá um link para redefinir a palavra-passe caso esse email exista.</msg></result>"
                    % 1
                )
        except Exception as e:
            result = "<result><code>%d</code><msg>%s</msg></result>" % (3, e)

    return result, {"Content-Type": "text/xml;charset=UTF-8"}


@main.route("/admin/register")
def registerAdmin():
    return render_template("registerAdmin.html")


@main.route("/admin/doRegister", methods=["POST", "GET"])
def doRegisterAdmin():
    result = None
    parsed_xml = None
    if request.method == "POST":
        try:
            registrationKey = request.form.get("registration-key")
            email = request.form.get("email")
            username = request.form.get("username")
            password = request.form.get("password")

            if email and username and password:
                if registrationKey == "pOiEnZ1zpdaXhyKqWUNEoX6ENQj5duEE":
                    result = (
                        "<h3>Administrador registrado com sucesso pelo email %s.</h3>"
                        % email
                    )
                    new_admin = Admin(
                        email=email,
                        username=username,
                        password=generate_password_hash(password, method="sha256"),
                    )
                    db.session.add(new_admin)
                    db.session.commit()
                else:
                    result = "<h3>Chave de registro inválida.</h3>"

                return result, {"Content-Type": "text/html;charset=UTF-8"}
        except:
            pass

        try:
            xml = request.data.decode("utf-8")
            parser = etree.XMLParser(no_network=False)
            doc = etree.tostring(etree.fromstring(str(xml), parser))

            DOMTree = minidom.parseString(doc)
            registrationKey = DOMTree.getElementsByTagName("registration-key")
            registrationKey = registrationKey[0].childNodes[0].nodeValue
            email = DOMTree.getElementsByTagName("email")
            email = email[0].childNodes[0].nodeValue
            username = DOMTree.getElementsByTagName("username")
            username = username[0].childNodes[0].nodeValue
            password = DOMTree.getElementsByTagName("password")
            password = password[0].childNodes[0].nodeValue

            if email and username and password:
                if registrationKey == "pOiEnZ1zpdaXhyKqWUNEoX6ENQj5duEE":
                    result = (
                        "<result><code>%d</code><msg>Administrador registrado com sucesso pelo email %s </msg></result>"
                        % (1, email)
                    )
                    new_admin = Admin(
                        email=email,
                        username=username,
                        password=generate_password_hash(password, method="sha256"),
                    )
                    db.session.add(new_admin)
                    db.session.commit()
                else:
                    result = (
                        "<result><code>%d</code><msg>Chave de registro inválida</msg></result>"
                        % 3
                    )

                return result, {"Content-Type": "text/xml;charset=UTF-8"}
        except Exception as e:
            result = "<result><code>%d</code><msg>%s</msg></result>" % (1, e)
            return result, {"Content-Type": "text/xml;charset=UTF-8"}


@main.route("/admin/logout")
def adminLogout():
    resp = redirect(url_for("main.admin"))
    resp.set_cookie("admin_session", "")
    return resp, 302


@main.route("/admin/s3cr3t")
def secret():
    trusted_proxies = ("127.0.0.1", "localhost")
    remote = request.remote_addr

    if remote != "127.0.0.1":
        abort(403)  # Forbidden

    return "REGISTRATION KEY: pOiEnZ1zpdaXhyKqWUNEoX6ENQj5duEE"
