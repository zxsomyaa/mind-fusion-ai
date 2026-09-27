"""
Talks to a local AI server - Ollama by default, or any OpenAI-compatible
server (LM Studio, Jan, LocalAI, etc). Nothing here ever calls out to the
internet or to a cloud AI provider; every request goes to a base_url that
points at the user's own machine.
"""

import json

import requests

PRESETS = {
    "ollama": {
        "label": "Ollama",
        "base_url": "http://localhost:11434",
        "chat_model": "llama3.2",
        "vision_model": "llava",
        "hint": "Run `ollama serve` then `ollama pull llama3.2`",
    },
    "lmstudio": {
        "label": "LM Studio",
        "base_url": "http://localhost:1234",
        "chat_model": "local-model",
        "vision_model": "local-model",
        "hint": "Start the local server in LM Studio -> Local Server tab",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "base_url": "http://localhost:8080",
        "chat_model": "my-model",
        "vision_model": "my-model",
        "hint": "Any server that speaks the /v1/chat/completions API",
    },
}

DEFAULT_CONFIG = {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "chat_model": "llama3.2",
    "vision_model": "llava",
}


def check_connection(config):
    """Returns a list of available model names, or raises if unreachable."""
    provider = config["provider"]
    base_url = config["base_url"]
    url = f"{base_url}/api/tags" if provider == "ollama" else f"{base_url}/v1/models"

    res = requests.get(url, timeout=4)
    res.raise_for_status()
    data = res.json()

    if provider == "ollama":
        return [m["name"] for m in data.get("models", [])]
    return [m["id"] for m in data.get("data", [])]


def chat_ai(config, messages, system_prompt=None):
    """Sends a chat turn to the local model and returns the reply text."""
    provider = config["provider"]
    base_url = config["base_url"]
    chat_model = config["chat_model"]

    full_messages = messages
    if system_prompt:
        full_messages = [{"role": "system", "content": system_prompt}] + messages

    if provider == "ollama":
        res = requests.post(
            f"{base_url}/api/chat",
            json={"model": chat_model, "messages": full_messages, "stream": False},
            timeout=180,
        )
        if not res.ok:
            raise RuntimeError(f"Ollama error {res.status_code}")
        data = res.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data.get("message", {}).get("content", "")

    # OpenAI-compatible
    res = requests.post(
        f"{base_url}/v1/chat/completions",
        json={"model": chat_model, "messages": full_messages},
        timeout=180,
    )
    if not res.ok:
        raise RuntimeError(f"Server error {res.status_code}")
    data = res.json()
    return data["choices"][0]["message"]["content"] if data.get("choices") else ""


def vision_ai(config, image_base64, prompt):
    """Sends an image + prompt to a vision-capable local model."""
    provider = config["provider"]
    base_url = config["base_url"]
    vision_model = config["vision_model"]

    if provider == "ollama":
        res = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": vision_model,
                "messages": [{"role": "user", "content": prompt, "images": [image_base64]}],
                "stream": False,
            },
            timeout=180,
        )
        if not res.ok:
            detail = ""
            try:
                detail = res.json().get("error", "")
            except ValueError:
                pass
            raise RuntimeError(f"Ollama vision error {res.status_code}{': ' + detail if detail else ''}")
        data = res.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data.get("message", {}).get("content", "")

    # OpenAI-compatible vision
    res = requests.post(
        f"{base_url}/v1/chat/completions",
        json={
            "model": vision_model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        },
        timeout=180,
    )
    if not res.ok:
        raise RuntimeError(f"Vision server error {res.status_code}")
    data = res.json()
    return data["choices"][0]["message"]["content"] if data.get("choices") else ""


def pull_model(config, model_name, on_progress=None):
    """Streams an `ollama pull` over HTTP so the desktop app can fetch a
    missing model itself, instead of asking the user to run a terminal
    command. `on_progress` is called with each JSON status dict Ollama sends."""
    base_url = config["base_url"]
    with requests.post(
        f"{base_url}/api/pull",
        json={"name": model_name, "stream": True},
        stream=True,
        timeout=600,
    ) as res:
        if not res.ok:
            raise RuntimeError(f"Pull failed: {res.status_code}")
        for line in res.iter_lines():
            if not line:
                continue
            status = json.loads(line)
            if status.get("error"):
                raise RuntimeError(status["error"])
            if on_progress:
                on_progress(status)
