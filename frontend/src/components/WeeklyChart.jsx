/*
 * This component renders a bar or line chart showing the user's nutritional trends
 * across the past seven days using the Recharts library.
 * It accepts an array of daily log objects as a prop and plots calorie and macro
 * data for each day with a responsive container and a clean dark-themed legend.
 * When fully implemented, it will support toggling between calorie, protein, carb,
 * and fat views via interactive legend clicks.
 */

import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

export default function WeeklyChart({ data }) {
  // If data is passed as the full API response object, extract the weekly array, otherwise use data directly if it's an array.
  const chartData = Array.isArray(data) ? data : data?.weekly_data || [];

  if (!chartData || chartData.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-zinc-400">
        <svg
          className="w-12 h-12 mb-3 text-zinc-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          ></path>
        </svg>
        <p>No data yet for this week</p>
      </div>
    );
  }

  // Custom styling for the tooltip to match the dark theme
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-zinc-800 border border-zinc-700 p-3 rounded-lg shadow-lg">
          <p className="text-white font-bold mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p
              key={index}
              style={{ color: entry.color }}
              className="text-sm font-medium"
            >
              {entry.name}: {entry.value}{" "}
              {entry.name.toLowerCase().includes("protein") ? "g" : "kcal"}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#a1a1aa", fontSize: 12 }}
            dy={10}
          />
          {/* Left Y-Axis for Calories */}
          <YAxis
            yAxisId="left"
            orientation="left"
            stroke="#a1a1aa"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#a1a1aa", fontSize: 12 }}
            domain={[0, 2000]}
          />
          {/* Right Y-Axis for Protein */}
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#a1a1aa"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#a1a1aa", fontSize: 12 }}
            domain={[0, 100]}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "rgba(255, 255, 255, 0.05)" }}
          />
          <Legend
            verticalAlign="top"
            height={36}
            iconType="circle"
            wrapperStyle={{ fontSize: "12px", color: "#a1a1aa" }}
          />
          <Bar
            yAxisId="left"
            dataKey="calories"
            name="Calories"
            fill="#22c55e"
            radius={[4, 4, 0, 0]}
            barSize={20}
          />
          <Bar
            yAxisId="right"
            dataKey="protein"
            name="Protein"
            fill="#60a5fa"
            radius={[4, 4, 0, 0]}
            barSize={20}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
