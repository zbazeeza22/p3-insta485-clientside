"""
Insta485 REST API.

URLs include:
/api/v1/
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


def check_authentication():
    """Check if user is authenticated via session or HTTP Basic Auth."""
    # Check session first
    if "username" in flask.session:
        return flask.session["username"]

    # Check HTTP Basic Auth
    if flask.request.authorization:
        username = flask.request.authorization.username
        password = flask.request.authorization.password

        # Import verify_password from index.py
        from insta485.views.index import verify_password

        connection = insta485.model.get_db()
        user = connection.execute(
            "SELECT password FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and verify_password(password, user["password"]):
            return username

    # No valid authentication found
    flask.abort(403)


@insta485.app.route("/api/v1/")
def get_services():
    """Return a list of services available."""
    context = {
        "comments": "/api/v1/comments/",
        "likes": "/api/v1/likes/",
        "posts": "/api/v1/posts/",
        "url": "/api/v1/",
    }
    return flask.jsonify(**context)


@insta485.app.route("/api/v1/posts/")
def get_posts():
    """Return the 10 most recent posts from followed users."""
    logname = check_authentication()

    page = flask.request.args.get("page", 0, type=int)
    size = flask.request.args.get("size", 10, type=int)
    postid_lte = flask.request.args.get("postid_lte", type=int)

    if size <= 0 or page < 0:
        flask.abort(400)

    connection = insta485.model.get_db()

    query = """
        SELECT postid, filename, owner, created 
        FROM posts 
        WHERE (owner = ? OR owner IN (SELECT followee FROM following WHERE follower = ?))
    """
    params = [logname, logname]

    # Add postid_lte filter if provided
    if postid_lte is not None:
        query += " AND postid <= ?"
        params.append(postid_lte)

    query += " ORDER BY postid DESC LIMIT ? OFFSET ?"
    params.extend([size + 1, page * size])

    posts_row = connection.execute(query, params).fetchall()

    print(f"DEBUG: len(posts_row)={len(posts_row)}, size={size}, len > size? {len(posts_row) > size}")
    if len(posts_row) - size >= 0:
        posts_row = posts_row[:size]

        next_postid_lte = postid_lte
        if postid_lte is None and posts_row:
            next_postid_lte = posts_row[0]["postid"]

        next_params = []
        next_params.append(f"size={size}")
        next_params.append(f"page={page + 1}")
        if next_postid_lte is not None:
            next_params.append(f"postid_lte={next_postid_lte}")

        print(f"DEBUG next_params: {next_params}")  # Add this line
        next_url = f"/api/v1/posts/?{'&'.join(next_params)}"
    else:
        next_url = ""

    posts = []
    for post in posts_row:
        posts.append(
            {"postid": post["postid"], "url": f"/api/v1/posts/{post['postid']}/"}
        )

    current_params = []
    t = False
    if size != 10:
        current_params.append(f"size={size}")
        t = True
    if page != 0:
        if not t: current_params.append(f"size={size}")
        current_params.append(f"page={page}")
    if postid_lte is not None:
        current_params.append(f"postid_lte={postid_lte}")

    current_url = "/api/v1/posts/"
    if current_params:
        current_url += "?" + "&".join(current_params)

    context = {"next": next_url, "results": posts, "url": current_url}
    return flask.jsonify(**context)


@insta485.app.route("/api/v1/likes/", methods=["POST"])
def create_like():
    "Create a like for a post."
    logname = check_authentication()
    
    postid = flask.request.args.get("postid", type=int)
    if postid is None:
        flask.abort(400)
    
    connection = insta485.model.get_db()
    post = connection.execute("SELECT postid FROM posts WHERE postid = ?", (postid,)).fetchone()
    if post is None:
        flask.abort(404)

    user_like = connection.execute(
        "SELECT likeid FROM likes WHERE postid = ? AND owner = ?", (postid, logname)).fetchone()
    if user_like is not None:
        return flask.jsonify({
            "likeid": user_like["likeid"], 
            "url": f"/api/v1/likes/{user_like['likeid']}/"}), 200
    
    connection.execute(
        "INSERT INTO likes (postid, owner) VALUES (?, ?)", (postid, logname))

    likeid = (connection.execute("SELECT last_insert_rowid()").fetchone())[0]
    print(debug:=f"DEBUG: New like created with likeid={likeid}")
    return flask.jsonify({
        "likeid": likeid,
        "url": f"/api/v1/likes/{likeid}/"
    }), 201


@insta485.app.route("/api/v1/likes/<int:likeid>/", methods=["DELETE"])
def delete_like(likeid):
    """Delete a like."""
    logname = check_authentication()
    
    connection = insta485.model.get_db()
    
    like = connection.execute(
        "SELECT owner FROM likes WHERE likeid = ?", (likeid,)
    ).fetchone()
    
    if like is None:
        flask.abort(404)
    
    if like["owner"] != logname:
        flask.abort(403)
    
    connection.execute("DELETE FROM likes WHERE likeid = ?", (likeid,))
    
    return "", 204