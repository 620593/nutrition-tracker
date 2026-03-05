/*
 * This is the React application entry point for the Nutrition Tracker frontend.
 * It mounts the root <App /> component into the HTML DOM element with id="root"
 * and wraps it with any global providers such as React Router's BrowserRouter,
 * an authentication context provider, and a Supabase session manager.
 * When fully implemented, it will also import and apply the global Tailwind CSS stylesheet.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";
