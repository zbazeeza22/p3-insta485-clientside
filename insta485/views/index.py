"""
Insta485 index (main) view.

URLs include:
/
"""
import os
import hashlib
import pathlib
import hmac
import uuid
# from werkzeug.utils import secure_filename
import flask
import arrow
import insta485

# def require_csrf():
#     """Check csrf manually."""
#     form_token = request.form.get("csrf_token", "")
#     session_token = session.get("csrf_token", "")
#     if not form_token or not session_token:
#         abort(403)  # missing token
#     if not hmac.compare_digest(form_token, session_token):
#         abort(403)  # bad token


@insta485.app.route('/')
def show_index():
    """Display / route."""
    # Connect to database
    if "username" not in flask.session:
        # optional: preserve target so you come back after logging in
        return flask.redirect("/accounts/login/?target=/", code=302)
    connection = insta485.model.get_db()

    # Query database
    logname = flask.session.get("username")

    if not logname:

        flask.abort(403)
    posts_row = connection.execute(
        "SELECT postid, filename, owner, created "
        "FROM posts "
        "WHERE owner = ?"
        "OR owner in (SELECT followee FROM following WHERE follower = ?)"
        "ORDER BY created DESC, postid DESC",
        (logname, logname)
    ).fetchall()
    # posts_row = cur.fetchall()

    posts = []

    for row in posts_row:
        postid = row["postid"]
        owner = row["owner"]
        created = row["created"]
        owner_pic_row = connection.execute(
            "SELECT filename FROM users WHERE username = ?",
            (owner,)
        ).fetchone()
        # owner_img_url = owner_pic_row["filename"]

        # comments = []
        comments = connection.execute(
            "SELECT postid, owner, text "
            "FROM comments "
            "WHERE postid = ? "
            "ORDER BY created ASC",
            (postid,),
        ).fetchall()
        # comments = cur.fetchall()

        likes_count = connection.execute(
            "SELECT COUNT(*) FROM likes WHERE postid = ?",
            (postid,)
        ).fetchone()["COUNT(*)"]

        did_like = connection.execute(
            "SELECT 1 FROM likes WHERE postid = ? AND owner = ?",
            (postid, logname)
        ).fetchone() is not None

        ts = arrow.get(created)                # works for str or datetime
        if ts.tzinfo is None:                  # DB times are usually naive UTC
            ts = ts.replace(tzinfo="UTC")

        # local_now = arrow.now("America/Detroit")   # timezone-aware
        created_ago = ts.to("America/Detroit").humanize(
            other=arrow.now("America/Detroit")
        )

        posts.append({
            "owner": owner,
            "owner_img_url": f"/uploads/{owner_pic_row["filename"]}",
            "img_url": f"/uploads/{row["filename"]}",
            "postid": postid,
            "timestamp": created,
            "created_ago": created_ago,
            "liked_by_logname": did_like,
            "likes": likes_count,
            "comments": comments,
        })
    context = {
        "logname": logname,
        "posts": posts,
    }
    return flask.render_template("index.html", **context)
    # Add database info to context
    # context = {"users": users}
    # return flask.render_template("index.html", **context)


