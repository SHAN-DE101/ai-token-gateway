import sys
import os

# Ensure the project root is at the front of Python's search path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the FastAPI application
try:
    from app.main import app
except Exception as e:
    # Fail-safe minimal fallback app so it NEVER crashes with 500
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    
    app = FastAPI(title="AI Token Gateway")
    
    @app.get("/healthz")
    def health_check():
        return {"status": "degraded", "error": str(e)}
        
    @app.get("/dashboard", response_class=HTMLResponse)
    def fallback_dashboard():
        return f"""
        <html>
        <body style="font-family:sans-serif; background:#020617; color:#f8fafc; padding:2rem; text-align:center;">
          <h2 style="color:#ef4444;">Gateway Startup Exception</h2>
          <p style="font-family:monospace; background:#0f172a; padding:1rem; border-radius:8px; display:inline-block;">{str(e)}</p>
          <p>Please check your environment variables in Vercel settings.</p>
        </body>
        </html>
        """

    @app.get("/", response_class=HTMLResponse)
    def root():
        return fallback_dashboard()
