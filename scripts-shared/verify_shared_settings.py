"""Verify native settings without starting model turns or reading credentials."""
import argparse
import json
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

def effective_config(binary, cwd):
    proc = subprocess.Popen([binary, "app-server", "--strict-config"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
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
    parser.add_argument("--codex", required=True)
    parser.add_argument("--cwd", required=True)
    args = parser.parse_args()
    root = Path(args.config_home)
    native = tomllib.loads((root/"config.toml").read_text(encoding="utf-8-sig"))
    assert native["agents"]["max_concurrent_threads_per_session"] == 10
    assert native["agents"]["default_subagent_model"] == "gpt-6.1-sol"
    assert native["agents"]["default_subagent_reasoning_effort"] == "high"
    verified = []
    for name, expected in PROFILES.items():
        for path in [root/"agents"/(name+".toml"), root/(name+".config.toml")]:
            value = tomllib.loads(path.read_text(encoding="utf-8-sig"))
            actual = tuple(value[key] for key in (
                "model", "model_reasoning_effort", "service_tier"))
            assert actual == expected, f"profile differs: {name}"
        verified.append(name)
    assert (root/"AGENTS.md").is_file()
    config = effective_config(args.codex, args.cwd)
    assert config["agents"]["max_concurrent_threads_per_session"] == 10
    assert config["agents"]["default_subagent_model"] == "gpt-6.1-sol"
    assert config["agents"]["default_subagent_reasoning_effort"] == "high"
    print(json.dumps({"status":"PASS", "effective_config":config,
        "profiles_parsed":verified, "model_turns_started":0,
        "fast_or_astra_profiles_invoked":False}, ensure_ascii=False))

if __name__ == "__main__":
    main()
