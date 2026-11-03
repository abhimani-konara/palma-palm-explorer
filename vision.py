"""Transparent OpenCV imaging pipeline. Palm-line classifications are CANDIDATES only.

MediaPipe (if installed) helps localize the hand; it does not name palm creases.
No simulated detection is reported as a certain observed feature.
"""
import base64
import math
from io import BytesIO
import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    import mediapipe as mp
    _MP_HANDS = getattr(getattr(mp, 'solutions', None), 'hands', None)
except (ImportError, AttributeError, OSError):
    _MP_HANDS = None

MAX_PIXELS = 16_000_000
MAX_SIDE = 1100


def parse_image(data, name='image'):
    try:
        pil = Image.open(BytesIO(data))
        if pil.format not in {'JPEG','PNG'}:
            raise ValueError(f'{name}: Please upload JPG, JPEG or PNG only.')
        if pil.width * pil.height > MAX_PIXELS:
            raise ValueError(f'{name}: Image is too large (maximum 16 megapixels).')
        if pil.width < 240 or pil.height < 240:
            raise ValueError(f'{name}: Image resolution is too low. Use at least 240 × 240 pixels; 720p or better is recommended.')
        pil = ImageOps.exif_transpose(pil).convert('RGB')
        pil.thumbnail((MAX_SIDE,MAX_SIDE), Image.Resampling.LANCZOS)
        return cv2.cvtColor(np.array(pil),cv2.COLOR_RGB2BGR)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f'{name}: Unable to read the image. Upload an uncorrupted JPEG or PNG.') from e


def encoded(image, max_side=960, quality=86):
    h,w=image.shape[:2]
    if max(h,w)>max_side:
        scale=max_side/max(h,w)
        image=cv2.resize(image,(int(w*scale),int(h*scale)))
    ok,buf=cv2.imencode('.jpg',image,[int(cv2.IMWRITE_JPEG_QUALITY),quality])
    return 'data:image/jpeg;base64,'+base64.b64encode(buf.tobytes()).decode('ascii') if ok else ''


def _landmarks(image):
    if _MP_HANDS is None: return None
    try:
        rgb=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
        with _MP_HANDS.Hands(static_image_mode=True,max_num_hands=1,min_detection_confidence=0.55) as hands:
            found=hands.process(rgb)
            if not found.multi_hand_landmarks:return None
            h,w=image.shape[:2]
            return np.array([[int(p.x*w),int(p.y*h)] for p in found.multi_hand_landmarks[0].landmark],dtype=np.int32)
    except Exception:
        return None


