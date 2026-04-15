# ============================================================
# SHADOWFORGE OS — BRIDGE SERVER
# Bridges the Node.js backend with the Python Agent Core.
# Allows full tool execution and robust state management.
# ============================================================

import os
import sys
import logging
from flask import Flask, request, jsonify
from pathlib import Path

# Add root app directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from core.config import Config
from core.logger import setup_logger
from agent.agent_core import AgentCore, MessageRole

app = Flask(__name__)

# Initialize Core components
config = Config()
config.load()
setup_logger(config)
agent = AgentCore(config)

logger = logging.getLogger("Bridge.Server")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "agent": str(agent),
        "providers": agent.provider_manager.get_available_providers()
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Expects: { "prompt": "...", "workspace": "...", "is_sudo": false }
    """
    data = request.json
    prompt = data.get("prompt", "")
    workspace = data.get("workspace")
    is_sudo = data.get("is_sudo", False)

    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    logger.info(f"Incoming request: {prompt[:50]}...")
    
    try:
        # Wrap prompt with sudo if requested
        if is_sudo and not prompt.startswith("sudo "):
            prompt = f"sudo {prompt}"
            
        api_keys = data.get("api_keys", {})
        response = agent.process(prompt, workspace=workspace, api_keys=api_keys)
        
        return jsonify({
            "success": response.success,
            "content": response.content,
            "provider": response.provider,
            "model": response.model,
            "tokens": response.tokens_used,
            "files": [str(p) for p in response.files_written],
            "error": response.error
        })
    except Exception as e:
        logger.error(f"Agent processing error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(agent.get_history_as_dicts())

@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    agent.clear_history()
    return jsonify({"success": True})

if __name__ == "__main__":
    PORT = int(os.environ.get("BRIDGE_PORT", 8000))
    logger.info(f"Starting Python Bridge Server on port {PORT}...")
    app.run(host="0.0.0.0", port=PORT, debug=False)
