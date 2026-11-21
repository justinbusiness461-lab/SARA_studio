"""R13-C: full 210s canonical ZIP (>64MiB) physically streams over authenticated HTTP."""
import base64,hashlib,http.client,json,resource,tempfile,unittest
from pathlib import Path
from test_m045_daw_export import DawHttp
from m045_daw_export import export_authorized_daw_bundle
import studio_server as studio

class LongHttpDaw(unittest.TestCase):
    def test_210_second_archive_binary_streaming_http(self):
        fx=DawHttp('test_bundle_revision_stems_midi_musicxml_and_checksum_identity')
        fx.setUp();self.addCleanup(fx.doCleanups)
        fx.build_canonical_mix(frames=210*44100)
        with tempfile.TemporaryDirectory(prefix='r13-original-') as directory:
            archive=Path(directory)/'canonical-daw.zip'
            export_authorized_daw_bundle(fx.fx.root,fx.request,fx.owner['principalId'],archive)
            size=archive.stat().st_size
            self.assertGreater(size,64*1024*1024)
            source_header=base64.urlsafe_b64encode(json.dumps(fx.request,sort_keys=True,
                separators=(',',':')).encode()).decode().rstrip('=')
            connection=http.client.HTTPConnection('127.0.0.1',studio.PORT,timeout=150)
            try:
                with archive.open('rb') as stream:
                    connection.request('POST','/api/m045/verify-daw-bundle',body=stream,
                      headers={'Content-Type':'application/zip','Content-Length':str(size),
                      'X-Sara-Daw-Source':source_header,'Cookie':fx.cookie,
                      'X-Studio-Capability':studio.CAPABILITY,
                      'Origin':f'http://127.0.0.1:{studio.PORT}'})
                response=connection.getresponse();body=json.loads(response.read())
            finally:connection.close()
            self.assertEqual(response.status,200,body)
            self.assertEqual(body['archiveSha256'],hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(body['state'],'VERIFIED_UNMODIFIED_BUNDLE')
            self.assertFalse(body['newRevisionCommitted'])
            print('R13_DAW_HTTP_210_PHYSICAL',json.dumps({'zipBytes':size,
                'sha256':body['archiveSha256'],'peakRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'state':body['state']},sort_keys=True),flush=True)

if __name__=='__main__':unittest.main()
