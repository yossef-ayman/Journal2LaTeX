import os
import sys

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting PDF Analyzer Server...")
    print("👉 Frontend: http://127.0.0.1:8080")
    print("👉 API Docs: http://127.0.0.1:8080/docs")
    uvicorn.run("main:app", app_dir=backend_dir, host="127.0.0.1", port=8080, reload=True)
