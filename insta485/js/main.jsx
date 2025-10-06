import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Feed from "./feed";

// Create a root
const root = createRoot(document.getElementById("reactEntry"));

// Insert the post component into the DOM.  Only call root.render() once.
root.render(
  <StrictMode>
    <Feed />
  </StrictMode>,
);
