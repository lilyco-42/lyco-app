"""Wikipedia zh retriever: opensearch -> summary."""
from core.retrievers import UA


def wiki_search(client, question):
    """Wikipedia zh: opensearch -> summary. Returns evidence str or ''."""
    try:
        r = client.get("https://zh.wikipedia.org/w/api.php",
                       params={"action": "opensearch", "search": question,
                               "limit": 3, "format": "json"},
                       headers=UA)
        if r.status_code != 200:
            return f"__ERR__ wiki: http={r.status_code}"
        titles = r.json()[1]
        titles = r.json()[1]
        if not titles:
            return ""
        title = titles[0]
        s = client.get(
            f"https://zh.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=UA)
        if s.status_code != 200:
            return f"__ERR__ wiki: summary http={s.status_code}"
        data = s.json()
        extract = data.get("extract", "")[:600]
        url = (data.get("content_urls", {})
               .get("desktop", {}).get("page", ""))
        if not extract:
            return ""
        return f"【维基百科:{title}】{extract} 来源:{url}"
    except Exception as e:
        return f"__ERR__ wiki: {str(e)[:120]}"
