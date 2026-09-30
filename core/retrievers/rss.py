"""RustCC RSS retriever: fetch (1h cache) -> keyword match title+desc."""
import os
import re
import time
import xml.etree.ElementTree as ET

from core.retrievers import UA, has_anchor, score_text, tokens

RSS_URL = "https://rustcc.cn/rss"
RSS_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", ".cache")
RSS_CACHE = os.path.normpath(os.path.join(RSS_CACHE, "rustcc_rss.xml"))
RSS_TTL = 3600


def rss_search(client, question, topn=2):
    """RustCC RSS: fetch (1h cache) -> keyword match title+desc."""
    toks = tokens(question)
    try:
        if (os.path.exists(RSS_CACHE) and
                time.time() - os.path.getmtime(RSS_CACHE) < RSS_TTL):
            with open(RSS_CACHE, encoding="utf-8",
                      errors="replace") as f:
                xml_text = f.read()
        else:
            r = client.get(RSS_URL, headers=UA)
            r.raise_for_status()
            xml_text = r.text
            os.makedirs(os.path.dirname(RSS_CACHE), exist_ok=True)
            with open(RSS_CACHE, "w", encoding="utf-8") as f:
                f.write(xml_text)
        root = ET.fromstring(xml_text)
    except Exception as e:
        return [], [f"rss-err: {str(e)[:100]}"]
    scored = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = re.sub(r"<[^>]+>", "",
                      item.findtext("description") or "")[:300]
        s = score_text(toks, title) * 3 + score_text(toks, desc)
        if s >= 2 and (has_anchor(toks, title) or has_anchor(toks, desc)):
            scored.append((s, f"【RustCC:{title}】{desc} 来源:{link}"))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:topn]], []
