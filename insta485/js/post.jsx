import React, { useState, useEffect } from "react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

export default function Post({ url }) {
  /* Display complete post with likes, comments, and interactive features */

  const [postData, setPostData] = useState(null);
  const [now, setNow] = useState(dayjs());

  // Update timestamp every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(dayjs());
    }, 60000); // Update every 60 seconds

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let ignoreStaleRequest = false;

    fetch(url, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        if (!ignoreStaleRequest) {
          setPostData(data);
        }
      })
      .catch((error) => {
        console.log(error);
      });

    return () => {
      ignoreStaleRequest = true;
    };
  }, [url]);

  // Handle like/unlike functionality
  const handleLike = async () => {
    if (!postData) return;

    try {
      if (postData.likes.lognameLikesThis) {
        // Unlike: DELETE the like
        const response = await fetch(postData.likes.url, {
          method: "DELETE",
          credentials: "same-origin",
        });

        if (response.ok) {
          // Update local state
          setPostData((prev) => ({
            ...prev,
            likes: {
              lognameLikesThis: false,
              numLikes: prev.likes.numLikes - 1,
              url: null,
            },
          }));
        }
      } else {
        // Like: POST a new like
        const response = await fetch(
          `/api/v1/likes/?postid=${postData.postid}`,
          {
            method: "POST",
            credentials: "same-origin",
          },
        );

        if (response.ok) {
          const likeData = await response.json();
          // Update local state
          setPostData((prev) => ({
            ...prev,
            likes: {
              lognameLikesThis: true,
              numLikes: prev.likes.numLikes + 1,
              url: likeData.url,
            },
          }));
        }
      }
    } catch (error) {
      console.log("Error handling like:", error);
    }
  };

  // Handle double-click to like
  const handleDoubleClick = () => {
    if (!postData || postData.likes.lognameLikesThis) return;
    handleLike();
  };

  // Handle comment submission
  const handleCommentSubmit = async (event) => {
    event.preventDefault();
    if (!postData) return;

    const textInput = event.target.querySelector('input[name="text"]');
    const text = textInput ? textInput.value.trim() : "";

    if (!text) return;

    console.log("Submitting comment:", text, "for post:", postData.postid);

    try {
      const response = await fetch(
        `/api/v1/comments/?postid=${postData.postid}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "same-origin",
          body: JSON.stringify({ text }),
        },
      );

      if (response.ok) {
        const newComment = await response.json();
        // Update local state
        setPostData((prev) => ({
          ...prev,
          comments: [...prev.comments, newComment],
        }));
        // Clear the form
        event.target.reset();
      }
    } catch (error) {
      console.log("Error adding comment:", error);
    }
  };

  // Handle comment deletion
  const handleDeleteComment = async (commentid) => {
    if (!postData) return;

    try {
      const response = await fetch(`/api/v1/comments/${commentid}/`, {
        method: "DELETE",
        credentials: "same-origin",
      });

      if (response.ok) {
        // Update local state
        setPostData((prev) => ({
          ...prev,
          comments: prev.comments.filter(
            (comment) => comment.commentid !== commentid,
          ),
        }));
      }
    } catch (error) {
      console.log("Error deleting comment:", error);
    }
  };

  // Format timestamp
  const formatTimestamp = (created) => {
    return dayjs.utc(created).local().from(now);
  };

  // Show loading state
  if (!postData) {
    return (
      <div className="post">
        <p>Loading...</p>
      </div>
    );
  }

  // Render complete post
  return (
    <div className="post">
      {/* Post header */}
      <div className="post-header">
        <img src={postData.ownerImgUrl} alt="profile" className="profile-pic" />
        <a href={postData.ownerShowUrl}>{postData.owner}</a>
      </div>

      {/* Post image with double-click to like */}
      <img
        src={postData.imgUrl}
        alt="post_image"
        onDoubleClick={handleDoubleClick}
      />
      {/* Likes section */}
      <div className="likes-section">
        <button data-testid="like-unlike-button" onClick={handleLike}>
          {postData.likes.lognameLikesThis ? "Unlike" : "Like"}
        </button>
        <span>
          {postData.likes.numLikes === 1
            ? "1 like"
            : `${postData.likes.numLikes} likes`}
        </span>
      </div>

      {/* Comments section */}
      <div className="comments-section">
        {postData.comments.map((comment) => (
          <div key={comment.commentid} className="comment">
            <span data-testid="comment-text">
              <a href={comment.ownerShowUrl}>{comment.owner}</a> {comment.text}
            </span>
            {comment.lognameOwnsThis && (
              <button
                data-testid="delete-comment-button"
                onClick={() => handleDeleteComment(comment.commentid)}
              >
                Delete
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Comment form */}
      <form data-testid="comment-form" onSubmit={handleCommentSubmit}>
        <input
          type="text"
          name="text"
          placeholder="Add a comment..."
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              const form = e.target.closest("form");
              handleCommentSubmit({ target: form, preventDefault: () => {} });
            }
          }}
        />
      </form>

      {/* Timestamp */}
      <div className="timestamp" data-testid="post-time-ago">
        <a href={postData.postShowUrl}>{formatTimestamp(postData.created)}</a>
      </div>
    </div>
  );
}
