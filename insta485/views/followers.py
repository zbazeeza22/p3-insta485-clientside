"""
Insta485 followers view.

URLs include:
/users/<user>/followers/
"""
import flask
import insta485


@insta485.app.route('/users/<user>/followers/')
def show_followers(user):
    """Display followers page."""
    
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
    
    # Get followers
    cur = connection.execute(
        "SELECT u.username, u.fullname, u.filename "
        "FROM users u "
        "JOIN following f ON u.username = f.follower "
        "WHERE f.followee = ? "
        "ORDER BY u.username",
        (user,)
    )
    followers = cur.fetchall()
    
    # For each follower, check if logname is following them
    for follower in followers:
        if follower['username'] != logname:
            cur = connection.execute(
                "SELECT * FROM following WHERE follower = ? AND followee = ?",
                (logname, follower['username'])
            )
            follower['is_following'] = cur.fetchone() is not None
        else:
            follower['is_following'] = None  # Blank for self
    
    # Add database info to context
    context = {
        "logname": logname,
        "user": user,
        "followers": followers
    }
    
    return flask.render_template("followers.html", **context)
