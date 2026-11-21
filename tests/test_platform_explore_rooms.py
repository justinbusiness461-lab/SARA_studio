"""R13 RED: authenticated durable Rooms reuse existing Studio owners."""
import unittest
from test_platform_identity_and_catalog import PlatformHTTP

class RoomsHTTP(unittest.TestCase):
    def setUp(self):
        f=PlatformHTTP(methodName='test_acc01_entry_does_not_bootstrap_local_user')
        f.setUp();self.f=f;self.addCleanup(f.doCleanups)
        self.api=f.api;self.req=f.req
        self.a=f.signup('artist_a');self.ca,_=f.login('artist_a')
        self.b=f.signup('artist_b','another strong password!');self.cb,_=f.login('artist_b','another strong password!')
        self.c=f.signup('artist_c','third strong password!');self.cc,_=f.login('artist_c','third strong password!')
    def create(self,visibility='private',occupancy=8):
        code,_,body=self.api('/api/explore/rooms',{'name':'Songwriters Circle','category':'Songwriters','visibility':visibility,'maxOccupancy':occupancy},cookie=self.ca)
        self.assertEqual(code,201,body)
        return body['roomId']
    def route(self,room,suffix):return '/api/explore/rooms/'+room+'/'+suffix
    def test_private_room_admission_durable_order_revocation_and_search(self):
        room=self.create()
        self.assertEqual(self.api('/api/explore/rooms',cookie=self.cc)[2]['rooms'],[])
        self.assertEqual(self.api(self.route(room,'messages'),cookie=self.cc)[0],403)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cb)[0],403)
        self.assertEqual(self.api(self.route(room,'invite'),{'handle':'artist_b'},cookie=self.ca)[0],200)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cb)[0],200)
        self.assertEqual(self.api(self.route(room,'messages'),{'body':'First verse idea'},cookie=self.ca)[0],201)
        self.assertEqual(self.api(self.route(room,'messages'),{'body':'Second hook idea'},cookie=self.cb)[0],201)
        msgs=self.api(self.route(room,'messages'),cookie=self.cb)
        self.assertEqual(msgs[0],200,msgs[2]);self.assertEqual([m['body'] for m in msgs[2]['messages']],['First verse idea','Second hook idea'])
        self.assertTrue(all(m['isBot'] is False for m in msgs[2]['messages']))
        self.assertEqual(len({m['sequence'] for m in msgs[2]['messages']}),2)
        self.assertEqual(self.api(self.route(room,'messages'),cookie=self.cc)[0],403)
        from platform_rooms import RoomStore
        self.assertEqual(len(RoomStore(self.f.root).messages(self.b['principalId'],room)['messages']),2)
        self.assertEqual(self.api(self.route(room,'kick'),{'handle':'artist_b'},cookie=self.ca)[0],200)
        self.assertEqual(self.api(self.route(room,'messages'),cookie=self.cb)[0],403)
        self.assertEqual(self.api(self.route(room,'messages'),{'body':'Late write'},cookie=self.cb)[0],403)
    def test_public_search_join_capacity_and_host_only_invite(self):
        room=self.create('public',occupancy=2)
        rooms=self.api('/api/explore/rooms?category=Songwriters&q=Circle',cookie=self.cc)[2]['rooms']
        self.assertEqual(rooms[0]['roomId'],room)
        self.assertEqual(self.api(self.route(room,'invite'),{'handle':'artist_c'},cookie=self.cb)[0],403)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cb)[0],200)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cc)[0],409)
        self.assertEqual(self.api(self.route(room,'leave'),{},cookie=self.cb)[0],200)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cc)[0],200)
    def test_publication_pin_is_not_audio_authority_after_unpublish(self):
        import studio_server as studio
        room=self.create('public')
        src=self.f.project(self.a['principalId'])
        studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:'ARTIST_OWNED'
            if (pid,rid,aid,principal)==(src['projectId'],src['revisionId'],src['artifactId'],self.a['principalId']) else None)
        pub=self.f.publish(src,self.ca)[2]['publicationId']
        pin=self.api(self.route(room,'pin-track'),{'publicationId':pub},cookie=self.ca)
        self.assertEqual(pin[0],200,pin[2])
        self.api(self.route(room,'join'),{},cookie=self.cb)
        self.assertEqual(self.api(self.route(room,'messages'),cookie=self.cb)[2]['listeningStation'][0]['publicationId'],pub)
        self.assertEqual(self.req('/api/songs/'+pub+'/audio')[0],200)
        self.assertEqual(self.api('/api/publications/'+pub+'/unpublish',{},cookie=self.ca)[0],200)
        self.assertEqual(self.req('/api/songs/'+pub+'/audio')[0],404)
        self.assertEqual(self.api(self.route(room,'messages'),cookie=self.cb)[2]['listeningStation'],[])
    def test_collaboration_proposal_is_not_revision_commit(self):
        room=self.create();self.api(self.route(room,'invite'),{'handle':'artist_b'},cookie=self.ca)
        self.api(self.route(room,'join'),{},cookie=self.cb)
        src=self.f.project(self.a['principalId']);wid=self.api('/api/workspaces',{'name':'Room Co-write'},cookie=self.ca)[2]['workspaceId']
        self.assertEqual(self.api(self.route(room,'propose-collaboration'),{'workspaceId':wid,'projectId':src['projectId'],'baseRevisionId':src['revisionId'],'instruction':'Replace hook'},cookie=self.cb)[0],403)
        self.assertEqual(self.api('/api/workspaces/'+wid+'/bind',{'projectId':src['projectId']},cookie=self.ca)[0],200)
        self.assertEqual(self.api('/api/workspaces/'+wid+'/invite',{'handle':'artist_b','role':'viewer'},cookie=self.ca)[0],200)
        created=self.api(self.route(room,'propose-collaboration'),{'workspaceId':wid,'projectId':src['projectId'],'baseRevisionId':src['revisionId'],'instruction':'Please review Verse 2 guitar texture'},cookie=self.cb)
        self.assertEqual(created[0],201,created[2]);self.assertEqual(created[2]['state'],'AWAITING_OWNER_REVIEW')
        self.assertFalse(created[2]['revisionCommitted'])
        from studio_server import project_operation
        after=project_operation(self.f.root,{'projectId':src['projectId']},principal_id=self.a['principalId'])
        self.assertEqual(after['manifest']['currentRevisionId'],src['revisionId'])



    def test_anonymous_room_directory_and_message_access_are_denied(self):
        room=self.create('public')
        self.assertEqual(self.api('/api/explore/rooms')[0],403)
        self.assertEqual(self.api(self.route(room,'messages'))[0],403)
        self.assertEqual(self.api(self.route(room,'messages'),{'body':'anonymous'})[0],403)
    def test_kicked_private_invitee_cannot_rejoin_without_new_invitation(self):
        room=self.create()
        self.api(self.route(room,'invite'),{'handle':'artist_b'},cookie=self.ca)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cb)[0],200)
        self.assertEqual(self.api(self.route(room,'kick'),{'handle':'artist_b'},cookie=self.ca)[0],200)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cb)[0],403)
    def test_social_block_and_room_block_deny_room_interactions(self):
        room=self.create('public')
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cb)[0],200)
        self.assertEqual(self.api('/api/social/action',{'action':'block','handle':'artist_b'},cookie=self.ca)[0],200)
        self.assertEqual(self.api(self.route(room,'messages'),cookie=self.cb)[0],403)
        self.assertEqual(self.api(self.route(room,'block'),{'handle':'artist_b'},cookie=self.ca)[0],200)
        self.assertEqual(self.api(self.route(room,'join'),{},cookie=self.cb)[0],403)
    def test_user_cannot_spoof_bot_role_or_fake_other_artist(self):
        room=self.create()
        self.assertEqual(self.api(self.route(room,'messages'),{'body':'hello','isBot':True},cookie=self.ca)[0],400)
        self.assertEqual(self.api(self.route(room,'messages'),{'body':'<script>evil()</script>'},cookie=self.ca)[0],201)
        body=self.api(self.route(room,'messages'),cookie=self.ca)[2]
        self.assertFalse(body['messages'][0]['isBot'])
        self.assertNotIn('<script>',body['messages'][0]['body'])
    def test_room_listing_capacity_rejects_unsafe_boolean_and_invalid_search(self):
        self.assertEqual(self.api('/api/explore/rooms',{'name':'No','category':'Songwriters','visibility':'public','maxOccupancy':True},cookie=self.ca)[0],400)
        self.assertEqual(self.api('/api/explore/rooms?q='+'x'*100,cookie=self.ca)[0],400)
    def test_member_revocation_during_slow_rights_recheck_cannot_expose_messages(self):
        import studio_server as studio
        from platform_rooms import RoomStore
        from platform_identity import PlatformDenied
        from unittest.mock import patch
        room=self.create('public')
        self.api(self.route(room,'join'),{},cookie=self.cb)
        src=self.f.project(self.a['principalId'])
        studio.configure_platform_publication_rights(lambda pid,rid,aid,principal:'ARTIST_OWNED'
          if (pid,rid,aid,principal)==(src['projectId'],src['revisionId'],src['artifactId'],self.a['principalId']) else None)
        pub=self.f.publish(src,self.ca)[2]['publicationId']
        self.assertEqual(self.api(self.route(room,'pin-track'),{'publicationId':pub},cookie=self.ca)[0],200)
        rooms=RoomStore(self.f.root);rooms.rights_policy=studio.PLATFORM_PUBLICATION_RIGHTS
        def revoke_during_music_read(*_):
            rooms.kick(self.a['principalId'],room,'artist_b')
            return {'song':{'publicationId':pub}}
        with patch('platform_catalog.public_song',revoke_during_music_read):
            with self.assertRaises(PlatformDenied):rooms.messages(self.b['principalId'],room)

