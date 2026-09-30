"""core.cli -- the loop and the POI chain as one JSON object per invocation.

For processes that cannot import Python: the DeepSeek Harness plugin shells
out to this, so the RAG loop and the "which shop is better" ranking stay in
one implementation.

    python -m core.cli "mpkg 记忆包是什么？有什么用？"
    python -m core.cli --shops 理发 --lat 31.2304 --lng 121.4737 --radius 1000

Stdout is always exactly one JSON object, including on failure ({"error": ...}),
so a caller never has to distinguish stdout from stderr to parse.
"""
import argparse
import json
import sys

# module-level so the except clause below always has the name bound
from services.poi import POIError


def build_parser():
    p = argparse.ArgumentParser(prog="python -m core.cli")
    p.add_argument("question", nargs="?", default="",
                   help="question for the OODA loop (ignored with --shops)")
    p.add_argument("--shops", metavar="TYPE", default=None,
                   help="rank nearby shops of this kind instead (needs "
                        "--lat/--lng and AMAP_WEBSERVICE_KEY)")
    p.add_argument("--lat", type=float)
    p.add_argument("--lng", type=float)
    p.add_argument("--radius", type=int, default=1000)
    p.add_argument("--question", dest="q", default=None,
                   help="overall question used when ranking shops")
    return p


def run(argv=None, *, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        if args.shops:
            if args.lat is None or args.lng is None:
                raise ValueError("--shops needs --lat and --lng")
            from services.poi import nearby_search
            from services.reviews import rank_shops
            pois = nearby_search(args.lat, args.lng, radius_m=args.radius,
                                 keywords=args.shops)
            ranked = rank_shops(pois, question=args.question)
            payload = {"mode": "shops", "kind": args.shops,
                       "radius_m": args.radius, "found": len(pois),
                       "ranking": ranked}
        else:
            if not args.question.strip():
                raise ValueError("give a question, or use --shops TYPE")
            from core.loop import answer
            r = answer(args.question)
            payload = {"mode": "ask",
                       "question": r["question"],
                       "answer": r["response"],
                       "routed_search": r["routed_search"],
                       "evidence": r["evidence"],
                       "retrieve_notes": r["retrieve_notes"],
                       "verify": r["verify"],
                       "elapsed_s": r["total_elapsed"]}
    except (ValueError, POIError) as exc:      # expected operator errors only
        json.dump({"error": str(exc)}, out, ensure_ascii=False)
        out.write("\n")
        return 2
    json.dump(payload, out, ensure_ascii=False)
    out.write("\n")
    return 0


def main(argv=None):
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
