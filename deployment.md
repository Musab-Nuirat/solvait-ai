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
  8. Test your backend:
    - Visit https://your-backend-url.onrender.com/health
    - Should return: {"status":"healthy","service":"Solvait AI Assistant","version":"0.1.0"}

  ---
  Step 2.5: Test Local Streamlit with Deployed Backend (Optional but Recommended)

  Before deploying Streamlit Cloud, test locally that your Streamlit app can connect to the deployed backend:

  1. Make sure your Render backend is deployed and running
  2. Set the API_URL environment variable to point to your Render backend:
    
    Windows PowerShell:
      $env:API_URL="https://solvait-api.onrender.com"
    
    Windows CMD:
      set API_URL=https://solvait-api.onrender.com
    
    Linux/Mac:
      export API_URL=https://solvait-api.onrender.com

  3. Run Streamlit locally:
      streamlit run streamlit_app.py

  4. Test the connection:
    - Open http://localhost:8501
    - Try sending a message in the chat
    - Check if database tables load in the sidebar
    - Verify there are no connection errors

  5. If everything works, you're ready to deploy to Streamlit Cloud!

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
  - When setting API_URL secret in Streamlit Cloud, ensure there are NO trailing spaces
    (e.g., use "https://Solvait-api.onrender.com" not "https://Solvait-api.onrender.com ")
  - If you see connection errors, verify the Render URL is correct and the backend is running
  - Free tier services on Render may spin down after inactivity - first request may be slow

  ---
  Done! Your app will be live at https://your-app.streamlit.app