class RoomsErasure(unittest.TestCase):
    def test_room_accounts_erasure_purges_transcripts_and_all_room_identity(self):
        import tempfile
        from platform_identity import PlatformStore
        from platform_rooms import RoomStore
        with tempfile.TemporaryDirectory() as d:
            identity=PlatformStore(d)
            a=identity.register('room_owner','strong password 1234','Room Owner')['principalId']
            b=identity.register('room_guest','strong password 1234','Room Guest')['principalId']
            rooms=RoomStore(d)
            own=rooms.create(a,{'name':'Music','category':'Songwriters','visibility':'private','maxOccupancy':4})['roomId']
            other=rooms.create(b,{'name':'Open Session','category':'Beat Lab','visibility':'public','maxOccupancy':4})['roomId']
            rooms.join(a,other);rooms.post_message(a,other,'Hello from owner')
            identity.request_account_erasure(a,'in_app')
            self.assertEqual(identity.process_pending_account_erasures()['processed'],1)
            receipt=identity.complete_account_erasure(a,studio_root=d)
            self.assertEqual(receipt['state'],'ERASURE_COMPLETED')
            with identity._db() as db:
                for table,col in [('music_rooms','host'),('music_room_members','principal'),('music_room_invites','principal'),('music_room_messages','author'),('music_room_proposals','author'),('music_room_blocks','principal')]:
                    self.assertFalse(db.execute('SELECT 1 FROM '+table+' WHERE '+col+'=?',(a,)).fetchone(),table)
            self.assertEqual(len(rooms.directory(b)['rooms']),1)

if __name__=='__main__':unittest.main()
