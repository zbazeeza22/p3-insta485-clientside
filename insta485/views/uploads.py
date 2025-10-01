"""
Insta485 uploads view.

URLs include:
/uploads/<filename>
"""
import flask
import insta485


@insta485.app.route('/uploads/<filename>')
def show_uploads(filename):
    """Serve uploaded files."""
    return flask.send_from_directory(
        insta485.app.config["UPLOAD_FOLDER"], filename
    )
