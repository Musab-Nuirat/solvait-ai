Step 1: Push to GitHub

  git add .
  git commit -m "Add deployment configuration"
  git push origin main

  ---
  Step 2: Deploy Backend on Render

  Option A: Using render.yaml (Recommended)
  1. Go to https://render.com → Sign up with GitHub
  2. Click "New +" → "Blueprint"
  3. Connect your solvait repository
  4. Render will automatically detect render.yaml and configure the service
  5. Add Environment Variables in the dashboard:
    - GOOGLE_API_KEY = your Google API key
    - LLAMA_CLOUD_API_KEY = your LlamaCloud API key (if using LlamaParse)
    - DEBUG_MODE = false
  6. Click "Apply" and wait for deploy
  7. Copy your URL (e.g., https://Solvait-api.onrender.com)

  Option B: Manual Configuration
  1. Go to https://render.com → Sign up with GitHub
  2. Click "New +" → "Web Service"
  3. Connect your solvait repository
  4. Configure:
    - Name: Solvait-api
    - Runtime: Python 3.11.7 (must specify full version: major.minor.patch)
    - Build Command: pip install -r requirements.txt
    - Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    - Plan: Free
  5. Add Environment Variables:
    - GOOGLE_API_KEY = your Google API key
    - LLAMA_CLOUD_API_KEY = your LlamaCloud API key (optional, if using LlamaParse)
    - DEBUG_MODE = false
    - PYTHON_VERSION = 3.11.7 (must be full version: major.minor.patch)
  6. Click "Create Web Service"
  7. Wait for deploy → Copy your URL (e.g., https://Solvait-api.onrender.com)

  ---
  Step 3: Deploy Frontend on Streamlit Cloud

  1. Go to https://share.streamlit.io → Sign up with GitHub
  2. Click "New app"
  3. Select your solvait repository
  4. Set:
    - Main file: streamlit_app.py
    - Branch: main
  5. Click "Advanced settings" → "Secrets" tab → Add secret:
    API_URL = "https://Solvait-api.onrender.com"
    (Replace with your actual Render URL)
  6. Click "Deploy"

  ---
  Important Notes:

  - Make sure your Render backend is fully deployed before deploying Streamlit frontend
  - The Streamlit app will use the API_URL environment variable to connect to your backend
  - If you see connection errors, verify the Render URL is correct and the backend is running
  - Free tier services on Render may spin down after inactivity - first request may be slow

  ---
  Done! Your app will be live at https://your-app.streamlit.app
