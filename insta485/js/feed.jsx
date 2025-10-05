// This fetches posts and shows them (like your HTML loop)
import React, { useState, useEffect } from "react";
import Post from "./post";

export default function Feed() {
  const [posts, setPosts] = useState([]);
  
  useEffect(() => {
    // Get posts from your API
    fetch("/api/v1/posts/")
      .then(response => response.json())
      .then(data => setPosts(data.results));
  }, []);

  return (
    <div className="feed-container">
      {posts.map(post => (
        <Post key={post.postid} url={post.url} />
      ))}
    </div>
  );
}