"""Playful, explicitly fictional palmistry stories; separate from image evidence."""
import json
from llm import _invoke, provider_name
from knowledge import retrieve, citation_set

NOTICE = 'For fun only — inspired by traditional palmistry, not a factual prediction.'
THEMES = {'adventure': ('The lantern-lit crossroads', 'curiosity and new experiences'),
          'connection': ('The garden of little connections', 'friendship and kindness'),
          'purpose': ('The maker’s next chapter', 'creativity and purpose')}
SHAPES = {'unknown', 'curved', 'straight', 'not-visible'}
KEYS = ('heart', 'head', 'life', 'fate')

def validate_choices(theme, choices):
    if theme not in THEMES:
        raise ValueError('Choose adventure, connection, or purpose.')
    if not isinstance(choices, dict) or any(k not in KEYS or v not in SHAPES for k,v in choices.items()):
        raise ValueError('Invalid symbolic line choices.')
    return {key: choices.get(key, 'unknown') for key in KEYS}

def build_fun_reading(analysis, theme='adventure', choices=None):
    choices = validate_choices(theme, choices if choices is not None else {})
    title, mood = THEMES[theme]
    counts = {side: len((analysis.get(side) or {}).get('features', [])) for side in ('left','right')}
    selected = [key for key, shape in choices.items() if shape in ('curved','straight')]
    kb = retrieve(' '.join(selected or ['heart','head','fate'])+' '+theme, k=4)
    route = 'a winding garden path' if 'curved' in choices.values() else 'a lantern-lined avenue'
    openers = {
        'adventure': f'Imagine stepping onto {route}, with a small golden compass in your hand. In this invented chapter, an unfamiliar doorway is an invitation to explore a hobby, a place, or an idea simply for the joy of discovery.',
        'connection': f'Picture {route} leading into a garden where every lantern carries a kind word. In this fictional chapter, a little conversation and a thoughtful gesture become the story’s brightest treasures.',
        'purpose': f'Imagine {route} ending at a quiet workshop filled with unfinished sketches. In this invented chapter, you choose one small creative project and give it patient attention. The adventure is in making, learning, and trying again.'}
    result = {
        'mode': 'local-story', 'title': title, 'notice': NOTICE,
        'theme': theme, 'choices': choices,
        'basis': f'Your photo session contains {counts["left"]} left-image and {counts["right"]} right-image candidate segments. They are not verified named palm lines. The story uses your chosen theme and optional manual symbols, not a forecast inferred from your images.',
        'chapters': [
            {'title': 'Your imagined next chapter', 'body': openers[theme]},
            {'title': 'A symbol to carry', 'body': 'In palmistry folklore, the heart represents connection, the head imagination, and fate direction. Borrow these as story symbols: a warm conversation, an interesting question, and a path you are free to choose. They do not establish your personality or future.'},
            {'title': 'A playful invitation', 'body': f'For a tiny real-world creative exercise, write one sentence about {mood}, or choose a harmless activity that fits the theme. Treat it as a story prompt, not advice from your palm.'}
        ], 'sources': citation_set(kb)
    }
    if provider_name() == 'demo':
        return result
    prompt = {'theme': mood, 'manual_storytelling_symbols': choices,
              'verified_named_palm_lines': [], 'image_candidate_counts': counts,
              'curated_cultural_notes': kb}
    system = (
        'Write a magical, playful palmistry-inspired FICTIONAL story for an entertainment feature. '
        'Begin each story in an imagined setting and use conditional or imaginative language. '
        'Manual line choices are user-selected storytelling prompts, not verified observations. '
        'Candidate image segments do not establish named palm lines. Do not claim to read the future '
        'or infer personality, health, lifespan, wealth, relationships, or employment outcomes. '
        'Do not give dates, guarantees, ominous warnings, diagnoses, or consequential advice. '
        'Return JSON with title (string) and chapters (exactly 3 objects with string title and body). '
        'Each body must be under 100 words. No markdown. '+NOTICE)
    try:
        raw = _invoke(system, json.dumps(prompt))
        if not isinstance(raw, str):
            raise ValueError('Empty provider response')
        parsed = json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())
        chapters = parsed.get('chapters')
        if not isinstance(parsed.get('title'), str) or not 1 <= len(parsed['title']) <= 160:
            raise ValueError('Invalid title')
        if not isinstance(chapters,list) or len(chapters)!=3:
            raise ValueError('Invalid chapters')
        if not all(isinstance(c,dict) and isinstance(c.get('title'),str) and 1<=len(c['title'])<=160
                   and isinstance(c.get('body'),str) and 1<=len(c['body'])<=1000 for c in chapters):
            raise ValueError('Invalid chapter content')
        result.update(title=parsed['title'], chapters=[{'title':c['title'],'body':c['body']} for c in chapters], mode=provider_name())
    except Exception:
        result['mode']='local-story-fallback'
        result['provider_note']='Live AI was unavailable or returned an invalid story. A local authored story is shown instead.'
    return result
