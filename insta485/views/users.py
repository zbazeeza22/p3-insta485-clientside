"""
Insta485 user profile view.

URLs include:
/users/<user>/
"""
import flask
import insta485


@insta485.app.route('/users/<user>/')
def show_user(user):
    """Display user profile page."""
    
    # Hardcode logged in user as awdeorio for now
    logname = "awdeorio"
    
    # Connect to database
    connection = insta485.model.get_db()
    
    # Check if user exists
    cur = connection.execute(
        "SELECT username FROM users WHERE username = ?",
        (user,)
    )
    if cur.fetchone() is None:
        flask.abort(404)
    
    # Get user info
    cur = connection.execute(
        "SELECT username, fullname, filename FROM users WHERE username = ?",
        (user,)
    )
    user_info = cur.fetchone()
    
    # Get post count
    cur = connection.execute(
        "SELECT COUNT(*) as post_count FROM posts WHERE owner = ?",
        (user,)
    )
    post_count = cur.fetchone()['post_count']
    
    # Get follower count
    cur = connection.execute(
        "SELECT COUNT(*) as follower_count FROM following WHERE followee = ?",
        (user,)
    )
    follower_count = cur.fetchone()['follower_count']
    
    # Get following count
    cur = connection.execute(
        "SELECT COUNT(*) as following_count FROM following WHERE follower = ?",
        (user,)
    )
    following_count = cur.fetchone()['following_count']
    
    # Check if logname is following user
    is_following = False
    if logname != user:
        cur = connection.execute(
            "SELECT * FROM following WHERE follower = ? AND followee = ?",
            (logname, user)
        )
        is_following = cur.fetchone() is not None
    
    # Get user's posts
    cur = connection.execute(
        "SELECT postid, filename FROM posts WHERE owner = ? ORDER BY postid DESC",
        (user,)
    )
    posts = cur.fetchall()
    
    # Add database info to context
    context = {
        "logname": logname,
        "user": user_info,
        "post_count": post_count,
        "follower_count": follower_count,
        "following_count": following_count,
        "is_following": is_following,
        "posts": posts
    }
    
    return flask.render_template("user.html", **context)
