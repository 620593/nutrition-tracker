/*
 * This file exports a pre-configured Axios HTTP client instance for communicating
 * with the Nutrition Tracker FastAPI backend. It sets the base URL from an environment
 * variable and attaches a request interceptor that automatically injects the user's
 * Supabase JWT access token into the Authorization header on every outgoing request.
 * When fully implemented, it will also handle 401 responses by triggering a token refresh.
 */

import axios from "axios";
import supabase from "../supabaseClient";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

apiClient.interceptors.request.use(
  async (config) => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default apiClient;
