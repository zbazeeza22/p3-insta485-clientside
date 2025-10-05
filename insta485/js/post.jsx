import React, { useState, useEffect } from "react";
import LikeButton from "./like";

export default function Post({ url }) {
  // Use ONE state for the entire post object
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ignoreStaleRequest = false;

    fetch(url, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        if (!ignoreStaleRequest) {
          console.log("Like status:", data.likes.lognameLikesThis);
          setPost(data); // Store the ENTIRE post object
          setLoading(false);
        }
      })
      .catch((error) => {
        console.log(error);
        setLoading(false);
      });

    return () => {
      ignoreStaleRequest = true;
    };
  }, [url]);

  const handleLikeChange = (newNumLikes, newIsLiked, newLikeid) => {
    setPost((prevPost) => ({
      ...prevPost,
      likes: {
        ...prevPost.likes,
        numLikes: newNumLikes,
        lognameLikesThis: newIsLiked,
        url: newLikeid ? `/api/v1/likes/${newLikeid}/` : null,
      },
    }));
  };

  const handleImageDoubleClick = async () => {
    console.log("Double-click! Currently liked?", post.likes.lognameLikesThis); // ADD THIS LINE
    if (!post.likes.lognameLikesThis) {
      try {
        const response = await fetch(`/api/v1/likes/?postid=${post.postid}`, {
          method: "POST",
          credentials: "same-origin",
        });

        if (response.ok) {
          const data = await response.json();
          const newNumLikes = post.likes.numLikes + 1;
          handleLikeChange(newNumLikes, true, data.likeid);
        }
      } catch (error) {
        console.error("Error liking post:", error);
      }
    }
  };

  // Don't render until we have post data
  if (loading) return <div>Loading...</div>;
  if (!post) return <div>Error loading post</div>;

  // Extract likeid from the likes URL
  const likeid = post.likes.url
    ? post.likes.url
        .split("/")
        .filter((part) => part)
        .pop()
    : null;

  return (
    <div className="post">
      <p style={{ color: "red" }}>
        DEBUG: Liked = {String(post.likes.lognameLikesThis)}
      </p>{" "}
      {/* ADD THIS LINE */}
      <img
        src={post.imgUrl}
        alt="post_image"
        onDoubleClick={handleImageDoubleClick}
        style={{ cursor: "pointer" }} // Optional: show it's clickable
      />
      <p>{post.owner}</p>
      <LikeButton
        postid={post.postid}
        initialLikes={post.likes.numLikes}
        initialLiked={post.likes.lognameLikesThis}
        likeid={likeid}
        onLikeChange={handleLikeChange}
      />
    </div>
  );
}
