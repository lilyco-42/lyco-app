"""A stand-in for `core.cli` used by the plugin's end-to-end test.

The real CLI needs llama-cli and a local model, so a plugin test cannot call
it. This stub keeps the *contract* -- one JSON object on stdout, exit 2 with
{"error": ...} -- and echoes the argv it received, which is what the test
actually asserts (argument marshalling across the process boundary).

Stdlib only, so any python on PATH runs it.
"""
import json
import sys


def main(argv, out=None):
    out = out or sys.stdout
    if not argv or not argv[0].strip():
        json.dump({"error": "give a question, or use --shops TYPE"}, out,
                  ensure_ascii=False)
        out.write("\n")
        return 2
    if "--shops" in argv:
        payload = {"mode": "shops", "kind": argv[argv.index("--shops") + 1],
                   "radius_m": 1000, "found": 2, "argv": argv,
                   "ranking": [
                       {"name": "A 店", "address": "某路 1 号", "reason": "证据充分",
                        "verify_pass": True},
                       {"name": "B 店", "address": "某路 2 号", "reason": "证据不足",
                        "verify_pass": False},
                   ]}
        json.dump(payload, out, ensure_ascii=False)
        out.write("\n")
        return 0
    if "BOOM" in argv[0]:
        json.dump({"error": "simulated core failure"}, out, ensure_ascii=False)
        out.write("\n")
        return 2
    json.dump({"mode": "ask", "question": argv[0], "answer": "stub 答案。",
               "routed_search": True, "evidence": ["【本地库:x】e"],
               "retrieve_notes": ["local:1"], "elapsed_s": 0.42,
               "verify": {"pass": True, "reason": "overlap=3"}},
              out, ensure_ascii=False)
    out.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
