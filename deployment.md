  Step 1: Push to GitHub
                                                                                                      
  git add .
  git commit -m "Add deployment configuration"
  git push origin main

  ---
  Step 2: Deploy Backend on Render

  1. Go to https://render.com → Sign up with GitHub
  2. Click "New +" → "Web Service"
  3. Connect your solvait repository
  4. Configure:
    - Name: Solvait-api
    - Runtime: Python 3
    - Build Command: pip install -r requirements.txt
    - Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    - Plan: Free
  5. Add Environment Variables:
    - GOOGLE_API_KEY = your key
    - DEBUG_MODE = false
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
  5. Click "Advanced settings" → Add secret:
  API_URL = "https://Solvait-api.onrender.com"
  5. (use your actual Render URL)
  6. Click "Deploy"

  ---
  Done! Your app will be live at https://your-app.streamlit.app
