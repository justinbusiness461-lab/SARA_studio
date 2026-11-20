"""Owner-disjoint Sample Lab and compound intent integration against real Studio HTTP auth."""
import base64,hashlib,io,unittest,wave
import test_m045_wave3_service as wave3
import studio_server as studio
from m045_wave4_service import authorized_compound_plan,authorized_sample_transform

class CompoundSampleHTTP(unittest.TestCase):
 setUp=wave3.Wave3HTTPTests.setUp
 tearDown=wave3.Wave3HTTPTests.tearDown
 request=wave3.Wave3HTTPTests.request
 def test_sample_preview_is_bound_unpublished_and_auth_checked(self):
  body={'projectId':self.pid,'revisionId':self.rid,'artifactId':self.digest,'transform':'slice','parameters':{'startFrame':0,'endFrame':120}}
  code,r=self.request('/api/m045/sample-preview',body,session=self.session)
  self.assertEqual(code,200,r)
  data=base64.b64decode(r['wavBase64']);self.assertEqual(hashlib.sha256(data).hexdigest(),r['previewArtifactSha256'])
  with wave.open(io.BytesIO(data),'rb') as w:self.assertEqual(w.getnframes(),120)
  self.assertFalse(r['projectRevisionCommitted']);self.assertEqual(r['audioPublication'],'NONE')
  self.assertEqual(r['provenance']['rights_status'],'UNVERIFIED_HELD')
  self.assertEqual(studio.project_operation(self.root,{'projectId':self.pid})['manifest']['currentRevisionId'],self.before)
  self.assertEqual(self.request('/api/m045/sample-preview',body)[0],403)
  foreign=studio.issue_studio_session('foreign-principal');self.assertEqual(self.request('/api/m045/sample-preview',body,session=foreign)[0],403)
  orphan=hashlib.sha256(b'unbound').hexdigest();self.assertEqual(self.request('/api/m045/sample-preview',{**body,'artifactId':orphan},session=self.session)[0],403)
 def test_compound_plan_is_source_bound_and_no_commit(self):
  body={'projectId':self.pid,'revisionId':self.rid,'instruction':'darken bass'}
  code,r=self.request('/api/m045/compound-plan',body,session=self.session)
  self.assertEqual(code,200,r);self.assertEqual(r['operations'][0]['kind'],'filter')
  self.assertFalse(r['revisionCommitted']);self.assertEqual(r['sourceRevisionId'],self.rid)
  self.assertEqual(studio.project_operation(self.root,{'projectId':self.pid})['manifest']['currentRevisionId'],self.before)
  self.assertEqual(self.request('/api/m045/compound-plan',{**body,'instruction':'change everything'},session=self.session)[0],400)
  self.assertEqual(self.request('/api/m045/compound-plan',body)[0],403)

if __name__=='__main__':unittest.main()