@insta485.app.route('/users/<username>/')
def show_user(username):
    """Display user route."""
    if "username" not in flask.session:
        # optional: preserve target so you come back after logging in
        return flask.redirect("/accounts/login/?target=/", code=302)
    logname = flask.session.get("username")
    connection = insta485.model.get_db()

    # check user exists
    user_row = connection.execute(
        "SELECT username, fullname FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if user_row is None:
        flask.abort(404)

    total_posts = connection.execute(
        "SELECT COUNT(*) FROM posts WHERE owner = ?",
        (username,),
    ).fetchone()["COUNT(*)"]

    followers = connection.execute(
        "SELECT COUNT(*) FROM following WHERE followee = ?",
        (username,),
    ).fetchone()["COUNT(*)"]

    following = connection.execute(
        "SELECT COUNT(*) FROM following WHERE follower = ?",
        (username,),
    ).fetchone()["COUNT(*)"]

    logname_follows_username = (
        connection.execute(
            "SELECT 1 FROM following WHERE follower = ? AND followee = ?",
            (logname, username),
        ).fetchone()
        is not None
    )

    rows = connection.execute(
        "SELECT postid, filename FROM posts "
        "WHERE owner = ? "
        "ORDER BY created DESC, postid DESC",
        (username,),
    ).fetchall()

    posts = []
    for r in rows:
        postid = r["postid"]
        img_url = f"/uploads/{r['filename']}"

        posts.append({
            "id": postid,
            "img_url": img_url
        })

    return flask.render_template(
        "user.html",
        logname=logname,
        username=username,
        fullname=user_row["fullname"],
        total_posts=total_posts,
        followers=followers,
        following=following,
        logname_follows_username=logname_follows_username,
        posts=posts,
        # current_page_url=current_page_url,
    )


@insta485.app.route('/users/<username>/followers/')
def show_followers(username):
    """Display follower route."""
    if "username" not in flask.session:
        # optional: preserve target so you come back after logging in
        return flask.redirect("/accounts/login/?target=/", code=302)
    connection = insta485.model.get_db()
    logname = flask.session.get("username")
    connection = insta485.model.get_db()

    # check user exists
    user_row = connection.execute(
        "SELECT username, fullname FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if user_row is None:
        flask.abort(404)

    row_followers = connection.execute(
        "SELECT follower FROM following WHERE followee = ?",
        (username,),
    ).fetchall()

    followers = []
    for r in row_followers:
        user = r["follower"]

        row_pic = connection.execute(
            "SELECT filename FROM users WHERE username = ?",
            (user,),
        ).fetchone()
        img = f"/uploads/{row_pic["filename"]}"

        logname_follows_username = (
            connection.execute(
                "SELECT 1 FROM following WHERE follower = ? AND followee = ?",
                (logname, user),
            ).fetchone()
            is not None
        )

        followers.append({
            "username": user,
            "user_img_url": img,
            "logname_follows_username": logname_follows_username
        })

    return flask.render_template(
        "follower.html",
        logname=logname,
        username=username,
        followers=followers,

        # current_page_url=current_page_url,
    )


@insta485.app.route('/users/<username>/following/')
def show_following(username):
    """Display following route."""
    if "username" not in flask.session:
        # optional: preserve target so you come back after logging in
        return flask.redirect("/accounts/login/?target=/", code=302)
    connection = insta485.model.get_db()
    logname = flask.session.get("username")
    connection = insta485.model.get_db()

    # check user exists
    user_row = connection.execute(
        "SELECT username, fullname FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if user_row is None:
        flask.abort(404)

    row_following = connection.execute(
        "SELECT followee FROM following WHERE follower = ?",
        (username,),
    ).fetchall()

    following = []
    for r in row_following:
        user = r["followee"]

        row_pic = connection.execute(
            "SELECT filename FROM users WHERE username = ?",
            (user,),
        ).fetchone()
        img = f"/uploads/{row_pic["filename"]}"

        logname_follows_username = (
            connection.execute(
                "SELECT 1 FROM following WHERE follower = ? AND followee = ?",
                (logname, user),
            ).fetchone()
            is not None
        )

        following.append({
            "username": user,
            "user_img_url": img,
            "logname_follows_username": logname_follows_username
        })

    return flask.render_template(
        "following.html",
        logname=logname,
        username=username,
        following=following,

        # current_page_url=current_page_url,
    )


@insta485.app.route('/posts/<int:postid>/')
def show_post(postid):
    """Display post route."""
    if "username" not in flask.session:
        target = f"/posts/{postid}/"
        return flask.redirect(f"/accounts/login/?target={target}", code=302)
    logname = flask.session.get("username")
    connection = insta485.model.get_db()

    row_owner = connection.execute(
        "SELECT owner, filename, created FROM posts WHERE postid = ?",
        (postid,),
    ).fetchone()
    if row_owner is None:
        flask.abort(404)

    owner = row_owner["owner"]
    row_filename = connection.execute(
        "SELECT filename FROM users WHERE username = ?",
        (owner,),
    ).fetchone()

    owner_img_url = f"/uploads/{row_filename['filename']}"
    img_url = f"/uploads/{row_owner['filename']}"

    row_comment = connection.execute(
        "SELECT commentid, owner, text FROM comments WHERE postid = ?",
        (postid,),
    ).fetchall()

    likes = connection.execute(
        "SELECT COUNT(*) FROM likes WHERE postid = ?",
        (postid,),
    ).fetchone()["COUNT(*)"]

    liked_by_logname = (
        connection.execute(
            "SELECT 1 FROM likes WHERE owner = ? AND postid = ?",
            (logname, postid),
        ).fetchone()
        is not None
    )

    comments = []
    for r in row_comment:

        comments.append({
            "owner": r["owner"],
            "text": r["text"],
            "commentid": r["commentid"]
        })

    return flask.render_template(
        "post.html",
        logname=logname,
        owner=owner,
        postid=postid,
        timestamp=row_owner["created"],
        likes=likes,
        liked_by_logname=liked_by_logname,
        owner_img_url=owner_img_url,
        img_url=img_url,
        comments=comments
        # current_page_url=current_page_url,
    )


LOGGER = flask.logging.create_logger(insta485.app)


@insta485.app.route("/likes/", methods=["POST"])
def update_likes():
    """Update like route."""
    LOGGER.debug("operation = %s", flask.request.form["operation"])
    LOGGER.debug("postid = %s", flask.request.form["postid"])
    # require_csrf()

    logname = flask.session.get("username")

    # logname = flask.session["username"] or "awdeorio"
    op = flask.request.form.get("operation")
    postid = flask.request.form.get("postid")
    target = flask.request.args.get("target", "/")

    if op not in {"like", "unlike"} or not postid:
        flask.abort(400)

    # DB work
    connection = insta485.model.get_db()

    # (Optional but nice) ensure post exists
    row = connection.execute(
        "SELECT 1 FROM posts WHERE postid = ?",
        (postid,),
    ).fetchone()
    if row is None:
        flask.abort(404)

    already = connection.execute(
        "SELECT 1 FROM likes WHERE owner = ? AND postid = ?",
        (logname, postid),
    ).fetchone() is not None

    if op == "like":
        if already:
            flask.abort(409)
        # Insert if absent (ignore duplicates)
        connection.execute(
            "INSERT INTO likes(owner, postid, created) "
            "VALUES (?, ?, CURRENT_TIMESTAMP)",
            (logname, postid),
        )
    else:  # "unlike"
        if not already:
            # Trying to unlike when you haven't liked → Conflict
            flask.abort(409)
        connection.execute(
            "DELETE FROM likes WHERE owner = ? AND postid = ?",
            (logname, postid),
        )

    # Redirect back to the page that issued the form
    # Use 303 to prevent the browser from re-POSTing on refresh
    return flask.redirect(target, code=302)


@insta485.app.route("/posts/", methods=["POST"])
def make_post():
    """Update post route."""
    # require_csrf()
    if "username" not in flask.session:
        flask.abort(403)
    logname = flask.session["username"]

    op = flask.request.form.get("operation")
    target = flask.request.args.get("target") or f"/users/{logname}/"
    if op not in {"create", "delete"}:
        flask.abort(400)

    connection = insta485.model.get_db()
    # Path object (per your config)
    upload_dir = insta485.app.config["UPLOAD_FOLDER"]
    # e.g., {"png","jpg","jpeg","gif"}

    if op == "create":
        try:
            fileobj = flask.request.files["file"]
        except KeyError:
            flask.abort(400)

        filename = fileobj.filename
        if not filename:
            flask.abort(400)

# Compute base name (filename without directory). We use a UUID to avoid
# clashes with existing files, and ensure that the name is compatible with the
# filesystem. For best practive, we ensure uniform file extensions (e.g.
# lowercase).
        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix.lower()
        uuid_basename = f"{stem}{suffix}"

        # Save to disk
        path = upload_dir/uuid_basename
        fileobj.save(path)

        # Insert DB row
        connection.execute(
            "INSERT INTO posts(owner, filename, created) "
            "VALUES (?, ?, CURRENT_TIMESTAMP)",
            (logname, uuid_basename),
        )
        return flask.redirect(target, code=302)

        # op == "delete"
    postid = flask.request.form.get("postid")
    if not postid:
        flask.abort(400)

    row = connection.execute(
        "SELECT owner, filename FROM posts WHERE postid = ?",
        (postid,),
    ).fetchone()
    if row is None:
        flask.abort(404)
    if row["owner"] != logname:
        flask.abort(403)

    # Remove image file (ignore if already gone)
    (upload_dir / row["filename"]).unlink(missing_ok=True)

    # Clean DB (comments, likes, then post)
    connection.execute("DELETE FROM comments WHERE postid = ?", (postid,))
    connection.execute("DELETE FROM likes    WHERE postid = ?", (postid,))
    connection.execute("DELETE FROM posts    WHERE postid = ?", (postid,))

    return flask.redirect(target, code=302)


@insta485.app.get("/accounts/login/")
def show_login():
    """Display login route."""
    # If already logged in, go to feed; otherwise show the login page
    if "username" in flask.session:
        return flask.redirect("/")
    return flask.render_template("login.html")


@insta485.app.get("/accounts/create/")
def show_create():
    """Display create route."""
    if "username" in flask.session:
        return flask.redirect("/accounts/edit/")
    return flask.render_template("create.html")


@insta485.app.get("/accounts/delete/")
def show_delete():
    """Display delete route."""
    if "username" not in flask.session:
        flask.abort(403)

    logname = flask.session["username"]
    return flask.render_template("delete.html", logname=logname)


@insta485.app.get("/accounts/edit/")
def show_edit():
    """Display edit route."""
    if "username" not in flask.session:
        flask.abort(403)
    connection = insta485.model.get_db()
    logname = flask.session["username"]
    row = connection.execute(
        "SELECT email, fullname, filename "
        "FROM users "
        "WHERE username = ?",
        (logname,),
    ).fetchone()

    fullname = row["fullname"]
    email = row["email"]
    filename = row["filename"]
    return flask.render_template(
        "edit.html",
        logname=logname,
        fullname=fullname,
        email=email,
        filename=filename,
    )


@insta485.app.get("/accounts/password/")
def show_password():
    """Display password route."""
    if "username" not in flask.session:
        flask.abort(403)

    logname = flask.session["username"]

    return flask.render_template("password.html", logname=logname)


@insta485.app.get("/accounts/auth/")
def accounts_auth():
    """Account auth."""
    if "username" in flask.session:
        return ("", 200)          # empty response body, status 200
    flask.abort(403)


@insta485.app.route("/accounts/logout/", methods=["POST"])
def accounts_logout():
    # require_csrf()
    """Display logout route."""
    # Clear session if present (idempotent)
    flask.session.clear()

    # Where to go next (default: login page)
    target = flask.request.args.get("target", "/accounts/login/")

    # Immediate redirect; 302 is fine for GET
    return flask.redirect(target, code=302)


@insta485.app.route("/comments/", methods=["POST"])
def update_comments():
    """Update comment route."""
    # require_csrf()
    if "username" not in flask.session:
        flask.abort(403)
    logname = flask.session.get("username")

    op = flask.request.form.get("operation")
    target = flask.request.args.get("target", "/")

    if op not in {"create", "delete"}:
        flask.abort(400)

    conn = insta485.model.get_db()

    if op == "create":
        postid = flask.request.form.get("postid")
        text = (flask.request.form.get("text") or "").strip()
        if not postid or not text:
            flask.abort(400)

        # ensure post exists
        if conn.execute(
            "SELECT 1 FROM posts WHERE postid = ?",
            (postid,)
        ).fetchone() is None:
            flask.abort(404)

        conn.execute(
            "INSERT INTO comments(owner, postid, text, created) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (logname, postid, text),
        )
        return flask.redirect(target, code=302)

    commentid = flask.request.form.get("commentid")
    if not commentid:
        flask.abort(400)

    row = conn.execute(
        "SELECT owner FROM comments WHERE commentid = ?",
        (commentid,),
    ).fetchone()
    if row is None:
        flask.abort(404)
    if row["owner"] != logname:
        flask.abort(403)

    conn.execute("DELETE FROM comments WHERE commentid = ?", (commentid,))
    return flask.redirect(target, code=302)


@insta485.app.route("/following/", methods=["POST"])
def update_following():
    """Update following route."""
    # require_csrf()
    # Use fallback during public/no-auth phase; switch to strict guard later.
    logname = flask.session.get("username")

    op = flask.request.form.get("operation")
    target = flask.request.args.get("target", "/")
    user = flask.request.form.get("username")

    if op not in {"follow", "unfollow"} or not user:
        flask.abort(400)

    conn = insta485.model.get_db()

    # Optional but helpful: ensure the target user exists
    row = conn.execute(
        "SELECT 1 FROM users WHERE username = ?",
        (user,)
    ).fetchone()
    if row is None:
        flask.abort(404)

    if op == "follow":

        conn.execute(
            "INSERT INTO following(follower, followee, created) "
            "VALUES (?, ?, CURRENT_TIMESTAMP)",
            (logname, user),
        )
    else:
        conn.execute(
            "DELETE FROM following WHERE follower = ? AND followee = ?",
            (logname, user),
        )

    return flask.redirect(target, code=302)


def verify_password(submitted_plain: str, stored: str) -> bool:
    """stored:sha512$<salt>$<hexdigest>."""
    try:
        algo, salt, digest = stored.split("$", 3)
    except ValueError:
        # no $, or malformed → treat as plaintext fallback (optional)
        return hmac.compare_digest(stored, submitted_plain)

    if algo != "sha512":
        return False

    salted = salt + submitted_plain
    check = hashlib.sha512((salted).encode("utf-8")).hexdigest()
    return hmac.compare_digest(check, digest)


def _db():
    """Get db table."""
    return insta485.model.get_db()


def _require_logged_in() -> str:
    """Check session."""
    if "username" not in flask.session:
        flask.abort(403)
    return flask.session["username"]


def _hash_pw(plain: str) -> str:
    """Hash helper route."""
    salt = uuid.uuid4().hex
    digest = hashlib.sha512((salt + plain).encode("utf-8")).hexdigest()
    return "$".join(["sha512", salt, digest])


def _save_upload_or_400(fileobj) -> str:
    """Save file path."""
    if fileobj is None or not fileobj.filename:
        flask.abort(400)
    upload_dir = flask.current_app.config["UPLOAD_FOLDER"]
    # allowed = flask.current_app.config["ALLOWED_EXTENSIONS"]
    suffix = pathlib.Path(fileobj.filename).suffix.lower()
    # ext = suffix.lstrip(".")
    # if ext not in allowed:
    #     flask.abort(400)
    stored = f"{uuid.uuid4().hex}{suffix}"
    # (upload_dir / stored).parent.mkdir(parents=True, exist_ok=True)
    fileobj.save(upload_dir / stored)
    return stored


def _op_login(target: str):
    """Login account route."""
    conn = _db()
    username = flask.request.form.get("username", "")
    password = flask.request.form.get("password", "")
    if not username or not password:
        flask.abort(400)
    row = conn.execute(
        "SELECT username, password FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None or not verify_password(password, row["password"]):
        flask.abort(403)
    flask.session["username"] = row["username"]
    return flask.redirect(target or "/", code=302)


def _op_create(target: str):
    """Create account route."""
    conn = _db()
    username = (flask.request.form.get("username") or "").strip()
    password = flask.request.form.get("password") or ""
    fullname = (flask.request.form.get("fullname") or "").strip()
    email = (flask.request.form.get("email") or "").strip()
    fileobj = flask.request.files.get("file")

    if not (username and password and fullname
            and email and fileobj and fileobj.filename):
        flask.abort(400)

    if conn.execute(
        "SELECT 1 FROM users WHERE username = ?",
        (username,),
    ).fetchone():
        flask.abort(409)

    avatar_basename = _save_upload_or_400(fileobj)
    pw_db = _hash_pw(password)

    conn.execute(
        "INSERT INTO users(username, password, fullname, email, filename) "
        "VALUES (?, ?, ?, ?, ?)",
        (username, pw_db, fullname, email, avatar_basename),
    )
    flask.session.clear()
    flask.session["username"] = username
    return flask.redirect(target or "/accounts/edit/", code=302)


def _op_delete(target: str):
    """Delete account route."""
    conn = _db()
    logname = _require_logged_in()
    upload_dir: pathlib.Path = flask.current_app.config["UPLOAD_FOLDER"]

    # remove all post images owned by this user
    rows = conn.execute(
        "SELECT filename FROM posts WHERE owner = ?",
        (logname,),
    ).fetchall()

    for row in rows:
        path = upload_dir / row["filename"]
        path.unlink(missing_ok=True)

    # remove avatar
    row_user = conn.execute(
        "SELECT filename FROM users WHERE username = ?",
        (logname,),
    ).fetchone()
    if row_user and row_user["filename"]:
        (upload_dir / row_user["filename"]).unlink(missing_ok=True)

    conn.execute("DELETE FROM users WHERE username = ?", (logname,))
    flask.session.clear()
    return flask.redirect(target or "/", code=302)


def _op_edit_account(target: str):
    """Edit account route."""
    conn = _db()
    logname = _require_logged_in()
    fullname = (flask.request.form.get("fullname") or "").strip()
    email = (flask.request.form.get("email") or "").strip()
    fileobj = flask.request.files.get("file")

    if not fullname or not email:
        flask.abort(400)

    row_user = conn.execute(
        "SELECT filename FROM users WHERE username = ?",
        (logname,),
    ).fetchone()
    if row_user is None:
        flask.abort(404)

    if not fileobj or not fileobj.filename:
        conn.execute(
            "UPDATE users SET fullname = ?, email = ? WHERE username = ?",
            (fullname, email, logname),
        )
        return flask.redirect(target, code=302)

    new_basename = _save_upload_or_400(fileobj)
    old = row_user["filename"]
    upload_dir: pathlib.Path = flask.current_app.config["UPLOAD_FOLDER"]
    if old:
        (upload_dir / old).unlink(missing_ok=True)

    conn.execute(
        "UPDATE users SET fullname = ?,"
        "email = ?, filename = ? WHERE username = ?",
        (fullname, email, new_basename, logname),
    )
    return flask.redirect(target, code=302)


def _op_update_password(target: str):
    """Update password route."""
    conn = _db()
    logname = _require_logged_in()
    current = flask.request.form.get("password") or ""
    new1 = flask.request.form.get("new_password1") or ""
    new2 = flask.request.form.get("new_password2") or ""

    if not (current and new1 and new2):
        flask.abort(400)

    row = conn.execute(
        "SELECT password FROM users WHERE username = ?",
        (logname,),
    ).fetchone()
    if row is None:
        flask.abort(404)
    if not verify_password(current, row["password"]):
        flask.abort(403)
    if new1 != new2:
        flask.abort(401)

    conn.execute(
        "UPDATE users SET password = ? WHERE username = ?",
        (_hash_pw(new1), logname),
    )
    return flask.redirect(target or "/accounts/edit/", code=302)


@insta485.app.post("/accounts/")
def accounts_post():
    """Update account route."""
    op = flask.request.form.get("operation")
    target = flask.request.args.get("target", "/")

    if op == "login":
        return _op_login(target)
    if op == "create":
        return _op_create(target)
    if op == "delete":
        return _op_delete(target)
    if op == "edit_account":
        return _op_edit_account(target)
    if op == "update_password":
        return _op_update_password(target)

    flask.abort(403)


@insta485.app.route("/explore/")
def explore():
    """Display /explore route."""
    # Connect to database
    connection = insta485.model.get_db()

    logname = flask.session.get("username")

    if not logname:

        flask.abort(403)

    cur = connection.execute(
        "SELECT username, fullname, filename "
        "FROM users "
        "WHERE username != ? "
        "  AND NOT EXISTS ("
        "    SELECT 1 "
        "    FROM following "
        "    WHERE following.follower = ? "
        "      AND following.followee = users.username"  # keep users. here
        "  ) "
        "ORDER BY username",
        (logname, logname),
    )
    rows = cur.fetchall()
    not_following = []
    for r in rows:
        filename = r["filename"]
        # Project skeleton typically serves uploads at /uploads/<filename>
        user_img_url = f"/uploads/{filename}" if filename else ""
        not_following.append({
            "username": r["username"],
            "user_img_url": user_img_url,
        })

    return flask.render_template(
        "explore.html",
        logname=logname,
        not_following=not_following,
    )


@insta485.app.get("/uploads/<path:filename>")
def uploads(filename):
    """Upload route."""
    # per spec: only logged-in users can fetch uploads
    if "username" not in flask.session:
        flask.abort(403)

    upload_dir = os.path.normpath(
        os.path.join(insta485.app.root_path, "..", "var", "uploads")
    )
    path = os.path.normpath(os.path.join(upload_dir, filename))
    # Optional safety: ensure the path stays within upload_dir
    if not path.startswith(upload_dir + os.sep):
        flask.abort(404)

    if not os.path.isfile(path):
        flask.abort(404)
    return flask.send_from_directory(upload_dir, filename)
