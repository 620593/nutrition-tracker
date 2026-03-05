/*
 * This page allows users to log a meal by typing a description, speaking it aloud,
 * or uploading a photo of their food. It sends the input to the LangGraph backend
 * agent, which parses the food items and retrieves their nutritional information.
 * When fully implemented, it will display a real-time breakdown of detected foods
 * with their macros before the user confirms the log to save it to the database.
 */

import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client.js";
import supabase from "../supabaseClient";

export default function LogMeal() {
  const [activeTab, setActiveTab] = useState("Text");

  // Text Tab State
  const [textInput, setTextInput] = useState("");

  // Photo Tab State
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState("");

  // Voice Tab State
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);

  // General State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Refs
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const fileInputRef = useRef(null);

  // Tab Switching
  const tabs = ["Text", "Photo", "Voice"];

  // Voice Handlers
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setAudioBlob(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingDuration(0);

      timerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      setError("Microphone access denied or not available. " + err.message);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream
        .getTracks()
        .forEach((track) => track.stop());
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const formatDuration = (seconds) => {
    const m = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  // Photo Handlers
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith("image/")) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith("image/")) {
        setImageFile(file);
        const reader = new FileReader();
        reader.onloadend = () => {
          setImagePreview(reader.result);
        };
        reader.readAsDataURL(file);
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  // Submit Handler
  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const {
        data: { user },
        error: userError,
      } = await supabase.auth.getUser();
      if (userError || !user) throw new Error("Could not authenticate user");

      const formData = new FormData();
      formData.append("user_id", user.id);

      if (activeTab === "Text") {
        if (!textInput.trim())
          throw new Error("Please enter a meal description.");
        formData.append("raw_input", textInput);
      } else if (activeTab === "Photo") {
        if (!imageFile) throw new Error("Please select an image.");
        formData.append("image", imageFile);
      } else if (activeTab === "Voice") {
        if (!audioBlob)
          throw new Error("Please record your meal description first.");
        formData.append("audio", audioBlob, "recording.webm");
      }

      const response = await apiClient.post("/log-meal", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setResult(response.data);
      // Reset inputs after success
      if (activeTab === "Text") setTextInput("");
      if (activeTab === "Photo") {
        setImageFile(null);
        setImagePreview("");
      }
      if (activeTab === "Voice") {
        setAudioBlob(null);
        setRecordingDuration(0);
      }
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || "An error occurred",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold text-white mb-6">Log Meal</h1>

      {/* Tabs */}
      <div className="flex bg-zinc-800 rounded-lg p-1 border border-zinc-700">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab);
              setError(null);
              setResult(null);
            }}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab
                ? "bg-zinc-700 text-green-500 shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="bg-zinc-800 p-6 rounded-xl border border-zinc-700">
        {activeTab === "Text" && (
          <div className="space-y-4">
            <label className="block text-sm font-medium text-zinc-300">
              What did you eat?
            </label>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="e.g. 2 eggs, a slice of toast, and black coffee"
              className="w-full h-32 bg-zinc-900 border border-zinc-700 rounded-lg p-4 text-white focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 resize-none transition-colors"
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !textInput.trim()}
              className="w-full bg-green-500 text-zinc-900 font-bold rounded-lg px-4 py-3 hover:bg-green-400 transition-colors disabled:opacity-70"
            >
              {loading ? "Analyzing..." : "Submit Meal"}
            </button>
          </div>
        )}

        {activeTab === "Photo" && (
          <div className="space-y-4">
            <label className="block text-sm font-medium text-zinc-300">
              Upload Food Photo
            </label>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className="border-2 border-dashed border-zinc-600 rounded-xl p-8 text-center bg-zinc-900 hover:border-green-500 transition-colors"
            >
              {imagePreview ? (
                <div className="space-y-4">
                  <img
                    src={imagePreview}
                    alt="Food preview"
                    className="max-h-64 mx-auto rounded-lg"
                  />
                  <button
                    onClick={() => {
                      setImageFile(null);
                      setImagePreview("");
                    }}
                    className="text-sm text-red-400 hover:text-red-300"
                  >
                    Remove Image
                  </button>
                </div>
              ) : (
                <div
                  className="space-y-2 cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <span className="text-4xl">📸</span>
                  <p className="text-zinc-400">
                    Drag & drop an image here, or click to select
                  </p>
                </div>
              )}
              <input
                type="file"
                accept="image/*"
                className="hidden"
                ref={fileInputRef}
                onChange={handleFileChange}
              />
            </div>
            <button
              onClick={handleSubmit}
              disabled={loading || !imageFile}
              className="w-full bg-green-500 text-zinc-900 font-bold rounded-lg px-4 py-3 hover:bg-green-400 transition-colors disabled:opacity-70"
            >
              {loading ? "Analyzing Image..." : "Submit Photo"}
            </button>
          </div>
        )}

        {activeTab === "Voice" && (
          <div className="space-y-8 flex flex-col items-center py-8">
            <div className="text-center space-y-2">
              <h3 className="text-lg font-medium text-white">
                Describe your meal
              </h3>
              <p className="text-sm text-zinc-400">
                Click the microphone to start recording
              </p>
            </div>

            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`w-32 h-32 rounded-full flex items-center justify-center transition-all ${
                isRecording
                  ? "bg-red-500/20 border-4 border-red-500 animate-pulse"
                  : "bg-zinc-700 hover:bg-zinc-600"
              }`}
            >
              <span className="text-5xl">{isRecording ? "⏹️" : "🎙️"}</span>
            </button>

            {isRecording ? (
              <div className="text-red-500 font-mono text-xl">
                {formatDuration(recordingDuration)}
              </div>
            ) : audioBlob ? (
              <div className="text-green-500 font-medium">
                Recording saved ({formatDuration(recordingDuration)})
              </div>
            ) : null}

            <button
              onClick={handleSubmit}
              disabled={loading || !audioBlob || isRecording}
              className="w-full max-w-sm mt-8 bg-green-500 text-zinc-900 font-bold rounded-lg px-4 py-3 hover:bg-green-400 transition-colors disabled:opacity-70"
            >
              {loading ? "Processing Audio..." : "Submit Recording"}
            </button>
          </div>
        )}
      </div>

      {/* States */}
      {error && (
        <div className="bg-red-500/10 border border-red-500 p-4 rounded-xl text-red-500">
          {error}
        </div>
      )}

      {result && (
        <div className="bg-zinc-800 p-6 rounded-xl border border-green-500 space-y-6">
          <div className="text-center border-b border-zinc-700 pb-4">
            <h2 className="text-2xl font-bold text-green-500">
              Meal Logged Successfully!
            </h2>
            {result.ai_recommendation_text && (
              <p className="text-zinc-300 mt-2 italic">
                "{result.ai_recommendation_text}"
              </p>
            )}
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white mb-3">
              Detected Items
            </h3>
            <ul className="list-disc list-inside text-zinc-300 space-y-1">
              {(result.detected_food_items || []).map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
              {(!result.detected_food_items ||
                result.detected_food_items.length === 0) && (
                <li className="text-zinc-500">No specific items listed</li>
              )}
            </ul>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div className="bg-zinc-900 p-3 rounded-lg">
              <p className="text-xs text-zinc-400 uppercase tracking-wide">
                Calories
              </p>
              <p className="font-bold text-white text-lg">
                {result.calories || 0}
              </p>
            </div>
            <div className="bg-zinc-900 p-3 rounded-lg">
              <p className="text-xs text-zinc-400 uppercase tracking-wide">
                Protein
              </p>
              <p className="font-bold text-white text-lg">
                {result.protein || 0}g
              </p>
            </div>
            <div className="bg-zinc-900 p-3 rounded-lg">
              <p className="text-xs text-zinc-400 uppercase tracking-wide">
                Carbs
              </p>
              <p className="font-bold text-white text-lg">
                {result.carbs || 0}g
              </p>
            </div>
            <div className="bg-zinc-900 p-3 rounded-lg">
              <p className="text-xs text-zinc-400 uppercase tracking-wide">
                Fat
              </p>
              <p className="font-bold text-white text-lg">{result.fat || 0}g</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
