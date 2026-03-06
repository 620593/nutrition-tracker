/*
 * This component renders an SVG-based circular ring chart that shows the user's
 * calorie intake as a percentage of their daily calorie goal.
 * It accepts consumed and target calorie values as props and draws an animated arc
 * that fills clockwise, with a centered label displaying the remaining calories.
 * When fully implemented, it will use smooth CSS transitions to animate every update.
 */

import React, { useState, useEffect } from "react";

export default function CalorieRing({ data }) {
  const [offset, setOffset] = useState(0);

  const consumed = data?.daily_log?.total_calories || 0;
  const goal = data?.daily_goals?.calorie_goal || 0;

  const radius = 60;
  const strokeWidth = 12;
  const normalizedRadius = radius - strokeWidth * 2;
  const circumference = normalizedRadius * 2 * Math.PI;

  useEffect(() => {
    const timeout = setTimeout(() => {
      const percentage = goal > 0 ? (consumed / goal) * 100 : 0;
      const progress = Math.min(100, Math.max(0, percentage));
      const dashOffset = circumference - (progress / 100) * circumference;
      setOffset(dashOffset);
    }, 100);
    return () => clearTimeout(timeout);
  }, [consumed, goal, circumference]);

  // Initial offset is full circumference before animation
  const initialOffset = circumference;
  const currentOffset = offset === 0 ? initialOffset : offset;

  const exceedsGoal = goal > 0 && consumed > goal;
  const strokeColor = exceedsGoal ? "text-yellow-500" : "text-green-500";
  const noGoalSet = goal === 0;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center w-48 h-48">
        <svg
          height={radius * 2}
          width={radius * 2}
          className="transform -rotate-90"
        >
          {/* Background track */}
          <circle
            stroke="currentColor"
            className="text-zinc-700"
            fill="transparent"
            strokeWidth={strokeWidth}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
          {/* Progress arc */}
          <circle
            stroke="currentColor"
            className={`${strokeColor} transition-all duration-1000 ease-out`}
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference + " " + circumference}
            style={{ strokeDashoffset: currentOffset }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
        </svg>

        {/* Center content */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span
            className={`text-3xl font-bold ${exceedsGoal ? "text-yellow-500" : "text-white"}`}
          >
            {consumed}
          </span>
          <span className="text-zinc-400 text-sm font-medium uppercase tracking-widest mt-1">
            calories
          </span>
        </div>
      </div>
      <div className="mt-4 text-center">
        <p className="text-zinc-400 text-sm font-medium">
          {noGoalSet ? "No goal set yet" : `Goal ${goal} calories`}
        </p>
      </div>
    </div>
  );
}
