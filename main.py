import uvicorn
from src.api.server import app

if __name__ == "__main__":
    # This block runs when you execute 'python main.py'
    # It starts the Uvicorn server, telling it where to find our FastAPI app.
    # host="0.0.0.0" makes it accessible on your local network.
    # reload=True automatically restarts the server when you save a file,
    # which is incredibly useful for development.
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)