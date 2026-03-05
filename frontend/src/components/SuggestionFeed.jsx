/*
 * This component displays a scrollable feed of AI-generated dietary suggestions
 * returned by the backend's recommender node in the LangGraph pipeline.
 * Each suggestion card shows an icon, a short headline, and a brief explanation
 * of the recommended action (e.g., "Add 30g of protein to hit your goal").
 * When fully implemented, it will poll the backend periodically and animate new
 * suggestions sliding in from the bottom of the feed.
 */

import React from "react";

export default function SuggestionFeed(props) {
  // Support both explicit props or extraction from a single nested data object
  const isLoading = props.loading;

  // Extract recommendation safely from either direct props or a nested data object
  const recommendation =
    props.recommendation ??
    props.data?.ai_recommendation ??
    props.data?.recommendation ??
    "";

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="animate-pulse flex space-x-4 bg-zinc-900 p-4 rounded-xl border border-zinc-800"
          >
            <div className="rounded-full bg-zinc-800 h-10 w-10"></div>
            <div className="flex-1 space-y-3 py-1">
              <div className="h-2 bg-zinc-800 rounded w-1/4"></div>
              <div className="h-2 bg-zinc-800 rounded w-3/4"></div>
              <div className="h-2 bg-zinc-800 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!recommendation || recommendation.trim() === "") {
    return (
      <div className="bg-zinc-900 border border-zinc-700/50 rounded-xl p-8 text-center flex flex-col items-center justify-center">
        <span className="text-4xl mb-3">✨</span>
        <p className="text-zinc-400 font-medium">
          Log a meal to get AI suggestions
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-zinc-900 border border-zinc-700 border-l-4 border-l-green-500 rounded-xl p-5 shadow-sm transition-all hover:bg-zinc-800/80">
        <div className="flex items-start gap-4">
          <div className="text-3xl mt-1">🤖</div>
          <div className="flex-1">
            <h3 className="text-green-500 font-semibold mb-2">
              AI Nutritionist
            </h3>
            <p className="text-zinc-100 text-sm leading-relaxed whitespace-pre-wrap">
              {recommendation}
            </p>
            <div className="mt-4 flex items-center gap-2">
              <span className="text-xs text-zinc-500 font-medium tracking-wide uppercase">
                Updated just now
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
