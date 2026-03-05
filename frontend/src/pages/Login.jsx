/*
 * This page provides the Login and Registration UI for the Nutrition Tracker application.
 * It renders a form where users can enter their email and password to sign in or create
 * a new account using Supabase Authentication. When fully implemented, it will handle
 * form validation, display inline error messages, and redirect authenticated users to
 * the Dashboard immediately after a successful sign-in or registration.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import supabase from "../supabaseClient";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (signInError) {
      setError(signInError.message);
      setLoading(false);
    } else {
      navigate("/dashboard");
    }
  };

  return (
    <div className="min-h-screen bg-zinc-900 flex items-center justify-center p-4 text-white font-sans">
      <div className="bg-zinc-800 p-8 rounded-xl shadow-2xl w-full max-w-md border border-zinc-700">
        <h1 className="text-3xl font-bold text-center mb-2 text-green-500">
          AI Nutrition Tracker
        </h1>
        <p className="text-zinc-400 text-center mb-8">
          Sign in to your account
        </p>

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-500 text-zinc-900 font-bold rounded-lg px-4 py-3 hover:bg-green-400 transition-colors flex items-center justify-center disabled:opacity-70"
          >
            {loading ? (
              <svg
                className="animate-spin h-5 w-5 text-zinc-900"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {error && (
          <p className="mt-4 text-center text-red-500 text-sm bg-red-500/10 p-3 rounded">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
