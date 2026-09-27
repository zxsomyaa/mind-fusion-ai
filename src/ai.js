// ─── Local AI Client ──────────────────────────────────────────
// Supports Ollama (primary) and any OpenAI-compatible endpoint
// (LM Studio, Jan, LocalAI, etc.)

export const PRESETS = {
  ollama: {
    label: 'Ollama',
    baseUrl: 'http://localhost:11434',
    chatModel: 'llama3.2',
    visionModel: 'llava',
    hint: 'Run `ollama serve` then `ollama pull llama3.2`',
  },
  lmstudio: {
    label: 'LM Studio',
    baseUrl: 'http://localhost:1234',
    chatModel: 'local-model',
    visionModel: 'local-model',
    hint: 'Start the local server in LM Studio → Local Server tab',
  },
  custom: {
    label: 'Custom (OpenAI-compatible)',
    baseUrl: 'http://localhost:8080',
    chatModel: 'my-model',
    visionModel: 'my-model',
    hint: 'Any server that speaks the /v1/chat/completions API',
  },
};

export const DEFAULT_CONFIG = {
  provider: 'ollama',
  baseUrl: 'http://localhost:11434',
  chatModel: 'llama3.2',
  visionModel: 'llava',
};

/** Returns array of available model names, or throws if unreachable. */
export async function checkConnection(config) {
  const { provider, baseUrl } = config;
  const url = provider === 'ollama'
    ? `${baseUrl}/api/tags`
    : `${baseUrl}/v1/models`;

  const res = await fetch(url, { signal: AbortSignal.timeout(4000) });
  if (!res.ok) throw new Error(`Server responded with ${res.status}`);
  const data = await res.json();

  return provider === 'ollama'
    ? (data.models || []).map(m => m.name)
    : (data.data  || []).map(m => m.id);
}

/** Send a chat turn to the local model. */
export async function chatAI(config, messages, systemPrompt) {
  const { provider, baseUrl, chatModel } = config;
  const full = systemPrompt
    ? [{ role: 'system', content: systemPrompt }, ...messages]
    : messages;

  if (provider === 'ollama') {
    const res = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: chatModel, messages: full, stream: false }),
    });
    if (!res.ok) throw new Error(`Ollama error ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data.message?.content || '';
  }

  // OpenAI-compatible
  const res = await fetch(`${baseUrl}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: chatModel, messages: full }),
  });
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content || '';
}

/** Pull an Ollama model, reporting streamed progress via onProgress({status, completed, total}). */
export async function pullModel(config, modelName, onProgress, signal) {
  const { baseUrl } = config;
  const res = await fetch(`${baseUrl}/api/pull`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({ name: modelName, stream: true }),
  });
  if (!res.ok || !res.body) throw new Error(`Pull failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      const json = JSON.parse(line);
      if (json.error) throw new Error(json.error);
      onProgress?.(json);
    }
  }
}

/** Send an image + prompt to a vision-capable local model. */
export async function visionAI(config, imageBase64, mimeType, prompt, signal) {
  const { provider, baseUrl, visionModel } = config;

  if (provider === 'ollama') {
    const res = await fetch(`${baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal,
      body: JSON.stringify({
        model: visionModel,
        messages: [{ role: 'user', content: prompt, images: [imageBase64] }],
        stream: false,
      }),
    });
    if (!res.ok) {
      let detail = '';
      try { const d = await res.json(); detail = d.error || ''; } catch {}
      throw new Error(`Ollama vision error ${res.status}${detail ? ': ' + detail : ''}`);
    }
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data.message?.content || '';
  }

  // OpenAI-compatible vision
  const res = await fetch(`${baseUrl}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({
      model: visionModel,
      messages: [{
        role: 'user',
        content: [
          { type: 'image_url', image_url: { url: `data:${mimeType};base64,${imageBase64}` } },
          { type: 'text', text: prompt },
        ],
      }],
    }),
  });
  if (!res.ok) throw new Error(`Vision server error ${res.status}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content || '';
}
