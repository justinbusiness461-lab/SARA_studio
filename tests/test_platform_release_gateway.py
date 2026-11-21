"""Round 14-B RED: release intent, rights and voice consent are not client authority."""
import hashlib
import unittest
from test_platform_identity_and_catalog import PlatformHTTP, SPEC

class ReleaseGatewayHTTP(unittest.TestCase):
    def setUp(self):
        f=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
        f.setUp();self.f=f;self.addCleanup(f.doCleanups)
        self.a=f.signup('release_artist');self.ca,_=f.login('release_artist')
        self.b=f.signup('other_artist','another strong password!')
        self.cb,_=f.login('other_artist','another strong password!')
        self.src=f.project(self.a['principalId'])
        self.payload={'projectId':self.src['projectId'],'revisionId':self.src['revisionId'],
          'artifactId':self.src['artifactId'],'title':SPEC['title'],
          'artistHandle':'release_artist','genre':'Outlaw Hypno-Rock Country-Hop',
          'coverArtSha256':'b'*64,'rightsStatus':'ARTIST_ORIGINAL'}
    def allow(self):
        import studio_server as studio
        a,p=self.a['principalId'],self.src
        studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:
            'ARTIST_OWNED' if (pid,rid,aid,principal)==
            (p['projectId'],p['revisionId'],p['artifactId'],a) else None)
    def approval(self,overrides=None,cookie=None):
        return self.f.api('/api/release/approve',
            {**self.payload,**(overrides or {}),'confirmRelease':True},
            cookie=self.ca if cookie is None else cookie)
    def test_prepare_requires_exact_single_use_owner_approval_and_host_rights(self):
        self.allow()
        code,_,approval=self.approval()
        self.assertEqual(code,201,approval)
        token=approval['approvalToken']
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'approvalToken':'forged'},cookie=self.ca)[0],403)
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'approvalToken':token},cookie=self.cb)[0],403)
        code,_,package=self.f.api('/api/release/prepare',
            self.payload|{'approvalToken':token},cookie=self.ca)
        self.assertEqual(code,201,package)
        self.assertEqual(package['schemaVersion'],'sara.release.package.v1')
        self.assertEqual(package['projectId'],self.src['projectId'])
        self.assertEqual(package['revisionId'],self.src['revisionId'])
        self.assertEqual(package['artifactSha256'],self.src['artifactId'])
        self.assertEqual(package['external_dsp_published'],False)
        self.assertEqual(package['content_id_entitled'],False)
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'approvalToken':token},cookie=self.ca)[0],403)
    def test_release_rights_policy_and_mutated_metadata_are_rejected(self):
        code,_,challenge=self.approval()
        self.assertEqual(code,201,challenge)
        token=challenge['approvalToken']
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'approvalToken':token},cookie=self.ca)[0],403)
        self.allow()
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'title':'WRONG','approvalToken':token},cookie=self.ca)[0],403)
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'rightsStatus':'UNVERIFIED_HELD','approvalToken':token},cookie=self.ca)[0],403)
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'rightsStatus':'LICENSE_CLEARED','approvalToken':token},cookie=self.ca)[0],403)
        self.assertEqual(self.f.api('/api/release/prepare',
            self.payload|{'approvalToken':token},cookie=self.ca)[0],201)
    def test_rejects_forged_audio_historical_revision_and_forged_artist(self):
        self.allow()
        for edit in ({'artifactId':'f'*64},{'artistHandle':'other_artist'},
                     {'coverArtSha256':'x'*64}):
            self.assertNotEqual(self.approval(edit)[0],201,edit)
        # Approval was for accepted R1; current promotion to R2 invalidates it.
        code,_,approval=self.approval()
        self.assertEqual(code,201,approval)
        from studio_server import project_operation
        newer=project_operation(self.f.root,{'projectId':self.src['projectId'],
            'expectedCurrentRevisionId':self.src['revisionId'],'songSpec':SPEC,
            'outputArtifactIds':[self.src['artifactId']]},commit=True,
            principal_id=self.a['principalId'])
        self.assertNotEqual(newer['revision']['revisionId'],self.src['revisionId'])
        self.assertEqual(self.f.api('/api/release/prepare',
          self.payload|{'approvalToken':approval['approvalToken']},cookie=self.ca)[0],403)
    def test_registration_does_not_self_verify_voice_consent(self):
        data={'projectId':self.src['projectId'],'revisionId':self.src['revisionId'],
          'artifactId':self.src['artifactId'],'consentAttestationSha256':'a'*64,
          'consentScope':'VOICE_CONDITIONED_STUDIO_ONLY'}
        code,_,asset=self.f.api('/api/voice-assets',data,cookie=self.ca)
        self.assertEqual(code,201,asset)
        self.assertFalse(asset['consentVerified'])
        self.assertEqual(self.f.api('/api/voice-assets/'+asset['voiceId']+'/authorize',
          {'projectId':data['projectId'],'revisionId':data['revisionId'],
           'artifactId':data['artifactId'],'consentScope':data['consentScope']},cookie=self.ca)[0],403)
        self.assertEqual(self.f.api('/api/voice-assets',data|{'consentVerified':True},
          cookie=self.ca)[0],400)
    def test_host_verified_voice_scoped_and_revocable(self):
        from platform_release_gateway import StudioReleaseGateway
        data={'projectId':self.src['projectId'],'revisionId':self.src['revisionId'],
          'artifactId':self.src['artifactId'],'consentAttestationSha256':'a'*64,
          'consentScope':'VOICE_CONDITIONED_STUDIO_ONLY'}
        code,_,asset=self.f.api('/api/voice-assets',data,cookie=self.ca)
        self.assertEqual(code,201,asset)
        gateway=StudioReleaseGateway(self.f.root)
        with self.assertRaises(PermissionError):
            gateway.host_verify_voice(asset['voiceId'],None)
        gateway.host_verify_voice(asset['voiceId'],lambda record:
            record['consentAttestationSha256']=='a'*64)
        use={'projectId':data['projectId'],'revisionId':data['revisionId'],
           'artifactId':data['artifactId'],'consentScope':data['consentScope']}
        self.assertEqual(self.f.api('/api/voice-assets/'+asset['voiceId']+'/authorize',
           use,cookie=self.ca)[0],200)
        self.assertEqual(self.f.api('/api/voice-assets/'+asset['voiceId']+'/authorize',
           use,cookie=self.cb)[0],403)
        self.assertEqual(self.f.api('/api/voice-assets/'+asset['voiceId']+'/authorize',
           use|{'consentScope':'VOICE_EXPORT'},cookie=self.ca)[0],403)
        self.assertEqual(self.f.api('/api/voice-assets/'+asset['voiceId']+'/revoke',{},
           cookie=self.ca)[0],200)
        self.assertEqual(self.f.api('/api/voice-assets/'+asset['voiceId']+'/authorize',
           use,cookie=self.ca)[0],403)
    def test_erasure_invalidates_pending_release_and_voice_asset(self):
        from platform_identity import PlatformStore
        code,_,approval=self.approval();self.assertEqual(code,201,approval)
        data={'projectId':self.src['projectId'],'revisionId':self.src['revisionId'],
          'artifactId':self.src['artifactId'],'consentAttestationSha256':'a'*64,
          'consentScope':'VOICE_CONDITIONED_STUDIO_ONLY'}
        self.assertEqual(self.f.api('/api/voice-assets',data,cookie=self.ca)[0],201)
        store=PlatformStore(self.f.root)
        store.request_account_erasure(self.a['principalId'],'in_app')
        self.assertEqual(self.f.api('/api/release/prepare',
           self.payload|{'approvalToken':approval['approvalToken']},cookie=self.ca)[0],403)
        store.process_pending_account_erasures()
        with store._db() as db:
            for table in ('voice_assets','release_approvals','release_readiness_packages'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table+' WHERE principal=?',
                   (self.a['principalId'],)).fetchone()[0],0,table)

if __name__=='__main__':unittest.main()
