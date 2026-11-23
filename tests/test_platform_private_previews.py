"""Round 14-A2 RED: private preview links are exact-revision, revocable media grants."""
import time
import unittest
from urllib.parse import urlencode
from test_platform_identity_and_catalog import PlatformHTTP

class PrivatePreviewHTTP(unittest.TestCase):
    def setUp(self):
        fixture=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
        fixture.setUp();self.f=fixture;self.addCleanup(fixture.doCleanups)
        self.owner=fixture.signup('preview_artist');self.cookie,_=fixture.login('preview_artist')
        self.foreign=fixture.signup('foreign_artist','another strong password!')
        self.other_cookie,_=fixture.login('foreign_artist','another strong password!')
        self.src=fixture.project(self.owner['principalId'])
    def create(self, **overrides):
        p=self.src
        return self.f.api('/api/previews/grants', {
            'projectId':p['projectId'],'revisionId':p['revisionId'],
            'artifactId':p['artifactId'],'expiresInSeconds':1800
        }|overrides,cookie=self.cookie)
    def test_link_playback_and_metadata_revoked_immediately(self):
        status,_,grant=self.create()
        self.assertEqual(status,201,grant)
        self.assertEqual(grant['revisionId'],self.src['revisionId'])
        self.assertNotIn('tokenDigest',grant)
        meta=self.f.api(grant['metadataUrl'],cookie=None)
        wav=self.f.req(grant['audioUrl'],cookie=None)
        self.assertEqual(meta[0],200,meta[2])
        self.assertEqual(wav[0],200)
        self.assertEqual(wav[2],self.src['sourceAudio'])
        self.assertEqual(wav[1].get('Cache-Control'),'no-store')
        self.assertEqual(self.f.api('/api/previews/'+grant['grantId']+'/revoke',{},
                 cookie=self.other_cookie)[0],403)
        self.assertEqual(self.f.api('/api/previews/'+grant['grantId']+'/revoke',{},
                 cookie=self.cookie)[0],200)
        self.assertEqual(self.f.api(grant['metadataUrl'])[0],403)
        self.assertEqual(self.f.req(grant['audioUrl'])[0],403)
    def test_token_is_required_and_not_forged_by_id_or_cas(self):
        status,_,grant=self.create()
        self.assertEqual(status,201,grant)
        clean='/api/previews/'+grant['grantId']
        for suffix in ('/metadata','/audio'):
            self.assertEqual(self.f.req(clean+suffix)[0],403)
            self.assertEqual(self.f.req(clean+suffix+'?token=forged')[0],403)
        self.assertEqual(self.create(artifactId='f'*64)[0],403)
        self.assertEqual(self.f.api('/api/previews/grants',{
           'projectId':self.src['projectId'],'revisionId':self.src['revisionId'],
           'artifactId':self.src['artifactId'],'expiresInSeconds':100
        },cookie=self.other_cookie)[0],403)
    def test_expiration_fails_closed(self):
        status,_,grant=self.create(expiresInSeconds=1)
        self.assertEqual(status,201,grant)
        from unittest.mock import patch
        with patch('platform_feedback.time.time',return_value=int(time.time())+2):
            self.assertEqual(self.f.api(grant['metadataUrl'])[0],403)
            self.assertEqual(self.f.req(grant['audioUrl'])[0],403)
        self.assertEqual(self.create(expiresInSeconds=0)[0],400)
        self.assertEqual(self.create(expiresInSeconds=99999999)[0],400)
    def test_account_erasure_blocks_audio_even_before_worker_purge(self):
        status,_,grant=self.create()
        self.assertEqual(status,201,grant)
        from platform_identity import PlatformStore
        identity=PlatformStore(self.f.root)
        identity.request_account_erasure(self.owner['principalId'],'in_app')
        self.assertEqual(self.f.req(grant['audioUrl'])[0],403)
        self.assertEqual(self.f.api(grant['metadataUrl'])[0],403)
        identity.process_pending_account_erasures()
        with identity._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM private_preview_grants WHERE creator=?',
               (self.owner['principalId'],)).fetchone()[0],0)
    def test_historical_grant_never_tracks_new_current_revision(self):
        status,_,grant=self.create()
        self.assertEqual(status,201,grant)
        from test_platform_identity_and_catalog import SPEC
        from studio_server import project_operation
        new=project_operation(self.f.root,{
            'projectId':self.src['projectId'],
            'expectedCurrentRevisionId':self.src['revisionId'],
            'songSpec':SPEC,'outputArtifactIds':[self.src['artifactId']]
        },commit=True,principal_id=self.owner['principalId'])
        self.assertNotEqual(new['revision']['revisionId'],self.src['revisionId'])
        data=self.f.api(grant['metadataUrl'])[2]
        self.assertEqual(data['revisionId'],self.src['revisionId'])
        self.assertEqual(self.f.req(grant['audioUrl'])[2],self.src['sourceAudio'])

if __name__=='__main__':unittest.main()
