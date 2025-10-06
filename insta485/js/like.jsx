import React, { useState } from "react";

export default function LikeButton({
  postid,
  initialLikes,
  initialLiked,
  likeid,
  onLikeChange,
}) {
  const numLikes = initialLikes;
  const isLiked = initialLiked;
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async () => {
    if (isLoading) return;

    setIsLoading(true);

    try {
      if (isLiked) {
        const response = await fetch(`/api/v1/likes/${likeid}/`, {
          method: "DELETE",
          credentials: "same-origin",
        });

        if (response.ok) {
          onLikeChange(numLikes - 1, false, null);
        } else {
          console.error("Failed to unlike post");
        }
      } else {
        const response = await fetch(`/api/v1/likes/?postid=${postid}`, {
          method: "POST",
          credentials: "same-origin",
        });

        if (response.ok) {
          const data = await response.json();
          onLikeChange(numLikes + 1, true, data.likeid);
        } else {
          console.error("Failed to like post");
        }
      }
    } catch (error) {
      console.error("Error updating like:", error);
    }

    setIsLoading(false);
  };

  return (
    <div className="like-section">
      <button
        data-testid="like-unlike-button"
        onClick={handleClick}
        disabled={isLoading}
        className={`like-button ${isLiked ? "liked" : ""}`}
      >
        {isLiked ? "unlike" : "like"}
      </button>
      <p>
        {numLikes} {numLikes === 1 ? "like" : "likes"}
      </p>
    </div>
  );
}
