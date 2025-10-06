"""
Insta485 REST API.

URLs include:
/api/v1/

"""

import sqlite3
import flask
import insta485
from insta485.views.index import verify_password


def check_authentication():
    """Check if user is authenticated via session or HTTP Basic Auth."""
    # Check session first
    if "username" in flask.session:
        return flask.session["username"]

    # Check HTTP Basic Auth
    if flask.request.authorization:
        username = flask.request.authorization.username
        password = flask.request.authorization.password

        connection = insta485.model.get_db()
        user = connection.execute(
            "SELECT password FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and verify_password(password, user["password"]):
            return username
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


def _build_pagination_urls(page, size, postid_lte, posts_row):
    """Build next and current URLs for pagination."""
    # Build next URL
    if len(posts_row) >= size:
        next_postid_lte = (postid_lte if postid_lte is not None
                           else posts_row[0]["postid"])
        next_params = [f"size={size}", f"page={page + 1}"]
        if next_postid_lte is not None:
            next_params.append(f"postid_lte={next_postid_lte}")
        next_url = f"/api/v1/posts/?{'&'.join(next_params)}"
    else:
        next_url = ""

    # Build current URL
    current_params = []
    if size != 10:
        current_params.append(f"size={size}")
    if page != 0:
        if size == 10:
            current_params.append(f"size={size}")
        current_params.append(f"page={page}")
    if postid_lte is not None:
        current_params.append(f"postid_lte={postid_lte}")

    current_url = "/api/v1/posts/"
    if current_params:
        current_url += "?" + "&".join(current_params)

    return next_url, current_url


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
        WHERE (owner = ? OR owner IN
        (SELECT followee FROM following WHERE follower = ?))
    """
    params = [logname, logname]

    if postid_lte is not None:
        query += " AND postid <= ?"
        params.append(postid_lte)

    query += " ORDER BY postid DESC LIMIT ? OFFSET ?"
    params.extend([size + 1, page * size])

    posts_row = connection.execute(query, params).fetchall()

    if len(posts_row) > size:
        posts_row = posts_row[:size]

    # Use helper function to build URLs
    next_url, current_url = _build_pagination_urls(page, size,
                                                   postid_lte, posts_row)

    posts = [{"postid": post["postid"],
              "url": f"/api/v1/posts/{post['postid']}/"}
             for post in posts_row]

    return flask.jsonify({"next": next_url,
                          "results": posts,
                          "url": current_url})


@insta485.app.route("/api/v1/likes/", methods=["POST"])
def create_like():
    """Create a like for a post."""
    logname = check_authentication()

    postid = flask.request.args.get("postid", type=int)
    if postid is None:
        flask.abort(400)

    connection = insta485.model.get_db()
    post = connection.execute("SELECT postid FROM posts WHERE postid = ?",
                              (postid,)).fetchone()
    if post is None:
        flask.abort(404)

    user_like = connection.execute(
        "SELECT likeid FROM likes WHERE postid = ? AND owner = ?",
        (postid, logname)).fetchone()

    if user_like is not None:
        return flask.jsonify({
            "likeid": user_like["likeid"],
            "url": f"/api/v1/likes/{user_like['likeid']}/"}), 200

    try:
        cur = connection.execute(
            "INSERT INTO likes (postid, owner) VALUES (?, ?)",
            (postid, logname))
        connection.commit()
    except sqlite3.IntegrityError:
        flask.abort(500)

    likeid = cur.lastrowid

    return flask.jsonify({
        "likeid": likeid,
        "url": f"/api/v1/likes/{likeid}/"
    }), 201


@insta485.app.route('/api/v1/posts/<int:postid>/')
def api_posts_detail(postid):
    """Return details for a specific post."""
    logname = check_authentication()
    connection = insta485.model.get_db()

    # Get post details
    cur = connection.execute(
        "SELECT owner, created, filename FROM posts WHERE postid = ?",
        (postid,)
    )
    post = cur.fetchone()

    if not post:
        flask.abort(404)

    # Get owner details
    cur = connection.execute(
        "SELECT filename FROM users WHERE username = ?",
        (post['owner'],)
    )
    owner_info = cur.fetchone()

    # Get comments
    cur = connection.execute(
        "SELECT commentid, owner, text FROM comments WHERE postid = ? "
        "ORDER BY commentid",
        (postid,)
    )
    comments = cur.fetchall()

    # Build comments list
    comments_list = []
    for comment in comments:
        comments_list.append({
            "commentid": comment['commentid'],
            "lognameOwnsThis": comment['owner'] == logname,
            "owner": comment['owner'],
            "ownerShowUrl": f"/users/{comment['owner']}/",
            "text": comment['text'],
            "url": f"/api/v1/comments/{comment['commentid']}/"
        })

    # Get likes info
    cur = connection.execute(
        "SELECT COUNT(*) as num_likes FROM likes WHERE postid = ?",
        (postid,)
    )
    num_likes = cur.fetchone()['num_likes']

    # Check if logname likes this post
    cur = connection.execute(
        "SELECT likeid FROM likes WHERE postid = ? AND owner = ?",
        (postid, logname)
    )
    like_info = cur.fetchone()

    likes_data = {
        "lognameLikesThis": like_info is not None,
        "numLikes": num_likes,
        "url": f"/api/v1/likes/{like_info['likeid']}/" if like_info else None
    }

    return flask.jsonify({
        "comments": comments_list,
        "comments_url": f"/api/v1/comments/?postid={postid}",
        "created": post['created'],
        "imgUrl": f"/uploads/{post['filename']}",
        "likes": likes_data,
        "owner": post['owner'],
        "ownerImgUrl": f"/uploads/{owner_info['filename']}",
        "ownerShowUrl": f"/users/{post['owner']}/",
        "postShowUrl": f"/posts/{postid}/",
        "postid": postid,
        "url": f"/api/v1/posts/{postid}/"
    })


@insta485.app.route('/api/v1/comments/', methods=['POST'])
def api_comments_post():
    """Create a comment for a post."""
    logname = check_authentication()
    connection = insta485.model.get_db()

    postid = flask.request.args.get('postid', type=int)
    if not postid:
        flask.abort(400)

    # Get comment text from JSON body
    if not flask.request.is_json:
        flask.abort(400)

    data = flask.request.get_json()
    text = data.get('text', '').strip()

    if not text:
        flask.abort(400)

    # Check if post exists
    cur = connection.execute(
        "SELECT 1 FROM posts WHERE postid = ?",
        (postid,)
    )
    if not cur.fetchone():
        flask.abort(404)

    # Create new comment
    cur = connection.execute(
        "INSERT INTO comments (owner, postid, text) VALUES (?, ?, ?)",
        (logname, postid, text)
    )
    commentid = cur.lastrowid
    connection.commit()

    return flask.jsonify({
        "commentid": commentid,
        "lognameOwnsThis": True,
        "owner": logname,
        "ownerShowUrl": f"/users/{logname}/",
        "text": text,
        "url": f"/api/v1/comments/{commentid}/"
    }), 201


@insta485.app.route('/api/v1/comments/<int:commentid>/', methods=['DELETE'])
def api_comments_delete(commentid):
    """Remove a comment."""
    logname = check_authentication()
    connection = insta485.model.get_db()

    # Check if comment exists
    cur = connection.execute(
        "SELECT owner FROM comments WHERE commentid = ?",
        (commentid,)
    )
    comment = cur.fetchone()
    if not comment:
        flask.abort(404)

    # Check if comment belongs to logname
    if comment['owner'] != logname:
        flask.abort(403)

    # Delete the comment
    connection.execute(
        "DELETE FROM comments WHERE commentid = ?",
        (commentid,)
    )
    connection.commit()

    return '', 204


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
