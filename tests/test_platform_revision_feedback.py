"""R14-A RED: waveform comments must stay attached to the exact lawful audio revision."""
import unittest
from test_platform_identity_and_catalog import PlatformHTTP
from platform_identity import PlatformDenied

class RevisionFeedbackHTTP(unittest.TestCase):
    def setUp(self):
        fixture = PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
        fixture.setUp()
        self.f = fixture
        self.addCleanup(fixture.doCleanups)
        self.a = fixture.signup('artist_a')
        self.ca, _ = fixture.login('artist_a')
        self.b = fixture.signup('artist_b', 'another strong password!')
        self.cb, _ = fixture.login('artist_b', 'another strong password!')
        self.source = fixture.project(self.a['principalId'])

    def test_exact_source_comment_survives_new_revision_without_reanchoring(self):
        from platform_feedback import FeedbackStore
        import studio_server as studio
        from test_platform_identity_and_catalog import SPEC
        store = FeedbackStore(self.f.root)
        src = self.source
        created = store.create_comment(self.a['principalId'], {
            'projectId': src['projectId'], 'revisionId': src['revisionId'],
            'artifactId': src['artifactId'], 'samplePosition': 100,
            'barBeatLabel': 'bar 1 beat 1', 'body': 'Bass note is late'
        })
        self.assertEqual(created['samplePosition'], 100)
        self.assertEqual(created['revisionId'], src['revisionId'])
        result = store.list_comments(self.a['principalId'], src['projectId'], src['revisionId'], src['artifactId'])
        self.assertEqual(len(result['comments']), 1)
        self.assertEqual(result['comments'][0]['body'], 'Bass note is late')
        newer = studio.project_operation(self.f.root, {
            'projectId': src['projectId'], 'expectedCurrentRevisionId': src['revisionId'],
            'songSpec': SPEC, 'outputArtifactIds': [src['artifactId']]
        }, commit=True, principal_id=self.a['principalId'])
        newer_id = newer['revision']['revisionId']
        self.assertNotEqual(newer_id, src['revisionId'])
        self.assertEqual(len(store.list_comments(self.a['principalId'], src['projectId'], newer_id, src['artifactId'])['comments']), 0)
        self.assertEqual(len(store.list_comments(self.a['principalId'], src['projectId'], src['revisionId'], src['artifactId'])['comments']), 1)

    def test_foreign_principal_and_forged_artifact_fail_closed(self):
        from platform_feedback import FeedbackStore
        store = FeedbackStore(self.f.root)
        src = self.source
        with self.assertRaises((PlatformDenied, PermissionError)):
            store.list_comments(self.b['principalId'], src['projectId'], src['revisionId'], src['artifactId'])
        with self.assertRaises((PlatformDenied, PermissionError)):
            store.create_comment(self.b['principalId'], {'projectId':src['projectId'], 'revisionId':src['revisionId'],
              'artifactId':src['artifactId'], 'samplePosition':0, 'barBeatLabel':'1.1', 'body':'Unauthorized'})
        with self.assertRaises((PlatformDenied, PermissionError, ValueError)):
            store.create_comment(self.a['principalId'], {'projectId':src['projectId'], 'revisionId':src['revisionId'],
              'artifactId':'0'*64, 'samplePosition':0, 'barBeatLabel':'1.1', 'body':'Forged audio'})

    def test_invalid_sample_position_never_becomes_a_comment(self):
        from platform_feedback import FeedbackStore
        store = FeedbackStore(self.f.root)
        src = self.source
        base = {'projectId': src['projectId'], 'revisionId':src['revisionId'],
          'artifactId':src['artifactId'], 'barBeatLabel':'1.1', 'body':'Late snare'}
        for position in [-1, 2**63, 0.5, True]:
            with self.subTest(position=position):
                with self.assertRaises((ValueError, PlatformDenied)):
                    store.create_comment(self.a['principalId'], base | {'samplePosition':position})
        self.assertEqual(store.list_comments(self.a['principalId'], src['projectId'], src['revisionId'], src['artifactId'])['comments'], [])
    def test_authenticated_http_feedback_never_leaks_private_project(self):
        from urllib.parse import urlencode
        src=self.source
        body={'projectId':src['projectId'],'revisionId':src['revisionId'],
          'artifactId':src['artifactId'],'samplePosition':100,
          'barBeatLabel':'1.1','body':'Bring the guitar forward'}
        path='/api/feedback/comments'
        self.assertEqual(self.f.api(path,body,cookie=self.cb)[0],403)
        self.assertEqual(self.f.api(path,body,cookie=None)[0],403)
        response=self.f.api(path,body,cookie=self.ca)
        self.assertEqual(response[0],201,response[2])
        url=path+'?'+urlencode({k:body[k] for k in ('projectId','revisionId','artifactId')})
        self.assertEqual(self.f.api(url,cookie=self.cb)[0],403)
        self.assertEqual(self.f.api(url,cookie=None)[0],403)
        result=self.f.api(url,cookie=self.ca)
        self.assertEqual(result[0],200,result[2])
        self.assertEqual(result[2]['comments'][0]['samplePosition'],100)

    def test_erasure_request_purges_private_feedback_before_completion(self):
        from platform_feedback import FeedbackStore
        from platform_identity import PlatformStore
        src=self.source
        FeedbackStore(self.f.root).create_comment(self.a['principalId'],{
          'projectId':src['projectId'],'revisionId':src['revisionId'],
          'artifactId':src['artifactId'],'samplePosition':10,
          'barBeatLabel':'1.1','body':'private draft'})
        owner=PlatformStore(self.f.root)
        owner.request_account_erasure(self.a['principalId'],'in_app')
        owner.process_pending_account_erasures()
        with owner._db() as db:
            count=db.execute('SELECT COUNT(*) FROM revision_timeline_comments WHERE author=?',
               (self.a['principalId'],)).fetchone()[0]
        self.assertEqual(count,0)
    def test_newest_bounded_feedback_is_visible_not_starved_by_old_comments(self):
        from platform_feedback import FeedbackStore
        store=FeedbackStore(self.f.root)
        src=self.source
        with store.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            for i in range(302):
                db.execute('''INSERT INTO revision_timeline_comments
                  (id,project,revision,artifact,sample_position,sample_rate,bar_beat_label,author,body,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?)''',
                  (f'fc-{i:032x}',src['projectId'],src['revisionId'],src['artifactId'],
                   i,44100,'1.1',self.a['principalId'],f'comment-{i}',1000+i))
            db.commit()
        result=store.list_comments(self.a['principalId'],src['projectId'],
                                   src['revisionId'],src['artifactId'])
        self.assertEqual(len(result['comments']),300)
        self.assertEqual(result['comments'][0]['body'],'comment-2')
        self.assertEqual(result['comments'][-1]['body'],'comment-301')
