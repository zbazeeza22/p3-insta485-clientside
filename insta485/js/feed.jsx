import React, { useState, useEffect } from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import Post from "./post";

export default function Feed() {
  const [posts, setPosts] = useState([]);
  const [nextUrl, setNextUrl] = useState("");
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    fetch("/api/v1/posts/", { credentials: "same-origin" })
      .then((response) => response.json())
      .then((data) => {
        setPosts(data.results);
        setNextUrl(data.next); // ← Use the backend's "next" URL
        setHasMore(data.next !== "");
      });
  }, []);

  const fetchMorePosts = () => {
    if (!nextUrl) return;

    fetch(nextUrl, { credentials: "same-origin" }) // ← Call backend's next URL
      .then((response) => response.json())
      .then((data) => {
        setPosts((prevPosts) => [...prevPosts, ...data.results]);
        setNextUrl(data.next); // ← Get next "next" URL
        setHasMore(data.next !== "");
      });
  };

  return (
    <InfiniteScroll
      dataLength={posts.length}
      next={fetchMorePosts}
      hasMore={hasMore}
      loader={<h4>Loading...</h4>}
    >
      <div className="feed-container">
        {posts.map((post) => (
          <Post key={post.postid} url={post.url} />
        ))}
      </div>
    </InfiniteScroll>
  );
}
