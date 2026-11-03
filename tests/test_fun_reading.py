import sys,types,unittest,time
from unittest.mock import patch
with patch.dict(sys.modules, {'vision':types.SimpleNamespace(analyze=lambda *args:None)}):
 import app
import fun_reading

class FunReadingTests(unittest.TestCase):
 def setUp(self):
  self.client=app.app.test_client();app.CACHE.clear()
  self.analysis={'left':{'features':[{'traditional_association':'head','confidence':'low'}]},'right':{'features':[]}}
  app.CACHE['test-scan']={'created':time.time(),'features':self.analysis,'report':{}}
 def test_story_has_explicit_entertainment_label_and_actual_counts(self):
  with patch('fun_reading.provider_name',return_value='demo'):
   r=self.client.post('/api/fun-reading',json={'scan_id':'test-scan','theme':'connection','choices':{'heart':'curved'}})
  self.assertEqual(r.status_code,200);s=r.json['story'];self.assertEqual(s['mode'],'local-story');self.assertEqual(len(s['chapters']),3)
  self.assertIn('not a factual prediction',s['notice']);self.assertIn('1 left-image and 0 right-image',s['basis']);self.assertEqual(s['choices']['head'],'unknown')
 def test_full_reading_covers_requested_topics_and_no_marriage_age(self):
  with patch('fun_reading.provider_name',return_value='demo'):
   r=self.client.post('/api/fun-reading',json={'scan_id':'test-scan','theme':'full','choices':{}})
  self.assertEqual(r.status_code,200)
  cards=r.json['story']['chapters']
  self.assertEqual([c['title'] for c in cards],['Love & relationships','Marriage & commitment','Career & ambitions','Future possibilities','Marriage age & timing'])
  self.assertIn('No age, year, or timeline is calculated',cards[-1]['body'])
 def test_each_focused_topic_produces_three_sections(self):
  for theme in ['relationships','marriage','career','future']:
   with patch('fun_reading.provider_name',return_value='demo'):
    story=fun_reading.build_fun_reading(self.analysis,theme,{'heart':'curved'})
   self.assertEqual(len(story['chapters']),3)
   self.assertTrue(all(c['title'] and c['body'] for c in story['chapters']))
 def test_no_scan_and_expired_scan_cannot_generate(self):
  self.assertEqual(self.client.post('/api/fun-reading',json={'scan_id':'missing'}).status_code,404)
  app.CACHE['test-scan']['created']=0
  self.assertEqual(self.client.post('/api/fun-reading',json={'scan_id':'test-scan'}).status_code,404)
 def test_rejects_invalid_input(self):
  for payload in [[],{'scan_id':[]},{'scan_id':'test-scan','theme':'guaranteed-wealth'},{'scan_id':'test-scan','choices':{'heart':'diagnosis'}},{'scan_id':'test-scan','choices':{'injected':'curved'}}]:
   self.assertIn(self.client.post('/api/fun-reading',json=payload).status_code,(400,404))
 def test_provider_failure_and_bad_schema_fall_back_honestly(self):
  for raw in ['not json','{"title":"X","chapters":[]}']:
   with patch('fun_reading.provider_name',return_value='gemini'),patch('fun_reading._invoke',return_value=raw):
    r=fun_reading.build_fun_reading(self.analysis)
   self.assertEqual(r['mode'],'local-story-fallback');self.assertIn('local authored story',r['provider_note'])
 def test_provider_context_excludes_raw_photos(self):
  self.analysis['left']['images']={'original':'PRIVATE_IMAGE_SENTINEL'}
  raw='{"title":"An imagined garden","chapters":[{"title":"One","body":"Imagine a lantern."},{"title":"Two","body":"Picture a garden."},{"title":"Three","body":"Choose a creative prompt."}]}'
  with patch('fun_reading.provider_name',return_value='gemini'),patch('fun_reading._invoke',return_value=raw) as invoke:
   r=fun_reading.build_fun_reading(self.analysis,'adventure',{})
  self.assertEqual(r['mode'],'gemini');self.assertNotIn('PRIVATE_IMAGE_SENTINEL',str(invoke.call_args));self.assertIn('FICTIONAL',invoke.call_args.args[0])
 def test_clearing_session_prevents_story_generation(self):
  self.client.post('/api/session/clear',json={'scan_id':'test-scan'})
  self.assertEqual(self.client.post('/api/fun-reading',json={'scan_id':'test-scan'}).status_code,404)

if __name__ == '__main__':
 unittest.main(verbosity=2)
