/*
 * This page lets users log physical activity and exercise sessions to offset caloric intake.
 * Users can select an activity type, enter duration, and optionally add notes about intensity.
 * When fully implemented, it will use MET (Metabolic Equivalent of Task) values to estimate
 * calories burned and post the exercise record to the backend so the Dashboard can factor
 * it into the user's net calorie balance for the day.
 */

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client.js";
import supabase from "../supabaseClient";

export default function LogExercise() {
  const [exerciseType, setExerciseType] = useState("Running");
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const EXERCISE_OPTIONS = ["Running", "Walking", "Cycling", "Gym", "Yoga"];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();
      if (userError || !user) throw new Error("Could not authenticate user");

      const response = await apiClient.post("/log-exercise", {
        user_id: user.id,
        exercise_type: exerciseType,
        duration_minutes: Number(durationMinutes),
      });

      setResult(response.data);
    } catch (err) {
      console.error("[LogExercise] handleSubmit error:", err);
      setError(
        err.response?.data?.detail || err.message || "An error occurred",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold text-white mb-6">Log Exercise</h1>

      <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Exercise Type
            </label>
            <select
              value={exerciseType}
              onChange={(e) => setExerciseType(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-colors"
            >
              {EXERCISE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Duration (minutes)
            </label>
            <input
              type="number"
              min="1"
              max="300"
              required
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-500 text-zinc-900 font-bold rounded-lg px-4 py-3 hover:bg-green-400 transition-colors flex items-center justify-center disabled:opacity-70"
          >
            {loading ? "Submitting..." : "Log Exercise"}
          </button>
        </form>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500 p-4 rounded-xl text-red-500">
          {error}
        </div>
      )}

      {result && (
        <div className="bg-zinc-800 p-6 rounded-xl border border-green-500">
          <h2 className="text-xl font-bold text-green-500 mb-4">
            Exercise Logged!
          </h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-zinc-900 p-4 rounded-lg">
              <p className="text-sm text-zinc-400 uppercase tracking-wider">
                Type
              </p>
              <p className="text-xl font-bold text-white">
                {result.exercise_type || exerciseType}
              </p>
            </div>
            <div className="bg-zinc-900 p-4 rounded-lg">
              <p className="text-sm text-zinc-400 uppercase tracking-wider">
                Duration
              </p>
              <p className="text-xl font-bold text-white">
                {result.duration || durationMinutes} min
              </p>
            </div>
            <div className="bg-zinc-900 p-4 rounded-lg">
              <p className="text-sm text-zinc-400 uppercase tracking-wider">
                Burned
              </p>
              <p className="text-xl font-bold text-green-500">
                {result.calories_burned} kcal
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
