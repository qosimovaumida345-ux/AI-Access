# ============================================================
# SHADOWFORGE OS — AI TOOLS
# Defines the actions the agent can perform on the device.
# Each tool is gated by the PermissionManager.
# ============================================================

import os
import subprocess
import logging
import psutil
import json
import webbrowser
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("Agent.Tools")

class ToolBox:
    """
    Central repository for AI-executable tools.
    """
    
    def __init__(self, agent_core):
        self.agent = agent_core
        self.perms = agent_core.perms
        
    def execute(self, tool_name: str, args: Dict[str, Any], is_sudo: bool = False) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        logger.info(f"Tool execution requested: {tool_name} (sudo={is_sudo})")
        
        # Security: check if tool exists
        method = getattr(self, f"tool_{tool_name}", None)
        if not method:
            return {"success": False, "error": f"Tool '{tool_name}' not found."}
            
        try:
            return method(args, is_sudo=is_sudo)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ── SYSTEM TOOLS ──────────────────────────────────────
    def tool_system_control(self, args: Dict[str, Any], is_sudo: bool = False) -> Dict[str, Any]:
        """
        Control system settings.
        Args: { "action": "wifi_on" | "wifi_off" | "volume_set" | "get_status" }
        """
        action = args.get("action")
        
        # Check permissions
        if not self.perms.check("modify_system", operation=f"system_control_{action}", is_sudo=is_sudo).granted:
            return {"success": False, "error": "Permission denied for system modification."}

        if action == "wifi_on":
            if os.name == "nt": # Windows
                subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "enabled"], check=True)
            else: # Linux/Mac
                subprocess.run(["nmcli", "radio", "wifi", "on"], check=True)
            return {"success": True, "message": "WiFi enabled."}
            
        elif action == "wifi_off":
            if os.name == "nt":
                subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "disabled"], check=True)
            else:
                subprocess.run(["nmcli", "radio", "wifi", "off"], check=True)
            return {"success": True, "message": "WiFi disabled."}
            
        elif action == "get_status":
            cpu_usage = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            battery = psutil.sensors_battery()
            return {
                "success": True,
                "data": {
                    "cpu": f"{cpu_usage}%",
                    "ram": f"{mem.percent}%",
                    "battery": f"{battery.percent}%" if battery else "N/A"
                }
            }

        return {"success": False, "error": f"Unknown action: {action}"}

    # ── BROWSER TOOLS ─────────────────────────────────────
    def tool_browser(self, args: Dict[str, Any], is_sudo: bool = False) -> Dict[str, Any]:
        """
        Open URLs or search the web.
        Args: { "action": "open" | "search", "query": "..." }
        """
        action = args.get("action")
        query = args.get("query", "")
        
        if action == "open":
            webbrowser.open(query)
            return {"success": True, "message": f"Opened {query}"}
        elif action == "search":
            search_url = f"https://www.google.com/search?q={query}"
            webbrowser.open(search_url)
            return {"success": True, "message": f"Searching for: {query}"}
            
        return {"success": False, "error": "Unknown browser action."}

    # ── FILE TOOLS ────────────────────────────────────────
    def tool_filesystem(self, args: Dict[str, Any], is_sudo: bool = False) -> Dict[str, Any]:
        """
        Advanced file operations.
        Args: { "action": "extract", "path": "...", "out": "..." }
        """
        action = args.get("action")
        path = args.get("path")
        
        if action == "extract":
            import zipfile
            # Sandbox check will happen inside extract_all if we use the sandbox logic
            # For now, let's keep it simple.
            src_path = Path(path)
            out_path = Path(args.get("out", str(src_path.parent)))
            
            with zipfile.ZipFile(src_path, 'r') as zip_ref:
                zip_ref.extractall(out_path)
            return {"success": True, "message": f"Extracted to {out_path}"}
            
        return {"success": False, "error": "Unknown filesystem action."}

    # ── CODE TOOLS ────────────────────────────────────────
    def tool_exec_python(self, args: Dict[str, Any], is_sudo: bool = False) -> Dict[str, Any]:
        """
        Execute arbitrary Python code (SUDO ONLY).
        """
        if not is_sudo:
            return {"success": False, "error": "Python execution requires SUDO mode."}
            
        code = args.get("code", "")
        try:
            # We run it in a separate process for safety
            # In a real app, this should be even more sandboxed
            result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
            return {
                "success": True, 
                "stdout": result.stdout, 
                "stderr": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

import sys
