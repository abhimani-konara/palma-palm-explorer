"""Playful, explicitly fictional palmistry stories; separate from image evidence."""
import json
from llm import _invoke, provider_name
from knowledge import retrieve, citation_set

NOTICE = 'For fun only — inspired by traditional palmistry, not a factual prediction.'
THEMES = {
    'full': ('Your symbolic palmistry reading', 'love, marriage, career, and future possibilities'),
    'relationships': ('Love & relationships', 'love and relationships'),
    'marriage': ('Marriage & commitment', 'marriage and commitment, without predicted ages or dates'),
    'career': ('Career & ambitions', 'career symbolism and ambitions'),
    'future': ('Future possibilities', 'open-ended future possibilities'),
    'adventure': ('Adventure & possibilities', 'curiosity and new experiences'),
    'connection': ('Love & relationships', 'love and relationships'),
    'purpose': ('Career & ambitions', 'creativity and purpose')
}
SHAPES = {'unknown', 'curved', 'straight', 'not-visible'}
KEYS = ('heart', 'head', 'life', 'fate')

def validate_choices(theme, choices):
    if theme not in THEMES:
        raise ValueError('Choose one of the available reading topics.')
    if not isinstance(choices, dict) or any(k not in KEYS or v not in SHAPES for k,v in choices.items()):
        raise ValueError('Invalid symbolic line choices.')
    return {key: choices.get(key, 'unknown') for key in KEYS}

def reading_chapters(theme, choices):
    heart = choices.get('heart', 'unknown')
    heart_metaphor = (
        'For this playful reading, your curved-symbol choice becomes a metaphor for warmth and openness.'
        if heart == 'curved' else
        'For this playful reading, your straight-symbol choice becomes a metaphor for steadiness and clear communication.'
        if heart == 'straight' else
        'No heart-line shape was selected, so this is general symbolism rather than an interpretation of an observed line.')
    deck = {
        'relationships': {'title': 'Love & relationships', 'body':
            'The traditional heart-line theme invites a reflection on affection, trust, and emotional connection. '
            + heart_metaphor + ' It does not establish your feelings or what another person will do.'},
        'marriage': {'title': 'Marriage & commitment', 'body':
            'In this for-fun reading, partnership is imagined as a shared path: companionship, mutual choice, and growing together. '
            'No marriage or union line has been verified in your photographs. These themes do not establish whether you will marry or how a partnership will turn out.'},
        'career': {'title': 'Career & ambitions', 'body':
            'The head and fate symbols become a playful lens for curiosity, creative effort, and finding direction. '
            'Imagine this as a chapter of exploring skills and possibilities. It is not a forecast of a job offer, income, promotion, or a career suited to your personality.'},
        'future': {'title': 'Future possibilities', 'body':
            'The symbolic horizon stays open: new interests, changing plans, and opportunities you might choose to explore. '
            'Read it as a palmistry-inspired reflection on possibilities, not events that your hand says will happen.'},
        'timing': {'title': 'Marriage age & timing', 'body':
            'A palm photograph cannot establish a marriage age or date. No age, year, or timeline is calculated by this feature. '
            'Timing remains open in this entertainment reading.'},
        'symbols': {'title': 'Your symbolic reflection', 'body':
            'Heart, head, life, and fate are used here as creative symbols for connection, imagination, experience, and direction. '
            'Your optional manual choices guide the wording, but neither those choices nor the image candidates verify a prediction.'}
    }
    if theme == 'full':
        keys = ['relationships', 'marriage', 'career', 'future', 'timing']
    else:
        topic = {'connection':'relationships','purpose':'career','adventure':'future'}.get(theme, theme)
        keys = [topic, 'symbols', 'timing' if topic == 'marriage' else 'future' if topic != 'future' else 'relationships']
    return [dict(deck[key]) for key in keys]

def build_fun_reading(analysis, theme='adventure', choices=None):
    choices = validate_choices(theme, choices if choices is not None else {})
    title, mood = THEMES[theme]
    counts = {side: len((analysis.get(side) or {}).get('features', [])) for side in ('left','right')}
    selected = [key for key, shape in choices.items() if shape in ('curved','straight')]
    kb = retrieve(' '.join(selected or ['heart','head','fate'])+' '+theme, k=4)
    result = {
        'mode': 'local-story', 'title': title, 'notice': NOTICE,
        'theme': theme, 'choices': choices,
        'basis': f'Your photo session contains {counts["left"]} left-image and {counts["right"]} right-image candidate segments. They are not verified named palm lines. This entertainment reading uses your chosen topics and optional manual symbols, not a forecast inferred from your images.',
        'chapters': reading_chapters(theme, choices), 'sources': citation_set(kb)
    }
    if provider_name() == 'demo':
        return result
    prompt = {'theme': mood, 'manual_storytelling_symbols': choices,
              'verified_named_palm_lines': [], 'image_candidate_counts': counts,
              'curated_cultural_notes': kb,
              'required_section_titles': [c['title'] for c in result['chapters']]}
    system = (
        'Write a warm palmistry-style symbolic entertainment reading, rather than a scene-based fantasy story. '
        'Its framing must remain FICTIONAL and for fun, not factual prediction. '
        'Cover only the requested section topics, in the order of required_section_titles. '
        'Discuss love, relationships, marriage/commitment, career symbolism, and future possibilities as relevant. '
        'Manual line choices are storytelling prompts, not verified observations. '
        'Never claim an unverified named line was detected or infer actual personality, health, lifespan, '
        'wealth, relationship outcomes, or employment outcomes. '
        'For marriage age and timing, explicitly say that no age or date can be inferred; never invent one. '
        'Use conditional symbolic language, without guarantees, diagnoses, ominous warnings, or consequential advice. '
        f'Return JSON with title (string) and chapters (exactly {len(result["chapters"])} objects with string title and body). '
        'Each body must be under 100 words. No markdown. '+NOTICE)
    try:
        raw = _invoke(system, json.dumps(prompt))
        if not isinstance(raw, str):
            raise ValueError('Empty provider response')
        parsed = json.loads(raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())
        chapters = parsed.get('chapters')
        if not isinstance(parsed.get('title'), str) or not 1 <= len(parsed['title']) <= 160:
            raise ValueError('Invalid title')
        if not isinstance(chapters,list) or len(chapters)!=len(result['chapters']):
            raise ValueError('Invalid chapters')
        if not all(isinstance(c,dict) and isinstance(c.get('title'),str) and 1<=len(c['title'])<=160
                   and isinstance(c.get('body'),str) and 1<=len(c['body'])<=1000 for c in chapters):
            raise ValueError('Invalid chapter content')
        result.update(title=parsed['title'], chapters=[{'title':c['title'],'body':c['body']} for c in chapters], mode=provider_name())
    except Exception:
        result['mode']='local-story-fallback'
        result['provider_note']='Live AI was unavailable or returned an invalid story. A local authored story is shown instead.'
    return result
