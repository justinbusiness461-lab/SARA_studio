"""R25 RED: distinct host-attested 19s S15 + 20s pilot, fail-closed others."""
import hashlib, io, unittest, wave
from m045_soundtrack_grant import HostSigningKeyRing, GrantIssuerDenied, issue_authorized_grant, verify_issued_grant_signature
RATE=44100
class ExactPilot(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  s=io.BytesIO()
  with wave.open(s,'wb') as w:
   w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(b'\0\0\0\0'*(273*RATE))
  cls.audio=s.getvalue();cls.aid=hashlib.sha256(cls.audio).hexdigest()
 def test_19s_and_20s_same_source_stable_mapping(self):
  sections=[{'id':'s15','sample_rate':RATE,'start_sample':229*RATE,'end_sample_exclusive':248*RATE},{'id':'pilot20','sample_rate':RATE,'start_sample':252*RATE,'end_sample_exclusive':272*RATE}]
  ring=HostSigningKeyRing('staging',{'staging':b'R'*32},frozenset())
  rights={'rights_status':'UNVERIFIED_HELD','private_pilot_authorized':True,'principal_id':'artist','revision_id':'a'*64,'artifact_id':self.aid,'cinema_project_id':'private','approved_sections':{s['id']:{'start_sample':s['start_sample'],'end_sample_exclusive':s['end_sample_exclusive']} for s in sections}}
  def invoke(sid):
   return issue_authorized_grant(root='fixture',request={'projectId':'1'*32,'revisionId':'a'*64,'artifactId':self.aid,'cinemaProjectId':'private','sectionId':sid,'fps':'24/1','scope':'private_cinema_pilot'},principal_id='artist',ring=ring,read_project=lambda *a,**kw:{'manifest':{'projectId':'1'*32},'revision':{'projectId':'1'*32,'revisionId':'a'*64},'productionTimeline':{'timebase':{'initial_bpm':120,'ticks_per_quarter_note':960},'sections':sections}},read_audio=lambda *a,**kw:self.audio,rights_policy=lambda *a:rights,now=1840000000)
  one=invoke('s15');two=invoke('pilot20')
  self.assertEqual((one['resolved_start_sample'],one['resolved_end_sample_exclusive'],one['resolved_start_frame'],one['resolved_end_frame_exclusive']),(10098900,10936800,5496,5952))
  self.assertEqual((two['resolved_start_sample'],two['resolved_end_sample_exclusive'],two['resolved_start_frame'],two['resolved_end_frame_exclusive']),(11113200,11995200,6048,6528))
  self.assertTrue(verify_issued_grant_signature(one,ring));self.assertTrue(verify_issued_grant_signature(two,ring))
  for secs in (18,21):
   sections[0]['end_sample_exclusive']=(229+secs)*RATE
   rights['approved_sections']['s15']['end_sample_exclusive']=(229+secs)*RATE
   with self.assertRaises(GrantIssuerDenied):invoke('s15')

class HostMultiWindowIngestion(unittest.TestCase):
 def test_host_attested_19s_plus_20s_persist_in_exact_canonical_timeline(self):
  import hashlib,tempfile,struct
  from pathlib import Path
  from m045_artist_master_ingestion import ingest_original_master
  from studio_server import project_operation
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'root';source=Path(t)/'synthetic.wav'
   with wave.open(str(source),'wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
    w.writeframes(struct.pack('<hh',500,-500)*(39*44100))
   digest=hashlib.sha256(source.read_bytes()).hexdigest()
   catalog={'title':'Turn The Noise Back On','principalId':'staging','sourceSha256':digest,'projectId':'3'*32,'rightsEvidenceSha256':'c'*64,'rightsStatus':'UNVERIFIED_HELD','privatePilotAuthorized':True,'commercialReleaseAuthorized':False,'pilotSections':[{'id':'s15','sampleRate':44100,'startSample':0,'endSampleExclusive':19*44100},{'id':'pilot20','sampleRate':44100,'startSample':19*44100,'endSampleExclusive':39*44100}]}
   record=ingest_original_master(root=root,principal_id='staging',title=catalog['title'],source_path=source,host_catalog_lookup=lambda *args:catalog)
   opened=project_operation(root,{'projectId':record['projectId']},principal_id='staging')
   self.assertEqual(len(opened['productionTimeline']['sections']),2)
   self.assertEqual(opened['productionTimeline']['sections'][0]['end_sample_exclusive'],19*44100)
   self.assertEqual(opened['productionTimeline']['sections'][1]['end_sample_exclusive'],39*44100)
   self.assertFalse(record['commercialReleaseAuthorized'])
   self.assertEqual(record['decoded48000Frames'],39*48000)
   self.assertEqual(record['decoded44100Frames'],39*44100)
   self.assertNotEqual(record['decoded48000PcmSha256'],record['decoded44100PcmSha256'])