import sys

# Check for GEMINI_API_KEY
import os
import app

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)
        
    print("Starting Watch Banner Generator Web UI on http://localhost:5001")
    app.app.run(host='0.0.0.0', port=5001, debug=False)
