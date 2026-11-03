"""Small traceable, curated local palmistry knowledge base (not scientific evidence)."""
import json
import re
from pathlib import Path

KB = json.loads((Path(__file__).parent / 'knowledge' / 'palmistry.json').read_text(encoding='utf-8'))


def retrieve(query, k=4):
    terms = set(re.findall(r'[a-z]+', (query or '').lower()))
    ranked = []
    for item in KB:
        tags = set(item['tags'])
        words = set(re.findall(r'[a-z]+', (item['title']+' '+item['tradition']).lower()))
        score = sum(4 for t in terms if t in tags) + sum(1 for t in terms if t in words)
        ranked.append((score,item))
    ranked.sort(key=lambda p:p[0],reverse=True)
    hits = [item for score,item in ranked if score>0][:k]
    return hits or [next(x for x in KB if x['id']==id) for id in ['heart','head','life','ethics']]


def citation_set(items):
    return [{'title':item['title'], 'id':item['id']} for item in items]
