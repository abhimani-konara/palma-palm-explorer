"""LineLens — NIBM ICA01 two-palm imaging, traditional narrative and chatbot demonstration."""
import os
import re
import secrets
import time
from collections import OrderedDict
from flask import Flask, jsonify, render_template, request, send_from_directory
from dotenv import load_dotenv
from vision import analyze
from llm import build_report, answer, provider_name

load_dotenv()
app=Flask(__name__, static_folder='dist', static_url_path='')
app.config['MAX_CONTENT_LENGTH']=int(os.getenv('MAX_UPLOAD_MB','8'))*1024*1024*2
app.config['SECRET_KEY']=os.getenv('SECRET_KEY') or secrets.token_hex(24)
app.json.ensure_ascii=False
CACHE=OrderedDict()
SESSION_TTL=3600

def expire_sessions():
    cutoff=time.time()-SESSION_TTL
    for key in list(CACHE):
        if CACHE[key]['created']<cutoff:CACHE.pop(key,None)
MAX_SCANS=18

@app.get('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.get('/api/status')
def status():
    return jsonify({'ok':True,'app':'LineLens Palm Vision Studio','provider':provider_name(),
        'ai_enabled':provider_name()!='demo','save_uploads':False,'requires_two_palms':True,'session_ttl_seconds':SESSION_TTL})

@app.post('/api/analyze')
def analyze_route():
    expire_sessions()
    try:
        if 'left' not in request.files or 'right' not in request.files:
            return jsonify(error='Please upload separate photographs of your LEFT and RIGHT palms.'),400
        results={}
        for side in ('left','right'):
            file=request.files[side]
            if not file.filename:return jsonify(error=f'Please select a {side} palm image.'),400
            if not re.search(r'\.(jpe?g|png)$',file.filename,re.I):
                return jsonify(error=f'{side.title()} palm: use .jpg, .jpeg or .png files.'),400
            data=file.read(8*1024*1024+1)
            if len(data)>8*1024*1024:return jsonify(error=f'{side.title()} palm image exceeds the 8MB per-file limit.'),413
            results[side]=analyze(data,side)
            q=results[side]['quality']
            if q['sharpness_laplacian']<5 or q['brightness']<15 or q['brightness']>246:
                return jsonify(error=f'{side.title()} image quality is unsuitable. Re-take the picture sharply in even light and upload again.',
                    detail=q['warnings']),422
        report=build_report(results)
        scan_id=secrets.token_urlsafe(20)
        # Only compact feature records are cached. The image content is NOT retained server-side.
        records={s:{k:v for k,v in r.items() if k!='images'} for s,r in results.items()}
        CACHE[scan_id]={'created':time.time(),'features':records,'report':report}
        CACHE.move_to_end(scan_id)
        while len(CACHE)>MAX_SCANS:CACHE.popitem(last=False)
        return jsonify({'ok':True,'scan_id':scan_id,'hands':results,'report':report})
    except ValueError as error:
        return jsonify(error=str(error)),400
    except Exception:
        app.logger.exception('Unexpected scan failure')
        return jsonify(error='Image processing failed. Check both photos and try again.'),500

@app.post('/api/chat')
def chat_route():
    expire_sessions()
    data=request.get_json(silent=True) or {}
    sid=data.get('scan_id','')
    message=str(data.get('message','')).strip()
    if sid not in CACHE:return jsonify(error='Scan not found or session expired. Please analyze both palms first.'),404
    if not message:return jsonify(error='Please enter a question.'),400
    if len(message)>1200:return jsonify(error='Please keep questions under 1,200 characters.'),400
    item=CACHE[sid]
    history=data.get('history',[])
    if not isinstance(history,list):history=[]
    safe_history=[{'role':h.get('role','user'),'content':str(h.get('content',''))[:1000]}
                  for h in history[-8:] if isinstance(h,dict) and h.get('role') in {'user','assistant'}]
    return jsonify({'ok':True,**answer(message,item['features'],item['report'],safe_history)})

@app.post('/api/session/clear')
def clear_session():
    data=request.get_json(silent=True) or {}
    CACHE.pop(str(data.get('scan_id','')),None)
    return jsonify(ok=True)

@app.errorhandler(413)
def too_big(_):return jsonify(error='Files are too large. Use JPG or PNG images under 8MB each.'),413

@app.after_request
def headers(resp):
    resp.headers['X-Content-Type-Options']='nosniff'
    resp.headers['X-Frame-Options']='DENY'
    resp.headers['Referrer-Policy']='no-referrer'
    return resp

if __name__=='__main__':
    app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
