import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(BASE_DIR, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    import uvicorn
    print("[PDF Analyzer] Starting Server...")
    print("Frontend: http://127.0.0.1:8080")
    print("API Docs: http://127.0.0.1:8080/docs")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8080, reload=True)
