/*
 * This page is the main hub that users see after logging in and serves as the home screen.
 * It displays a summary of the user's daily nutritional progress including a calorie ring,
 * a protein progress bar, and an AI-generated suggestion feed tailored to their goals.
 * When fully implemented, it will fetch today's meal and exercise logs from the backend
 * and render the WeeklyChart component to visualize trends across the past seven days.
 */

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import CalorieRing from "../components/CalorieRing.jsx";
import ProteinBar from "../components/ProteinBar.jsx";
import WeeklyChart from "../components/WeeklyChart.jsx";
import SuggestionFeed from "../components/SuggestionFeed.jsx";
import apiClient from "../api/client.js";
import supabase from "../supabaseClient";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const {
        data: { user: supabaseUser },
        error: userError,
      } = await supabase.auth.getUser();

      if (userError || !supabaseUser) {
        throw new Error("Failed to get current user.");
      }

      setUser(supabaseUser);

      const response = await apiClient.get("/daily-summary", {
        params: { user_id: supabaseUser.id },
      });

      setData(response.data);
    } catch (err) {
      setError(err.message || "Failed to fetch dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getGreeting = () => {
    const hour = new Date().getHours();
    return hour < 12 ? "Good morning" : "Good evening";
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-zinc-800 rounded w-1/3"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-zinc-800 h-32 rounded-xl"></div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-zinc-800 h-64 rounded-xl"></div>
          <div className="bg-zinc-800 h-64 rounded-xl"></div>
        </div>
        <div className="bg-zinc-800 h-64 rounded-xl"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-800 border border-red-500/50 rounded-xl p-8 text-center">
        <p className="text-red-400 mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="bg-green-500 text-zinc-900 px-6 py-2 rounded-lg font-medium hover:bg-green-400 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const calConsumed = data?.calories_consumed || 0;
  const protConsumed = data?.protein_consumed || 0;
  const calBurned = data?.calories_burned || 0;
  const calGoal = data?.calorie_goal || 2000;
  const calRemaining = Math.max(0, calGoal - calConsumed);

  return (
    <div className="space-y-6">
      {/* Section 1: Greeting */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {getGreeting()},{" "}
            <span className="text-green-500">{user?.email}</span>
          </h1>
          <p className="text-zinc-400">
            Here's your nutritional summary for today.
          </p>
        </div>
        <button
          onClick={fetchData}
          className="bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            ></path>
          </svg>
          Refresh
        </button>
      </div>

      {/* Section 2: Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700 flex flex-col items-center justify-center text-center">
          <span className="text-3xl mb-2">🍽️</span>
          <p className="text-zinc-400 text-sm uppercase tracking-wider font-semibold">
            Calories Consumed
          </p>
          <p className="text-3xl font-bold text-white mt-1">{calConsumed}</p>
        </div>

        <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700 flex flex-col items-center justify-center text-center">
          <span className="text-3xl mb-2">🥩</span>
          <p className="text-zinc-400 text-sm uppercase tracking-wider font-semibold">
            Protein Consumed
          </p>
          <p className="text-3xl font-bold text-white mt-1">{protConsumed}g</p>
        </div>

        <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700 flex flex-col items-center justify-center text-center">
          <span className="text-3xl mb-2">🔥</span>
          <p className="text-zinc-400 text-sm uppercase tracking-wider font-semibold">
            Calories Burned
          </p>
          <p className="text-3xl font-bold text-white mt-1">{calBurned}</p>
        </div>

        <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700 flex flex-col items-center justify-center text-center">
          <span className="text-3xl mb-2">🎯</span>
          <p className="text-zinc-400 text-sm uppercase tracking-wider font-semibold">
            Calories Remaining
          </p>
          <p className="text-3xl font-bold text-green-500 mt-1">
            {calRemaining}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 3: CalorieRing */}
        <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700">
          <h2 className="text-lg font-semibold text-white mb-4">
            Daily Calorie Goal
          </h2>
          <CalorieRing data={data} />
        </div>

        {/* Section 4: ProteinBar */}
        <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700">
          <h2 className="text-lg font-semibold text-white mb-4">
            Protein Progress
          </h2>
          <ProteinBar data={data} />
        </div>
      </div>

      {/* Section 5: WeeklyChart */}
      <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700">
        <h2 className="text-lg font-semibold text-white mb-4">Weekly Trends</h2>
        <WeeklyChart data={data} />
      </div>

      {/* Section 6: SuggestionFeed */}
      <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700">
        <h2 className="text-lg font-semibold text-white mb-4">
          AI Suggestions
        </h2>
        <SuggestionFeed data={data} />
      </div>
    </div>
  );
}
