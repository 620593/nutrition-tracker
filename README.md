# 🍏 Nutrition Tracker

An intelligent, AI-powered Nutrition Tracker application that helps users manage their daily meals, exercises, and nutritional goals. It leverages a modern tech stack to provide an intuitive interface, advanced image recognition for food, voice input processing, and personalized recommendations.

## ✨ Features

### 🤖 AI-Powered Processing Pipeline (LangGraph)
- **Smart Input Routing**: Automatically determines the type of user input (text, voice, image).
- **Speech-to-Text (STT)**: Processes voice commands to log meals and exercises seamlessly.
- **Image Detection**: Uses a trained Keras model to classify food images and estimate portion sizes.
- **Food Parsing & Nutrition Lookup**: Parses natural language food descriptions and fetches accurate nutritional data.
- **Goal Analysis & Recommendations**: Analyzes user progress against daily goals and provides personalized, AI-driven nutritional suggestions.

### 📊 Interactive Dashboard & Visualizations
- **Calorie Ring**: A dynamic visual representation of daily calorie intake vs. goals.
- **Protein Bar**: Tracks daily macronutrient progress (Protein, Carbs, Fats) with clean UI components.
- **Weekly Chart**: Visualizes eating and exercise trends over the past 7 days.
- **Suggestion Feed**: Displays real-time, actionable insights and AI recommendations.

### 📝 Comprehensive Tracking
- **Log Meals**: Easily log meals via text, image upload, or voice.
- **Log Exercises**: Keep track of physical activities and calories burned.
- **Daily Goals**: Set and monitor personal macro and calorie targets.
- **Leaderboard**: Engage with a community of users through a gamified leaderboard system.

### 🔒 Secure Authentication & Data Storage
- Uses **Supabase Auth** for secure user registration and login (email/password).
- Robust **Row Level Security (RLS)** ensures that user data is private and secure.

## 🛠️ Technology Stack

### Frontend
- **Framework**: React (Vite)
- **Styling**: Tailwind CSS
- **State Management & Routing**: React Router
- **Backend Communication**: Supabase JS Client

### Backend
- **Framework**: FastAPI (Python)
- **AI/Workflow Engine**: LangGraph
- **Machine Learning**: TensorFlow / Keras (Food Classification, Portion Estimation)
- **Database & Auth**: Supabase (PostgreSQL)

## 📁 Project Structure

```text
nutrition-tracker/
├── backend/
│   ├── agents/          # LangGraph state & nodes
│   ├── database/        # Supabase client & DB connection
│   ├── models/          # Trained Keras models (.keras, .pkl)
│   ├── .env.example     # Environment variables
│   ├── main.py          # FastAPI application entrypoint
│   └── requirements.txt # Python dependencies
└── frontend/
    ├── src/
    │   ├── api/         # Axios/Fetch clients
    │   ├── components/  # Reusable UI components (CalorieRing, etc.)
    │   ├── pages/       # Application views (Dashboard, LogMeal, etc.)
    │   ├── App.jsx      # React router setup
    │   ├── main.jsx     # Frontend entrypoint
    │   └── supabaseClient.js # Supabase configuration
    ├── index.html
    ├── package.json
    └── tailwind.config.js
```

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.9+)
- A Supabase Project (Database, Auth)

### Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `.env` based on `.env.example`.
5. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up environment variables (Supabase URL and Anon Key).
4. Start the development server:
   ```bash
   npm run dev
   ```

## 📜 License
This project is licensed under the MIT License.