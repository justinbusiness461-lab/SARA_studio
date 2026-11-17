import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import wave
import struct

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'prior'))
from live_nasa004 import run, validate_fixture, _path, _origin, ContractFailure, CASE_RULES


def audio(samples):
    buff = io.BytesIO()
    with wave.open(buff, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(b''.join(struct.pack('<hh', s, s) for s in samples))
    return buff.getvalue()


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_GET(self):
        cookie = self.headers.get('Cookie')
        user = 'A' if cookie == 'SID_A_TEST' else 'B' if cookie == 'SID_B_TEST' else None
        if user is None:
            self.reply(401, b'{"error":"anonymous"}')
            return
        if self.path in ('/project/a', '/project/b'):
            owner = self.path[-1].upper()
            status = 200 if user == owner or (self.server.mode == 'cross_user_leak' and user == 'B' and owner == 'A') else 404
            self.reply(status, b'{"name":"safe"}' if status == 200 else b'{"error":"not found"}')
        elif self.path == '/history/a/r1':
            self.reply(200 if user == 'A' else 404, b'{"revisions":[]}' if user == 'A' else b'{"error":"not found"}')
        elif self.path == '/artifact/a/unbound':
            self.reply(404, b'{"error":"not found"}')
        elif self.path in ('/audio/a/r1', '/audio/a/r2'):
            if user != 'A':
                self.reply(404, b'{"error":"not found"}')
                return
            if self.server.mode == 'redirect':
                self.send_response(302);self.send_header('Location', 'https://untrusted.example.com/audio');self.end_headers()
                return
            revision = self.path[-2:]
            payload = self.server.audios[revision]
            if self.server.mode == 'bad_wav' and revision == 'r2': payload = b'BAD_WAV_BYTES'
            if self.server.mode == 'wrong_sha' and revision == 'r2': payload = self.server.audios['r1']
            extras = {'X-Source-Revision-Id': self.server.revision_ids[revision],
                      'X-Audio-SHA256': hashlib.sha256(payload).hexdigest()}
            if self.server.mode == 'missing_header' and revision == 'r2':extras.pop('X-Source-Revision-Id')
            if self.server.mode == 'wrong_revision' and revision == 'r2': extras['X-Source-Revision-Id'] = self.server.revision_ids['r1']
            self.reply(200, payload, 'audio/wav', extras)
        else:
            self.reply(404, b'{"error":"not found"}')

    def reply(self,status,body,mime='application/json',extras=None):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        for k,v in (extras or {}).items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)


