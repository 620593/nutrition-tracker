/*
 * This is the root App component that defines the top-level routing structure of the
 * Nutrition Tracker SPA. It uses React Router to map URL paths to their corresponding
 * page components such as Login, Dashboard, LogMeal, LogExercise, and Leaderboard.
 * When fully implemented, it will also enforce authentication guards on protected routes
 * so that unauthenticated users are always redirected back to the Login page.
 */

import React, { useEffect, useState } from "react";
import {
  Routes,
  Route,
  Navigate,
  Link,
  useNavigate,
  Outlet,
} from "react-router-dom";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import LogMeal from "./pages/LogMeal.jsx";
import LogExercise from "./pages/LogExercise.jsx";
import Leaderboard from "./pages/Leaderboard.jsx";
import supabase from "./supabaseClient";

const ProtectedRoute = () => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
      if (!session) {
        navigate("/login");
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (!session) {
        navigate("/login");
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-900 flex items-center justify-center text-green-500">
        Loading...
      </div>
    );
  }

  return session ? (
    <div className="min-h-screen bg-zinc-900 text-white font-sans">
      <nav className="bg-zinc-800 p-4 shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex space-x-6 items-center">
            <span className="text-xl font-bold text-green-500">
              NutritionTracker
            </span>
            <Link
              to="/dashboard"
              className="hover:text-green-400 transition-colors font-medium"
            >
              Dashboard
            </Link>
            <Link
              to="/log-meal"
              className="hover:text-green-400 transition-colors font-medium"
            >
              Log Meal
            </Link>
            <Link
              to="/log-exercise"
              className="hover:text-green-400 transition-colors font-medium"
            >
              Log Exercise
            </Link>
            <Link
              to="/leaderboard"
              className="hover:text-green-400 transition-colors font-medium"
            >
              Leaderboard
            </Link>
          </div>
          <div className="flex space-x-4 items-center">
            <span className="text-sm text-zinc-400">{session.user?.email}</span>
            <button
              onClick={() => {
                supabase.auth.signOut();
                navigate("/login");
              }}
              className="bg-green-500 text-zinc-900 px-4 py-2 rounded font-semibold hover:bg-green-400 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto p-4 md:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  ) : null;
};

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<Login />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/log-meal" element={<LogMeal />} />
        <Route path="/log-exercise" element={<LogExercise />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
      </Route>
    </Routes>
  );
}
