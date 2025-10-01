"""
Insta485 following view.

URLs include:
/users/<user>/following/
"""
import flask
import insta485


@insta485.app.route('/users/<user>/following/')
def show_following(user):
    """Display following page."""
    
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
    
    # Get following
    cur = connection.execute(
        "SELECT u.username, u.fullname, u.filename "
        "FROM users u "
        "JOIN following f ON u.username = f.followee "
        "WHERE f.follower = ? "
        "ORDER BY u.username",
        (user,)
    )
    following = cur.fetchall()
    
    # For each user being followed, check if logname is following them
    for user_followed in following:
        if user_followed['username'] != logname:
            cur = connection.execute(
                "SELECT * FROM following WHERE follower = ? AND followee = ?",
                (logname, user_followed['username'])
            )
            user_followed['is_following'] = cur.fetchone() is not None
        else:
            user_followed['is_following'] = None  # Blank for self
    
    # Add database info to context
    context = {
        "logname": logname,
        "user": user,
        "following": following
    }
    
    return flask.render_template("following.html", **context)