def _roi_mask(img, points):
    h,w=img.shape[:2]
    mask=np.zeros((h,w),dtype=np.uint8)
    if points is not None:
        # MCPs + palm edge landmarks form a rough, inner-palm polygon; fingers excluded.
        ids=[0,1,2,5,9,13,17]
        poly=points[ids]
        cv2.fillConvexPoly(mask,cv2.convexHull(poly),255)
        kernel=np.ones((13,13),np.uint8)
        mask=cv2.erode(mask,kernel,iterations=1)
        return mask,'MediaPipe hand landmarks',True
    # No landmark detector: do not claim hand verification. Approximate central-palm region.
    # Location is a guide for visual edge analysis only, never a validated palm bounding box.
    x1,x2=int(w*.22),int(w*.78)
    y1,y2=int(h*.32),int(h*.79)
    cv2.ellipse(mask,(w//2,int(h*.54)),(int(w*.29),int(h*.29)),0,0,360,255,-1)
    return mask,'unverified central image region',False


def _line_candidates(edges,mask):
    if not np.any(mask):return []
    h,w=edges.shape
    min_len=int(min(h,w)*0.12)
    detected=cv2.HoughLinesP(cv2.bitwise_and(edges,edges,mask=mask), 1,np.pi/180,
                             threshold=max(16,int(min(h,w)*.028)), minLineLength=min_len,
                             maxLineGap=max(8,int(w*.025)))
    if detected is None:return []
    candidates=[]
    for packed in np.asarray(detected).reshape(-1,4)[:180]:
        x1,y1,x2,y2=(int(a) for a in packed);dx=x2-x1;dy=y2-y1
        length=math.hypot(dx,dy)
        if length<min_len:continue
        angle=abs(math.degrees(math.atan2(dy,dx)))
        my=(y1+y2)/(2*h);mx=(x1+x2)/(2*w)
        if (angle<40 or angle>140) and .34<my<.55:
            label='Upper transverse crease';traditional='heart'
        elif (angle<48 or angle>132) and .48<my<.72:
            label='Middle transverse crease';traditional='head'
        elif 48<angle<132 and .42<mx<.65:
            label='Longitudinal crease';traditional='fate'
        elif 40<angle<142 and (.22<mx<.46 or .57<mx<.78):
            label='Curving-side crease';traditional='life'
        else:continue
        candidates.append({'key':traditional,'label':label,'points':(x1,y1,x2,y2),
                           'length':round(length/max(h,w),3),'confidence':'low',
                           'status':'visual candidate only'})
    selected=[]
    for key in ['heart','head','life','fate']:
        options=sorted((x for x in candidates if x['key']==key),key=lambda x:x['length'],reverse=True)
        if options:selected.append(options[0])
    return selected


def analyze(data,hand):
    img=parse_image(data,hand)
    h,w=img.shape[:2]
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    variance=float(cv2.Laplacian(gray,cv2.CV_64F).var())
    brightness=float(np.mean(gray))
    contrast=float(np.std(gray))
    warnings=[]
    if variance<32:warnings.append('Possible blur detected; use a sharp, well-focused photograph.')
    if brightness<55:warnings.append('Image appears dark; use more even lighting.')
    if brightness>220:warnings.append('Image appears overexposed; reduce glare.')
    if contrast<24:warnings.append('Low contrast; stronger, even lighting may help.')
    if min(h,w)<480:warnings.append('Higher resolution recommended for analyzing fine palm creases.')
    if max(h,w)/min(h,w)>2.2:warnings.append('Unusual image aspect ratio; ensure the full palm and fingertips are visible.')
    resized=img.copy()                           # 1 resize & normalize via parse_image
    denoised=cv2.GaussianBlur(gray,(5,5),0)       # 2 smoothing
    clahe=cv2.createCLAHE(clipLimit=2.3,tileGridSize=(8,8)).apply(denoised) # 3 contrast
    edges=cv2.Canny(clahe,45,110)                # 4 edge detection
    _,threshold=cv2.threshold(clahe,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU) # 5 thresholding
    morph=cv2.morphologyEx(edges,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8)) # 6 morphology
    landmarks=_landmarks(img)
    mask,region_source,verified=_roi_mask(img,landmarks)
    palm_shape={'status':'unverified','description':'Palm shape not measured without reliable hand landmarks.'}
    if landmarks is not None:
        # Coarse geometric evidence only: palm width across index/pinky knuckles
        # compared with wrist to middle-finger knuckle. Not a palmistry type.
        palm_width=float(np.linalg.norm(landmarks[5]-landmarks[17]))
        palm_length=float(np.linalg.norm(landmarks[0]-landmarks[9]))
        if palm_width>8 and palm_length>8:
            ratio=round(palm_length/palm_width,2)
            palm_shape={'status':'geometric estimate','length_to_width_ratio':ratio,
                        'description':'Approximate wrist-to-middle-knuckle distance divided by index-to-pinky-knuckle distance; not a traditional palm-shape classification.'}
        border_margin=max(9,int(min(w,h)*.025))
        tips=landmarks[[4,8,12,16,20]]
        if np.any(tips[:,0]<border_margin) or np.any(tips[:,0]>w-border_margin) or np.any(tips[:,1]<border_margin) or np.any(tips[:,1]>h-border_margin):
            warnings.append('One or more fingertips may be cut off or too close to the edge; reframe the complete hand.')
    if not verified:
        warnings.append('Hand detection not verified. Install optional MediaPipe or use a palm-centered photo; positions are only exploratory.')
    candidates=_line_candidates(morph,mask)
    if not candidates:warnings.append('No reliable-looking crease candidates found; do not interpret absent features.')
    colors={'heart':(102,165,246),'head':(38,211,230),'life':(105,191,144),'fate':(214,130,244)}
    overlay=img.copy()
    # Draw actual detected edge pixels in a subtle copper color; do not fabricate named lines.
    edge_pixels=(morph>0)&(mask>0)
    overlay[edge_pixels]=(0.45*overlay[edge_pixels]+0.55*np.array([72,150,238])).astype(np.uint8)
    for candidate in candidates:
        x1,y1,x2,y2=candidate['points'];color=colors[candidate['key']]
        cv2.line(overlay,(x1,y1),(x2,y2),color,3,cv2.LINE_AA)
        caption=candidate['label']+' ?'
        tx=max(5,min(w-225,x1));ty=max(18,min(h-5,y1-12))
        cv2.putText(overlay,caption,(tx,ty),cv2.FONT_HERSHEY_SIMPLEX,.50,color,2,cv2.LINE_AA)
    if landmarks is not None:
        for p in landmarks[[0,5,9,13,17]]:
            cv2.circle(overlay,(int(p[0]),int(p[1])),4,(46,182,249),-1)
    cv2.putText(overlay,'CANDIDATES ONLY - NOT VERIFIED PALMISTRY LINES',(12,h-17),
                cv2.FONT_HERSHEY_SIMPLEX,max(.33,min(w/900,.55)),(80,190,246),2,cv2.LINE_AA)
    return {
        'hand':hand,'dimensions':{'width':w,'height':h},
        'quality':{'sharpness_laplacian':round(variance,1),'brightness':round(brightness,1),
                   'contrast_std':round(contrast,1),'warnings':warnings},
        'region_source':region_source,'hand_landmarks_verified':verified, 'palm_shape':palm_shape,
        'features':[{'name':x['label'],'traditional_association':x['key'],
                     'status':x['status'],'confidence':x['confidence'],
                     'relative_length':x['length']} for x in candidates],
        'images':{
            'original':encoded(resized),
            'grayscale':encoded(cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR)),
            'gaussian':encoded(cv2.cvtColor(denoised,cv2.COLOR_GRAY2BGR)),
            'clahe':encoded(cv2.cvtColor(clahe,cv2.COLOR_GRAY2BGR)),
            'edges':encoded(cv2.cvtColor(edges,cv2.COLOR_GRAY2BGR)),
            'threshold':encoded(cv2.cvtColor(threshold,cv2.COLOR_GRAY2BGR)),
            'morphology':encoded(cv2.cvtColor(morph,cv2.COLOR_GRAY2BGR)),
            'annotated':encoded(overlay),
        }
    }
