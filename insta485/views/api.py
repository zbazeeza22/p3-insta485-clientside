"""
Insta485 REST API views.

URLs include:
/api/v1/
/api/v1/posts/
/api/v1/posts/<postid>/
/api/v1/likes/
/api/v1/comments/
"""
import base64
import hashlib
import hmac
import flask
import insta485


def _check_auth():
    """Check authentication using session or HTTP Basic Auth."""
    # Check session first
    if "username" in flask.session:
        return flask.session.get("username")

    # Check HTTP Basic Auth
    auth_header = flask.request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        try:
            # Decode base64 credentials
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = credentials.split(':', 1)

            # Verify credentials
            connection = insta485.model.get_db()
            cur = connection.execute(
                "SELECT password FROM users WHERE username = ?",
                (username,)
            )
            row = cur.fetchone()

            if row and _verify_password(password, row["password"]):
                return username
        except (ValueError, UnicodeDecodeError):
            pass

    return None


def _verify_password(submitted_plain: str, stored: str) -> bool:
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


def _require_auth():
    """Require authentication, return 403 if not authenticated."""
    username = _check_auth()
    if not username:
        flask.abort(403)
    return username


@insta485.app.route('/api/v1/')
def api_resources():
    """List all available API resources."""
    return flask.jsonify({
        "comments": "/api/v1/comments/",
        "likes": "/api/v1/likes/",
        "posts": "/api/v1/posts/",
        "url": "/api/v1/"
    })


@insta485.app.route('/api/v1/posts/')
def api_posts_list():
    """Return a list of posts with pagination."""
    logname = _require_auth()
    connection = insta485.model.get_db()

    # Get query parameters
    size = flask.request.args.get('size', 10, type=int)
    page = flask.request.args.get('page', 0, type=int)
    postid_lte = flask.request.args.get('postid_lte', type=int)

    # Validate parameters
    if size <= 0:
        flask.abort(400)
    if page < 0:
        flask.abort(400)

    # Build SQL query
    where_conditions = [
        "owner = ? OR owner IN (SELECT followee FROM following "
        "WHERE follower = ?)"
    ]
    params = [logname, logname]

    if postid_lte is not None:
        where_conditions.append("postid <= ?")
        params.append(postid_lte)

    where_clause = " AND ".join(where_conditions)

    # Get posts
    cur = connection.execute(
        f"SELECT postid FROM posts WHERE {where_clause} "
        "ORDER BY created DESC, postid DESC "
        "LIMIT ? OFFSET ?",
        params + [size, page * size]
    )
    posts = cur.fetchall()

    # Check if there are more results
    cur = connection.execute(
        f"SELECT COUNT(*) as count FROM posts WHERE {where_clause}",
        params
    )
    total_count = cur.fetchone()['count']
    has_next = (page + 1) * size < total_count

    # Build next URL
    next_url = ""
    if has_next:
        next_params = f"size={size}&page={page + 1}"
        if postid_lte is not None:
            next_params += f"&postid_lte={postid_lte}"
        next_url = f"/api/v1/posts/?{next_params}"

    # Build results
    results = []
    for post in posts:
        results.append({
            "postid": post['postid'],
            "url": f"/api/v1/posts/{post['postid']}/"
        })

    return flask.jsonify({
        "next": next_url,
        "results": results,
        "url": "/api/v1/posts/"
    })


@insta485.app.route('/api/v1/posts/<int:postid>/')
def api_posts_detail(postid):
    """Return details for a specific post."""
    logname = _require_auth()
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


@insta485.app.route('/api/v1/likes/', methods=['POST'])
def api_likes_post():
    """Create a like for a post."""
    logname = _require_auth()
    connection = insta485.model.get_db()

    postid = flask.request.args.get('postid', type=int)
    if not postid:
        flask.abort(400)

    # Check if post exists
    cur = connection.execute(
        "SELECT 1 FROM posts WHERE postid = ?",
        (postid,)
    )
    if not cur.fetchone():
        flask.abort(404)

    # Check if already liked
    cur = connection.execute(
        "SELECT likeid FROM likes WHERE postid = ? AND owner = ?",
        (postid, logname)
    )
    existing_like = cur.fetchone()

    if existing_like:
        return flask.jsonify({
            "likeid": existing_like['likeid'],
            "url": f"/api/v1/likes/{existing_like['likeid']}/"
        }), 200

    # Create new like
    cur = connection.execute(
        "INSERT INTO likes (owner, postid) VALUES (?, ?)",
        (logname, postid)
    )
    likeid = cur.lastrowid
    connection.commit()

    return flask.jsonify({
        "likeid": likeid,
        "url": f"/api/v1/likes/{likeid}/"
    }), 201


@insta485.app.route('/api/v1/likes/<int:likeid>/', methods=['DELETE'])
def api_likes_delete(likeid):
    """Remove a like."""
    logname = _require_auth()
    connection = insta485.model.get_db()

    # Check if like exists
    cur = connection.execute(
        "SELECT owner FROM likes WHERE likeid = ?",
        (likeid,)
    )
    like = cur.fetchone()
    if not like:
        flask.abort(404)
    
    # Check if like belongs to logname
    if like['owner'] != logname:
        flask.abort(403)

    # Delete the like
    connection.execute(
        "DELETE FROM likes WHERE likeid = ?",
        (likeid,)
    )
    connection.commit()

    return '', 204


@insta485.app.route('/api/v1/comments/', methods=['POST'])
def api_comments_post():
    """Create a comment for a post."""
    logname = _require_auth()
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
    logname = _require_auth()
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
