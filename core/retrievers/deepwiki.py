"""DeepWiki official MCP retriever (repo knowledge).

Two measured fixes from lyco-model (section 12 of its report):

  - a 200 response is not necessarily an answer. DeepWiki relays upstream
    failures inside `content`, e.g. "Error processing question: Client error
    '429 Too Many Requests' for url 'https://api.devin.ai/ada/query'". That
    text used to be fed to the model as evidence and recited back.
  - the rate limit is a window quota and it answers in ~0.25 s, so retries
    must wait on a seconds scale -- and only for limits. A permanent error is
    not retried.
"""
import json
import time

DEEPWIKI_MCP = "https://mcp.deepwiki.com/mcp"

ERR_MARKERS = ("Error processing question", "Too Many Requests", "Client error",
               "Server error", "Traceback", "for url ")

RETRY_TRIES = 3
RETRY_BASE = 2.0      # seconds
RETRY_MAX = 16.0


def looks_like_error(text):
    return any(m in text for m in ERR_MARKERS)


def is_ratelimit(text):
    t = text.lower()
    return ("429" in t or "too many requests" in t
            or "rate limit" in t or "quota" in t)


def backoff_sleeps(tries=RETRY_TRIES, base=RETRY_BASE, limit=RETRY_MAX):
    """Waits *between* attempts. Deliberately deterministic: random jitter
    would make recorded runs unreplayable."""
    return [min(base * (2 ** i), limit) for i in range(max(tries - 1, 0))]


def mcp_rpc(client, session, payload):
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if session:
        headers["Mcp-Session-Id"] = session
    r = client.post(DEEPWIKI_MCP, headers=headers, json=payload)
    sess = r.headers.get("Mcp-Session-Id", session)
    out = []
    for line in r.text.splitlines():
        if line.startswith("data:"):
            try:
                out.append(json.loads(line[5:].strip()))
            except Exception:
                pass
    return sess, out


def deepwiki_raw(client, repo, question):
    """One MCP call: initialize -> tools/call -> ask_wiki_question.
    Returns the answer text, '' , or a __ERR__ string."""
    try:
        sess, _ = mcp_rpc(client, None, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "lyco-rag", "version": "0.1"}}})
        sess, msgs2 = mcp_rpc(client, sess, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "ask_wiki_question",
                       "arguments": {"repoName": repo,
                                     "question": question}}})
        for m in msgs2:
            res = (m.get("result") or {})
            contents = res.get("content") or []
            texts = [c.get("text", "") for c in contents if c.get("type")
                     in ("text",)]
            if texts:
                return "".join(texts)
        err = next((m.get("error") for m in msgs2 if m.get("error")), None)
        return f"__ERR__ deepwiki: {str(err)[:120]}" if err else ""
    except Exception as e:
        return f"__ERR__ deepwiki: {str(e)[:120]}"


def deepwiki_ask(client, repo, question, tries=RETRY_TRIES,
                 sleeper=time.sleep, call=None):
    """Evidence string, '' , or a __ERR__ string. Rate limits get exponential
    backoff; anything else that looks like an error is returned at once so the
    caller can fall back to another source instead of waiting."""
    call = call or (lambda: deepwiki_raw(client, repo, question))
    waits = backoff_sleeps(tries)
    attempts = 0
    for i in range(tries):
        attempts += 1
        body = call()
        if not body:
            return ""
        if body.startswith("__ERR__") or looks_like_error(body):
            if is_ratelimit(body) and i < tries - 1:
                sleeper(waits[i])
                continue
            kind = "ratelimited" if is_ratelimit(body) else "error"
            return f"__ERR__ deepwiki {kind} after {attempts} try: {body[:100]}"
        return f"【DeepWiki:{repo}】{body[:600]}"
    return ""
