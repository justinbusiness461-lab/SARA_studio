"""R11-B RED: compare untrusted archive against canonical immutable owner output."""
import base64,io,json,unittest,zipfile
from test_m045_daw_export import DawHttp
from m045_daw_export import verify_authorized_daw_bundle

class DawVerifier(unittest.TestCase):
 def setUp(self):
  self.fx=DawHttp('test_bundle_revision_stems_midi_musicxml_and_checksum_identity');self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.fx.build_canonical_mix()
  self.status,_,self.data=self.fx.request_bundle()
  self.assertEqual(self.status,200)
 def test_genuine_archive_roundtrip_auth_and_receipt(self):
  status,_,response=self.fx.fx.api('/api/m045/verify-daw-bundle',{
    **self.fx.request,'archiveBase64':base64.b64encode(self.data).decode()},cookie=self.fx.cookie)
  self.assertEqual(status,200,response)
  self.assertEqual(response['state'],'VERIFIED_UNMODIFIED_BUNDLE')
  self.assertEqual(response['masterArtifactId'],self.fx.request['artifactId'])
  self.assertFalse(response['importCommitted'])
 def test_foreign_principal_and_tampered_bundle_rejected(self):
  self.assertEqual(self.fx.fx.api('/api/m045/verify-daw-bundle',{
    **self.fx.request,'archiveBase64':base64.b64encode(self.data).decode()})[0],403)
  damaged=bytearray(self.data);damaged[300]^=3
  status,_,_=self.fx.fx.api('/api/m045/verify-daw-bundle',{
    **self.fx.request,'archiveBase64':base64.b64encode(damaged).decode()},cookie=self.fx.cookie)
  self.assertEqual(status,409)
 def test_arbitrary_zip_not_accepted_as_authority(self):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:z.writestr('daw_manifest.json',json.dumps({'schema':'sara.daw.bundle.v1'}))
  status,_,_=self.fx.fx.api('/api/m045/verify-daw-bundle',{
    **self.fx.request,'archiveBase64':base64.b64encode(out.getvalue()).decode()},cookie=self.fx.cookie)
  self.assertEqual(status,409)
if __name__=='__main__':unittest.main()
