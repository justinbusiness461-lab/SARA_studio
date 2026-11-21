"""R13-C RED: bounded disk-spooled, authority-preserving ZIP upload over HTTP."""
import base64,hashlib,http.client,json,unittest
from test_m045_daw_export import DawHttp
import studio_server as studio

class HttpDawArchiveStream(unittest.TestCase):
    def setUp(self):
        f=DawHttp('test_bundle_revision_stems_midi_musicxml_and_checksum_identity')
        f.setUp();self.addCleanup(f.doCleanups);f.build_canonical_mix()
        status,_,self.archive=f.request_bundle();self.assertEqual(status,200)
        self.fx=f
    def stream(self,data,cookie=True,meta=None):
        header=base64.urlsafe_b64encode(json.dumps(meta if meta is not None else self.fx.request,
            sort_keys=True,separators=(',',':')).encode()).decode().rstrip('=')
        h={'Content-Type':'application/zip','Content-Length':str(len(data)),
           'X-Sara-Daw-Source':header,'X-Studio-Capability':studio.CAPABILITY,
           'Origin':f'http://127.0.0.1:{studio.PORT}'}
        if cookie:h['Cookie']=self.fx.cookie
        con=http.client.HTTPConnection('127.0.0.1',studio.PORT,timeout=45)
        try:
            con.request('POST','/api/m045/verify-daw-bundle',body=data,headers=h)
            response=con.getresponse();return response.status,json.loads(response.read())
        finally:con.close()
    def test_authorized_streamed_archive_proves_canonical_identity(self):
        status,r=self.stream(self.archive)
        self.assertEqual(status,200,r)
        self.assertEqual((r['state'],r['archiveSha256']),('VERIFIED_UNMODIFIED_BUNDLE',hashlib.sha256(self.archive).hexdigest()))
        self.assertFalse(r['newRevisionCommitted'])
    def test_foreign_missing_session_and_tamper_fail_closed(self):
        self.assertEqual(self.stream(self.archive,cookie=False)[0],403)
        damaged=bytearray(self.archive);damaged[len(damaged)//2]^=1
        self.assertEqual(self.stream(damaged)[0],409)
    def test_missing_or_foreign_source_scope_rejected(self):
        wrong=dict(self.fx.request,artifactId='0'*64)
        self.assertEqual(self.stream(self.archive,meta=wrong)[0],403)

if __name__=='__main__':unittest.main()
