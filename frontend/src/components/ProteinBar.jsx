/*
 * This component renders a horizontal progress bar that visually represents the user's
 * current protein intake relative to their daily protein goal in grams.
 * It accepts current and target protein values as props and displays a color-coded fill
 * that changes from red (below 50%) to yellow (50–80%) to green (above 80%).
 * When fully implemented, it will animate the bar fill smoothly on data updates.
 */

import React, { useState, useEffect } from "react";

export default function ProteinBar({ data }) {
  const [width, setWidth] = useState(0);

  const consumed = data?.daily_log?.total_protein || 0;
  const goal = data?.daily_goals?.protein_goal || 0;
  const unit = "g";

  useEffect(() => {
    // Provide a small delay to trigger the CSS transition on mount
    const timeout = setTimeout(() => {
      const targetPercent = goal > 0 ? (consumed / goal) * 100 : 0;
      setWidth(Math.min(100, Math.max(0, targetPercent)));
    }, 100);
    return () => clearTimeout(timeout);
  }, [consumed, goal]);

  const noGoalSet = goal === 0;
  const exceedsGoal = !noGoalSet && consumed >= goal;
  const remaining = Math.max(0, goal - consumed);
  const barColor = exceedsGoal ? "bg-yellow-500" : "bg-green-500";

  return (
    <div className="w-full">
      <div className="flex justify-between items-end mb-2">
        <span className="text-white font-medium">Protein</span>
        <span className="text-white font-bold">
          {consumed}
          {unit}{" "}
          <span className="text-zinc-500 font-normal">
            / {goal}
            {unit}
          </span>
        </span>
      </div>

      <div className="w-full h-3 bg-zinc-900 rounded-full overflow-hidden relative border border-zinc-700">
        <div
          className={`h-full ${barColor} transition-all duration-1000 ease-out`}
          style={{ width: `${width}%` }}
        />
      </div>

      <div className="mt-2 text-right">
        {noGoalSet ? (
          <span className="text-zinc-500 text-sm font-medium">
            No goal set yet
          </span>
        ) : exceedsGoal ? (
          <span className="text-green-500 text-sm font-medium">
            Goal reached!
          </span>
        ) : (
          <span className="text-zinc-400 text-sm font-medium">
            {remaining}
            {unit} remaining
          </span>
        )}
      </div>
    </div>
  );
}
