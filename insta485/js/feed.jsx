// This fetches posts and shows them (like your HTML loop)
import React, { useState, useEffect } from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import Post from "./post";

export default function Feed() {
  const [posts, setPosts] = useState([]);
  const [nextUrl, setNextUrl] = useState("");
  const [hasMore, setHasMore] = useState(true);

  // Load initial posts
  useEffect(() => {
    loadPosts("/api/v1/posts/");
  }, []);

  // Load posts function
  const loadPosts = async (url) => {
    try {
      const response = await fetch(url, { credentials: "same-origin" });
      if (!response.ok) throw Error(response.statusText);

      const data = await response.json();

      if (url === "/api/v1/posts/") {
        // Initial load
        setPosts(data.results);
      } else {
        // Load more posts
        setPosts((prevPosts) => [...prevPosts, ...data.results]);
      }

      setNextUrl(data.next);
      setHasMore(data.next !== "");
    } catch (error) {
      console.log("Error loading posts:", error);
      setHasMore(false);
    }
  };

  // Load more posts for infinite scroll
  const loadMorePosts = () => {
    if (nextUrl) {
      loadPosts(nextUrl);
    }
  };

  return (
    <div className="feed-container">
      <InfiniteScroll
        dataLength={posts.length}
        next={loadMorePosts}
        hasMore={hasMore}
        loader={<div className="loading">Loading more posts...</div>}
        endMessage={<div className="end-message">No more posts to load</div>}
      >
        {posts.map((post) => (
          <Post key={post.postid} url={post.url} />
        ))}
      </InfiniteScroll>
    </div>
  );
}
