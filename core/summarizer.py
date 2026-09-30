"""Summarizer: local chat model via llama-cli (never tested on memory)."""
import os
import re
import subprocess
import time

LLAMA_CLI = r"D:\APP\scoop\shims\llama-cli.exe"
CHAT_MODEL = (r"D:\gal\AliceInCradle\lyco-model\models"
              r"\chat_slm_qwen3_0p6b-Q4_K_M.gguf")


def dec(b):
    if not b:
        return ""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("utf-8", errors="replace")


def summarize(question, evidence, searched):
    """OODA Act: chat model only summarizes retrieved evidence."""
    if evidence:
        prompt = ("【检索到的资料】\n" + "\n".join(evidence) +
                  f"\n\n【用户问题】\n{question}\n\n"
                  "要求：只根据上述资料回答，资料没有的内容就说不知道。"
                  "用2-4句话总结要点。")
    elif searched:
        prompt = (f"【用户问题】\n{question}\n\n"
                  "要求：没有检索到相关资料，请直接说不知道，并说明可以去哪里查。")
    else:
        prompt = question
    t0 = time.time()
    p = subprocess.run(
        [LLAMA_CLI, "-m", CHAT_MODEL, "-p", prompt, "-n", "256",
         "--single-turn", "--no-display-prompt"],
        capture_output=True, timeout=180)
    dt = time.time() - t0
    out = dec(p.stdout) + dec(p.stderr)
    m = re.search(r"Generation:\s*([\d.]+)\s*t/s", out)
    # long-prompt echo is truncated with a "...(truncated)" marker and the
    # answer follows it; short prompts echo verbatim as "> "+prompt
    if "(truncated)" in out:
        body = out.split("(truncated)")[-1]
    else:
        marker = "> " + prompt
        body = out.split(marker)[-1] if marker in out else out
    body = re.sub(r"\[ ?Prompt:.*", "", body)
    body = body.split("Exiting...")[0].strip()
    return {"response": body[-3000:],
            "gen_ts": float(m.group(1)) if m else None,
            "elapsed": round(dt, 2), "rc": p.returncode}
