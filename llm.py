"""Two optional LLM provider integrations + transparent offline demonstration mode."""
import json
import os
import requests
from knowledge import retrieve, citation_set, KB

DISCLAIMER='Palmistry is a cultural entertainment tradition, not a scientific method. This reading is not a prediction and must not guide medical, financial, employment or relationship decisions.'
TOPICS=[('linework','The language of the lines'),('personality','Personality symbolism'),('career','Career & purpose'),('finance','Prosperity & resources'),('relationships','Emotions & connection'),('future','Future-facing narrative')]


def provider_name():
    choice=os.getenv('LLM_PROVIDER','demo').lower().strip()
    if choice=='gemini' and os.getenv('GEMINI_API_KEY'):return 'gemini'
    if choice=='openai' and os.getenv('OPENAI_API_KEY'):return 'openai'
    return 'demo'


def _invoke(system,user):
    provider=provider_name()
    if provider=='demo':return None
    if provider=='gemini':
        model=os.getenv('GEMINI_MODEL','gemini-2.5-flash')
        response=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
          headers={'x-goog-api-key':os.environ['GEMINI_API_KEY'],'Content-Type':'application/json'},
          json={'systemInstruction':{'parts':[{'text':system}]},'contents':[{'role':'user','parts':[{'text':user}]}],
                'generationConfig':{'temperature':0.5}},timeout=50)
        response.raise_for_status(); data=response.json()
        return ''.join(p.get('text','') for c in data.get('candidates',[]) for p in c.get('content',{}).get('parts',[]))
    response=requests.post('https://api.openai.com/v1/chat/completions',
      headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},
      json={'model':os.getenv('OPENAI_MODEL','gpt-4o-mini'),'temperature':0.5,
            'messages':[{'role':'system','content':system},{'role':'user','content':user}]},timeout=50)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']


def _compact(analysis):
    return {h:{k:v for k,v in details.items() if k!='images'} for h,details in analysis.items()}


def build_report(analysis):
    flattened=' '.join(x['traditional_association'] for a in analysis.values() for x in a['features'])
    kb=retrieve(flattened+' heart head life fate relationships career money future',k=8)
    ctx=_compact(analysis)
    report={
       'mode':provider_name(), 'disclaimer':DISCLAIMER,
       'headline':'Two hands. A story of symbols.',
       'overview':'A cultural palmistry-style reflection grounded in the visible image-processing output. Candidate creases are not confirmed anatomical classifications.',
       'sections':[], 'sources':citation_set(kb),
       'comparison':'', 'uncertainty':'Line candidates are exploratory; true palmistry categories have not been independently validated.'
    }
    counts={side:len(item['features']) for side,item in analysis.items()}
    report['comparison']=(f'The image-processing pipeline marked {counts.get("left",0)} candidate line structures in the left image and '
        f'{counts.get("right",0)} in the right image. Different photo conditions can change these counts; this is not a personality comparison.')
    topics={
      'linework':('A look at the lines','Traditional texts discuss heart, head, life and fate lines as symbols. Image processing highlighted crease-like structures where possible; any specific association is an unverified candidate. Inspect the annotated images before interpreting.'),
      'personality':('Patterns of character','Palmistry literature links line shapes to symbolic personality themes such as reflection, energy and sensitivity. These stories do not establish personal traits.'),
      'career':('Paths and purpose','The fate line is sometimes interpreted as a metaphor for direction and work. Presence or absence cannot predict a career path.'),
      'finance':('Resources and abundance','Prosperity symbolism appears in traditional readings, but palm features reveal nothing reliable about finances or future earnings.'),
      'relationships':('The language of connection','Traditional interpretations associate the heart line with emotions and connection. They cannot determine relationship outcomes.'),
      'future':('A story, not a forecast','Think of the palm as a visual prompt for imagination: the traditional symbols invite reflection, not a claim about what will happen.')
    }
    report['sections']=[{'id':id,'title':title,'body':body,'evidence':'Cultural tradition only; no verified predictive evidence.'}
                        for id,(title,body) in topics.items()]
    if provider_name()=='demo':
        report['overview']='DEMONSTRATION MODE — no AI API configured. The following symbolic text is generated locally from the curated knowledge base and is not a personalized predictive reading.'
        return report
    system=("You write cultural palmistry narratives for a student assignment. Palmistry is NOT scientifically validated. "
            "Never invent or assert that a named line was observed. Actual observations are provided as candidate features ONLY. "
            "Do not infer real health, lifespan, mental state, wealth, career, relationship success or future. "
            "State uncertainty and specify left/right comparisons as visual observations. "
            "Use the supplied curated tradition text, not new unverifiable superstitions. "
            "Return exactly a JSON object with keys headline, overview, comparison, uncertainty, sections; "
            "sections must be an array of 6 objects with keys id, title, body, evidence, with ids linework,personality,career,finance,relationships,future. "
            "Keep body below 80 words per section. No markdown fences. "+DISCLAIMER)
    prompt='VISUAL ANALYSIS DATA:\n'+json.dumps(ctx)+'\nCURATED TRADITIONS:\n'+json.dumps(kb)+'\nWrite a structured, safe palmistry-style reading.'
    try:
        raw=_invoke(system,prompt)
        cleaned=raw.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        ans=json.loads(cleaned)
        if isinstance(ans.get('sections'),list) and len(ans['sections'])==6:
            for key in ['headline','overview','comparison','uncertainty','sections']:
                if key in ans:report[key]=ans[key]
        else: report['mode']='demo-fallback'
    except Exception as exc:
        report['mode']='demo-fallback'
        report['api_note']='Live AI was unavailable; local curated content was substituted. '+type(exc).__name__
    return report


def answer(question,analysis,report,history):
    kb=retrieve(question,k=4)
    refs=citation_set(kb)
    ctx={'features':_compact(analysis),'report':{k:v for k,v in report.items() if k!='sources'},
         'prior_messages':history[-8:] if isinstance(history,list) else []}
    if provider_name()!='demo':
        system=('You are LineLens AI, a helpful palmistry CULTURAL-ENTERTAINMENT chatbot for an image processing coursework project. '
                'Never claim an undetected feature is visible. Every detected feature has LOW confidence unless evidence states otherwise. '
                'Ground answers in the supplied feature records and curated palmistry snippets. '
                'Never predict health, lifespan, finances, career outcomes, relationships, or future events as facts. '
                'Respond to multiple turns naturally, briefly and warmly, referencing left/right when supported. '
                'Remind users it is cultural entertainment, not scientific advice.')
        try:
            text=_invoke(system,'CONTEXT: '+json.dumps(ctx)+'\nRETRIEVED TRADITIONS: '+json.dumps(kb)+'\nQUESTION: '+str(question)[:1000])
            if text:return {'answer':text,'mode':provider_name(),'sources':refs}
        except Exception:pass
    hits=[x['tradition'] for x in kb[:2]]
    intro='In traditional palmistry, ' if 'palmistry' not in hits[0].lower() else ''
    response=intro+' '.join(hits)
    if any(word in question.lower() for word in ['left','right','compare','difference']):
        response=report['comparison']+' '+response
    return {'answer':response+'\n\n'+DISCLAIMER,'mode':'demo','sources':refs}
