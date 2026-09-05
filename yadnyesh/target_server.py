"""
Target Login Server — Smart SOC Miniproject
=============================================
A simple Flask backend that acts as the "victim" website.
The React frontend (react-target/) communicates with this server.

Endpoints:
  GET  /         → Home page status check
  POST /login    → Login endpoint (attacked by bruteforce_simulation.py)
  GET  /health   → Health check for the simulation script

Run: python target_server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import time

app = Flask(__name__)
CORS(app)  # Allow React frontend on :5173 to communicate

# Suppress request logs during attack simulation (reduce console noise)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Simple in-memory counter to track login attempts (for demo)
attempt_count = 0
failed_count  = 0

@app.route('/')
def home():
    return jsonify({
        "status": "ONLINE",
        "service": "Smart SOC Target Website",
        "endpoints": ["/login", "/health"]
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "uptime": time.time()})

@app.route('/login', methods=['POST'])
def login():
    global attempt_count, failed_count

    data     = request.form if request.form else request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')

    attempt_count += 1

    # Only one valid credential pair — everything else is a failed attempt
    if username == "admin" and password == "secretpassword123":
        return jsonify({"status": "success", "message": "Login successful!"}), 200

    failed_count += 1
    return jsonify({
        "status":  "error",
        "message": "Invalid credentials!",
        "attempt": attempt_count,
        "failed":  failed_count
    }), 401


if __name__ == '__main__':
    print("=" * 50)
    print("  Smart SOC — Target Server")
    print("  Running on http://0.0.0.0:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, threaded=True)
