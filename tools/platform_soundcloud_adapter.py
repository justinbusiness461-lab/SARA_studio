"""R15-B zero-network SoundCloud OAuth2/PKCE and release-intent builder.

The only authority for releases is the canonical StudioReleaseGateway and its
Studio ProjectRevision / immutable WAV. No token exchange, upload, replacement,
public release or Content ID service is implemented or remotely invoked.
"""
from __future__ import annotations
import base64,hashlib,json,re,secrets
from urllib.parse import urlencode,urlsplit
from platform_identity import PlatformStore,PlatformDenied
from platform_release_gateway import StudioReleaseGateway,digest

class SoundCloudUnavailable(RuntimeError):
    http_status=503

class SoundCloudReleaseAdapter:
    _AUTHORIZE_URL='https://secure.soundcloud.com/authorize'
    def __init__(self,root,*,client_id='',redirect_uri='',rights_policy=None):
        self.root=root
        self.client_id=client_id
        self.redirect_uri=redirect_uri
        self.rights_policy=rights_policy
        self.network_calls_made=0

    def _configured(self):
        if not isinstance(self.client_id,str) or not 1<=len(self.client_id)<=256:
            raise SoundCloudUnavailable('SOUNDCLOUD_CLIENT_ID_UNCONFIGURED_503')
        if not isinstance(self.redirect_uri,str) or not self.redirect_uri:
            raise SoundCloudUnavailable('SOUNDCLOUD_REDIRECT_UNCONFIGURED_503')
        u=urlsplit(self.redirect_uri)
        # Only an exact localhost callback or HTTPS public callback is admissible.
        if (u.scheme not in {'http','https'} or not u.hostname
            or u.username or u.password or u.fragment or
            (u.scheme=='http' and u.hostname not in {'127.0.0.1','localhost'})):
            raise SoundCloudUnavailable('SOUNDCLOUD_REDIRECT_UNQUALIFIED_503')

    def prepare_authorization(self):
        self._configured()
        verifier=secrets.token_urlsafe(64)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        state=secrets.token_urlsafe(32)
        query=urlencode({'response_type':'code','client_id':self.client_id,
            'redirect_uri':self.redirect_uri,'code_challenge_method':'S256',
            'code_challenge':challenge,'state':state})
        return {'state':state,'codeVerifier':verifier,'codeChallenge':challenge,
            'authorizationUrl':self._AUTHORIZE_URL+'?'+query,
            'expiresInSeconds':300,'statePersisted':False,
            'exchangeReady':False,'networkCallsMade':0,'external_dsp_published':False}

    def prepare_upload(self,package_id,principal):
        self._configured()
        if not isinstance(package_id,str) or not re.fullmatch('rp-[a-f0-9]{64}',package_id):
            raise PlatformDenied('SOUNDCLOUD_PACKAGE_DENIED')
        gateway=StudioReleaseGateway(self.root)
        with gateway.identity._db() as db:
            row=db.execute('''SELECT p.package_json,p.principal,a.status
                FROM release_readiness_packages p JOIN accounts a ON a.principal=p.principal
                WHERE p.package_id=?''',(package_id,)).fetchone()
        if row is None or row['principal']!=principal or row['status']!='active':
            raise PlatformDenied('SOUNDCLOUD_PACKAGE_OWNER_DENIED')
        package=json.loads(row['package_json'])
        if (package.get('schemaVersion')!='sara.release.package.v1'
            or package.get('packageId')!=package_id
            or 'rp-'+digest({k:v for k,v in package.items() if k!='packageId'})!=package_id
            or package.get('publicationState')!='PREPARED_ONLY'
            or package.get('external_dsp_published') is not False
            or package.get('content_id_entitled') is not False):
            raise PlatformDenied('SOUNDCLOUD_PACKAGE_INTEGRITY_DENIED')
        source={'projectId':package['projectId'],'revisionId':package['revisionId'],
                'artifactId':package['artifactSha256']}
        # Owner must still be lawful and current at time of intent construction.
        gateway._source(principal,source,require_current=True)
        if not callable(self.rights_policy):
            raise SoundCloudUnavailable('SOUNDCLOUD_HOST_RIGHTS_POLICY_UNCONFIGURED_503')
        expected={'ARTIST_ORIGINAL':'ARTIST_OWNED',
                  'LICENSE_CLEARED':'LICENSE_CLEARED'}.get(package['rightsStatus'])
        if self.rights_policy(source['projectId'],source['revisionId'],
                  source['artifactId'],principal)!=expected or not expected:
            raise PlatformDenied('SOUNDCLOUD_RELEASE_RIGHTS_UNVERIFIED')
        identity=hashlib.sha256((principal+'|'+package_id+'|'+source['artifactId']).encode()).hexdigest()
        # This is NOT a submission request. Cover art has a claimed checksum,
        # not a verified image/rights object. No upload client is installed.
        return {'schemaVersion':'sara.soundcloud.upload.intent.v1',
             'idempotencyKey':'sci-'+identity,
             'state':'UPLOAD_HELD','releasePackageId':package_id,
             'sourceProjectId':source['projectId'],
             'sourceRevisionId':source['revisionId'],
             'artifactSha256':source['artifactId'],
             'title':package['title'],'genre':package['genre'],
             'coverArtSha256Claim':package['coverArtSha256'],
             'coverArtMediaAndRightsQualified':False,
             'liveOauthReady':False,'liveUploadReady':False,
             'external_dsp_published':False,'content_id_entitled':False,
             'networkCallsMade':0,'chargesIncurredUsd':0}

    def exchange_code_for_token(self,code,state):
        raise SoundCloudUnavailable('SOUNDCLOUD_EXCHANGE_NOT_ADMITTED_503')

    def execute_upload(self,upload_intent):
        raise SoundCloudUnavailable('SOUNDCLOUD_UPLOAD_NOT_ADMITTED_503')