class LocalLiveHarness(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(('127.0.0.1',0), FakeHandler)
        self.srv.mode = ''
        self.srv.audios = {'r1':audio([x+200 for x in range(300)]), 'r2':audio([x+230 for x in range(300)])}
        self.srv.revision_ids = {'r1':'a'*64,'r2':'b'*64}
        self.th = threading.Thread(target=self.srv.serve_forever,daemon=True);self.th.start()
        self.fixture = {'base_url':f'http://127.0.0.1:{self.srv.server_port}',
                        'target_commit':'d'*64,
                        'audio':{k:{'sha256':hashlib.sha256(v).hexdigest(),'revision_id':self.srv.revision_ids[k]} for k,v in self.srv.audios.items()},
                        'routes':{
                            'A_PROJECT_OWN':'/project/a',
                            'B_PROJECT_OWN':'/project/b',
                            'B_PROJECT_A':'/project/a',
                            'A_PROJECT_B':'/project/b',
                            'ANON_PROJECT_A':'/project/a',
                            'A_AUDIO_R1':'/audio/a/r1',
                            'A_AUDIO_R2':'/audio/a/r2',
                            'B_AUDIO_A_R1':'/audio/a/r1',
                            'ANON_AUDIO_A_R1':'/audio/a/r1',
                            'A_HISTORY_R1':'/history/a/r1',
                            'B_HISTORY_A':'/history/a/r1',
                            'A_UNBOUND_ARTIFACT':'/artifact/a/unbound',
                        }}
        self.creds = {'A':'SID_A_TEST','B':'SID_B_TEST'}

    def tearDown(self):self.srv.shutdown();self.srv.server_close();self.th.join(timeout=2)

    def run_probe(self):return run(self.fixture,self.creds)

    def test_success_both_users_and_two_actual_wav_http_responses(self):
        result=self.run_probe()
        self.assertEqual(result['verdict'],'PASS', result.get('first_failed_boundary'))
        self.assertEqual(result['checked_cases'],12)
        self.assertEqual({x['case'] for x in result['cases']},set(CASE_RULES))
        self.assertNotIn('SID_A_TEST',json.dumps(result))
        self.assertNotIn('SID_B_TEST',json.dumps(result))
        self.assertEqual(next(x for x in result['cases'] if x['case']=='A_AUDIO_R2')['frames'],300)

    def test_live_cross_user_read_is_rejected(self):
        self.srv.mode='cross_user_leak'
        result=self.run_probe()
        self.assertEqual((result['verdict'],result['first_failed_boundary']),('HOLD','B_PROJECT_A'))

    def test_false_wav_is_rejected_after_http_success(self):
        self.srv.mode='bad_wav'
        result=self.run_probe()
        self.assertEqual((result['verdict'],result['first_failed_boundary']),('HOLD','A_AUDIO_R2'))

    def test_wrong_audio_sha_is_rejected(self):
        self.srv.mode='wrong_sha'
        result=self.run_probe()
        self.assertEqual(result['first_failed_boundary'],'A_AUDIO_R2')

    def test_missing_revision_header_is_rejected(self):
        self.srv.mode='missing_header'
        result=self.run_probe()
        self.assertEqual(result['first_failed_boundary'],'A_AUDIO_R2')

    def test_wrong_revision_header_is_rejected(self):
        self.srv.mode='wrong_revision'
        result=self.run_probe()
        self.assertEqual(result['first_failed_boundary'],'A_AUDIO_R2')

    def test_audio_redirect_fails_closed_without_redirect_follow(self):
        self.srv.mode='redirect'
        result=self.run_probe()
        self.assertEqual(result['first_failed_boundary'],'A_AUDIO_R1')

    def test_same_principal_cookie_rejected(self):
        with self.assertRaisesRegex(ContractFailure,'two independent'):
            run(self.fixture,{'A':'SID_A_TEST','B':'SID_A_TEST'})

    def test_missing_principal_cookie_rejected(self):
        with self.assertRaises(ContractFailure):run(self.fixture,{'A':'SID_A_TEST'})

    def test_reject_nonlocal_insecure_http(self):
        self.fixture['base_url']='http://public.example.com'
        with self.assertRaisesRegex(ContractFailure,'nonlocal HTTP'):
            validate_fixture(self.fixture)

    def test_reject_secret_in_url(self):
        self.fixture['routes']['A_AUDIO_R1']='/audio/a/r1?token=secret'
        with self.assertRaisesRegex(ContractFailure,'secret in query'):
            validate_fixture(self.fixture)

    def test_reject_cross_origin_path(self):
        with self.assertRaisesRegex(ContractFailure,'relative'):
            _path('//elsewhere.com/a')

    def test_reject_incomplete_coverage(self):
        self.fixture['routes'].pop('B_HISTORY_A')
        with self.assertRaisesRegex(ContractFailure,'twelve fixed'):
            validate_fixture(self.fixture)

    def test_reject_mutated_cross_user_target(self):
        self.fixture['routes']['B_AUDIO_A_R1']='/audio/a/r2'
        with self.assertRaisesRegex(ContractFailure,'identical R1'):
            validate_fixture(self.fixture)

    def test_reject_identical_audio_expectations(self):
        self.fixture['audio']['r2'] = self.fixture['audio']['r1'].copy()
        with self.assertRaisesRegex(ContractFailure,'R1/R2 revisions must be distinct'):
            validate_fixture(self.fixture)

    def test_no_expected_revision_naming_from_display_labels(self):
        self.fixture['audio']['r1']['revision_id']='R1'
        with self.assertRaisesRegex(ContractFailure,r'exact WAV\+revision SHA'):
            validate_fixture(self.fixture)

if __name__=='__main__':unittest.main()
