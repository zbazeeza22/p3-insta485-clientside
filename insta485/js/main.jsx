import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Post from "./post";

// Create a root
const root = createRoot(document.getElementById("reactEntry"));

// Insert the post component into the DOM.  Only call root.render() once.
root.render(
  <StrictMode>
    <Post url="/api/v1/posts/1/" />
  </StrictMode>
);