"""Verify native settings without starting model turns or reading credentials."""
import argparse
import json
import os
import ntpath
import queue
import subprocess
import threading
from pathlib import Path
import tomllib

PROFILES = {
    "sol_high": ("gpt-6.1-sol", "high", "default"),
    "sol_xhigh": ("gpt-6.1-sol", "xhigh", "default"),
    "sol_medium": ("gpt-6.1-sol", "medium", "default"),
    "luna_xhigh_standard": ("gpt-6-luna", "xhigh", "default"),
    "luna_xhigh_fast": ("gpt-6-luna", "xhigh", "fast"),
    "astra_high_approved": ("gpt-6-astra", "high", "default"),
}

def require(condition, message):
    # Assertions disappear under python -O / PYTHONOPTIMIZE. Verification must
    # retain every pass condition in optimized interpreter modes.
    if not condition:
        raise ValueError(message)

def verify_agents(agents, source):
    require(isinstance(agents, dict), source + ": agents configuration missing")
    require(agents.get("max_concurrent_threads_per_session") == 10,
            source + ": worker capacity differs")
    require(agents.get("default_subagent_model") == "gpt-6.1-sol",
            source + ": worker model differs")
    require(agents.get("default_subagent_reasoning_effort") == "high",
            source + ": worker reasoning effort differs")

def server_environment(binary, config_home, server_config_home=None):
    # Bind the server to the same home whose files main() validated.
    child_env = os.environ.copy()
    interop = os.name == "posix" and str(binary).lower().endswith(".exe")
    if interop:
        if not server_config_home or not ntpath.isabs(server_config_home) or not ntpath.splitdrive(server_config_home)[0]:
            raise ValueError("WSL-to-Windows verifier requires explicit --server-config-home with the Windows path to the same home")
        child_env["CODEX_HOME"] = server_config_home
        # The provided value is already a Windows path: never apply WSLENV /p.
        entries = [entry for entry in child_env.get("WSLENV", "").split(":")
                   if entry and entry.split("/", 1)[0] != "CODEX_HOME"]
        child_env["WSLENV"] = ":".join(entries + ["CODEX_HOME/w"])
    else:
        child_env["CODEX_HOME"] = str(Path(server_config_home or config_home).expanduser().resolve())
    return child_env

def effective_config(binary, cwd, config_home, server_config_home=None):
    child_env = server_environment(binary, config_home, server_config_home)
    proc = subprocess.Popen([binary, "app-server", "--strict-config"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                            env=child_env)
    replies = queue.Queue()
    def reader():
        for line in proc.stdout:
            try:
                replies.put(json.loads(line))
            except json.JSONDecodeError:
                pass
    threading.Thread(target=reader, daemon=True).start()
    def send(message):
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()
    def result(request_id):
        import time
        deadline = time.monotonic() + 25
        while True:
            response = replies.get(timeout=max(.1, deadline-time.monotonic()))
            if response.get("id") == request_id:
                if "error" in response:
                    raise RuntimeError("config RPC rejected: " + str(response["error"].get("code")))
                return response["result"]
            if time.monotonic() >= deadline:
                raise TimeoutError("config RPC timeout")
    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "shared-settings-verifier", "version": "1.0"}}})
        result(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "config/read", "params": {
            "includeLayers": False, "cwd": str(cwd)}})
        value = result(2)
        config = value["config"]
        return {key: config.get(key) for key in (
            "model", "model_reasoning_effort", "service_tier", "agents")}
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=10)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-home", required=True)
    parser.add_argument("--server-config-home", help="Native server path to the same home; required when launching Windows codex.exe from WSL")
    parser.add_argument("--codex", required=True)
    parser.add_argument("--cwd", required=True)
    args = parser.parse_args()
    root = Path(args.config_home).expanduser().resolve()
    native = tomllib.loads((root/"config.toml").read_text(encoding="utf-8-sig"))
    verify_agents(native.get("agents"), "native files")
    verified = []
    for name, expected in PROFILES.items():
        for path in [root/"agents"/(name+".toml"), root/(name+".config.toml")]:
            value = tomllib.loads(path.read_text(encoding="utf-8-sig"))
            actual = tuple(value[key] for key in (
                "model", "model_reasoning_effort", "service_tier"))
            require(actual == expected, "profile differs: " + name)
        verified.append(name)
    require((root/"AGENTS.md").is_file(), "AGENTS.md missing")
    require(bool((root/"AGENTS.md").read_text(encoding="utf-8-sig").strip()),
            "AGENTS.md empty")
    config = effective_config(args.codex, args.cwd, root, args.server_config_home)
    verify_agents(config.get("agents"), "effective server")
    print(json.dumps({"status":"PASS", "effective_config":config,
        "file_config_home":str(root), "server_config_home":server_environment(args.codex, root, args.server_config_home)["CODEX_HOME"],
        "profiles_parsed":verified, "model_turns_started":0,
        "fast_or_astra_profiles_invoked":False}, ensure_ascii=False))

if __name__ == "__main__":
    main()
