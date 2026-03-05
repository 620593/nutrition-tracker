/*
 * This page displays a ranked leaderboard showing how all users compare on key metrics
 * such as goal adherence rate, total protein logged, and streak consistency. It fetches
 * aggregated statistics from the backend and renders them in a sorted, paginated table
 * with each user's avatar, rank badge, and score. When fully implemented, it will update
 * in real time using Supabase Realtime subscriptions so the board refreshes automatically.
 */

import React, { useEffect, useState } from "react";
import apiClient from "../api/client.js";
import supabase from "../supabaseClient";

export default function Leaderboard() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentUserEmail, setCurrentUserEmail] = useState("");
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchLeaderboard = async () => {
    try {
      setLoading(true);
      setError(null);
      const {
        data: { user },
      } = await supabase.auth.getUser();
      setCurrentUserEmail(user?.email || "");

      const response = await apiClient.get("/leaderboard");
      setData(response.data || []);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || "Failed to fetch leaderboard.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const getShortEmail = (email) => {
    if (!email) return "unknown";
    return email.split("@")[0];
  };

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">
            Roommate Leaderboard
          </h1>
          <p className="text-zinc-400 text-sm">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={fetchLeaderboard}
          className="bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
          disabled={loading}
        >
          <svg
            className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
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

      {error ? (
        <div className="bg-zinc-800 border border-red-500/50 rounded-xl p-8 text-center">
          <p className="text-red-400">{error}</p>
        </div>
      ) : (
        <div className="bg-zinc-800 rounded-xl border border-zinc-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-zinc-900/50 border-b border-zinc-700 text-zinc-400 text-sm uppercase tracking-wider">
                  <th className="p-4 font-semibold">Rank</th>
                  <th className="p-4 font-semibold">User</th>
                  <th className="p-4 font-semibold text-center">Calories</th>
                  <th className="p-4 font-semibold text-center">Protein</th>
                  <th className="p-4 font-semibold text-center">Burned</th>
                  <th className="p-4 font-semibold w-1/3">
                    Daily Goal (2000 kcal)
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-700/50">
                {loading && data.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="p-8 text-center text-zinc-400">
                      Loading leaderboard...
                    </td>
                  </tr>
                ) : data.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="p-8 text-center text-zinc-400">
                      No data available yet.
                    </td>
                  </tr>
                ) : (
                  data.map((row, index) => {
                    const rank = index + 1;
                    const isCurrentUser = row.email === currentUserEmail;
                    const calConsumed = row.calories_consumed || 0;
                    const progressPercent = Math.min(
                      100,
                      Math.max(0, (calConsumed / 2000) * 100),
                    );

                    return (
                      <tr
                        key={row.email || index}
                        className={`hover:bg-zinc-700/30 transition-colors ${
                          isCurrentUser
                            ? "bg-zinc-700/20 border-l-4 border-l-green-500"
                            : ""
                        }`}
                      >
                        <td className="p-4 font-bold text-lg">
                          {rank === 1 ? <span className="mr-2">🏆</span> : null}
                          {rank}
                        </td>
                        <td
                          className={`p-4 font-medium ${isCurrentUser ? "text-green-500" : "text-white"}`}
                        >
                          {getShortEmail(row.email)}
                        </td>
                        <td className="p-4 text-center font-semibold">
                          {calConsumed}
                        </td>
                        <td className="p-4 text-center">
                          {row.protein_consumed || 0}g
                        </td>
                        <td className="p-4 text-center text-zinc-400">
                          {row.calories_burned || 0} kcal
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-full bg-zinc-900 rounded-full h-2.5 overflow-hidden">
                              <div
                                className={`h-2.5 rounded-full ${progressPercent > 100 ? "bg-red-500" : "bg-green-500"}`}
                                style={{ width: `${progressPercent}%` }}
                              ></div>
                            </div>
                            <span className="text-xs text-zinc-400 w-12 text-right">
                              {Math.round(progressPercent)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
