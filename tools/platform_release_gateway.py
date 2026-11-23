"""Release *preparation* and consent registry, subordinate to Studio revisions.

This cannot publish to a DSP, certify cover-art rights, verify a voice by artist
self-attestation, or create Content ID entitlement. All external rights evidence
is supplied exclusively by a host-installed verifier.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re
import secrets
import time
from platform_identity import PlatformStore, PlatformDenied

_SHA=re.compile(r'[0-9a-f]{64}\Z')
_TOKEN=re.compile(r'[0-9a-f]{64}\Z')
_VOICE=re.compile(r'va-[0-9a-f]{32}\Z')
_FIELDS=frozenset({'projectId','revisionId','artifactId','title','artistHandle','genre',
                   'coverArtSha256','rightsStatus'})
_SCOPES=frozenset({'VOICE_CONDITIONED_STUDIO_ONLY'})
_ALLOWED_RIGHTS={'ARTIST_ORIGINAL':'ARTIST_OWNED','LICENSE_CLEARED':'LICENSE_CLEARED'}

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

def digest(obj):
    return hashlib.sha256(canonical(obj).encode('utf-8')).hexdigest()

class StudioReleaseGateway:
    def __init__(self,root):
        self.root=root
        self.identity=PlatformStore(root)
        with self.identity._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS voice_assets(
                    id TEXT PRIMARY KEY, principal TEXT NOT NULL,
                    project TEXT NOT NULL, revision TEXT NOT NULL,
                    artifact TEXT NOT NULL, attestation_sha256 TEXT NOT NULL,
                    scope TEXT NOT NULL, consent_verified INTEGER NOT NULL DEFAULT 0,
                    revoked_at INTEGER);
                CREATE INDEX IF NOT EXISTS idx_voice_assets_principal
                    ON voice_assets(principal,revoked_at);
                CREATE TABLE IF NOT EXISTS release_approvals(
                    token_digest TEXT PRIMARY KEY, principal TEXT NOT NULL,
                    payload_digest TEXT NOT NULL, expires_at INTEGER NOT NULL,
                    used_at INTEGER);
                CREATE TABLE IF NOT EXISTS release_readiness_packages(
                    package_id TEXT PRIMARY KEY, principal TEXT NOT NULL,
                    package_json TEXT NOT NULL);
            """)

    def _source(self,principal,payload,*,require_current=False):
        from studio_server import project_operation,project_audio_bytes
        pid,rid,aid=(payload[k] for k in ('projectId','revisionId','artifactId'))
        self.identity.profile(principal)
        try:
            selection=project_operation(self.root,{'projectId':pid},principal_id=principal)
            source=project_operation(self.root,{'projectId':pid,'revisionId':rid},principal_id=principal)
            if aid not in source['revision'].get('outputArtifactIds',[]):
                raise PlatformDenied('RELEASE_SOURCE_NOT_ACCEPTED')
            if require_current and selection['manifest']['currentRevisionId']!=rid:
                raise PlatformDenied('RELEASE_REVISION_NOT_CURRENT')
            audio=project_audio_bytes(self.root,{'projectId':pid,'revisionId':rid,'artifactId':aid},
                                      principal_id=principal)
            if hashlib.sha256(audio).hexdigest()!=aid:
                raise PlatformDenied('RELEASE_AUDIO_READBACK_MISMATCH')
            return source
        except (ValueError,KeyError,PermissionError,OSError) as error:
            raise PlatformDenied('RELEASE_SOURCE_DENIED') from error

    def _metadata(self,principal,payload):
        if not isinstance(payload,dict) or set(payload)!=_FIELDS:
            raise ValueError('RELEASE_FIELDS_INVALID')
        if not all(isinstance(payload[k],str) for k in _FIELDS):
            raise ValueError('RELEASE_FIELDS_INVALID')
        if not _SHA.fullmatch(payload['coverArtSha256']):
            raise ValueError('RELEASE_COVER_DIGEST_INVALID')
        for key,limit in (('title',160),('artistHandle',30),('genre',100)):
            v=payload[key]
            if not 1<=len(v.strip())<=limit or '\x00' in v or v!=v.strip():
                raise ValueError('RELEASE_METADATA_INVALID')
        if payload['rightsStatus'] not in _ALLOWED_RIGHTS:
            raise PlatformDenied('RELEASE_RIGHTS_UNVERIFIED')
        profile=self.identity.profile(principal)
        if profile['handle']!=payload['artistHandle']:
            raise PlatformDenied('RELEASE_ARTIST_IDENTITY_DENIED')
        source=self._source(principal,payload,require_current=True)
        if source['songSpec'].get('title')!=payload['title']:
            raise PlatformDenied('RELEASE_TITLE_NOT_CANONICAL')
        return source

    def approve(self,principal,payload):
        if not isinstance(payload,dict) or set(payload)!=_FIELDS|{'confirmRelease'}:
            raise ValueError('RELEASE_APPROVAL_FIELDS_INVALID')
        if payload['confirmRelease'] is not True:
            raise PlatformDenied('RELEASE_APPROVAL_REQUIRED')
        request={k:payload[k] for k in _FIELDS}
        self._metadata(principal,request)
        token=secrets.token_hex(32)
        now=int(time.time())
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            active=db.execute("SELECT status FROM accounts WHERE principal=?",(principal,)).fetchone()
            if not active or active['status']!='active':
                raise PlatformDenied('RELEASE_OWNER_NOT_ACTIVE')
            db.execute("""INSERT INTO release_approvals
                (token_digest,principal,payload_digest,expires_at)
                VALUES(?,?,?,?)""",(hashlib.sha256(token.encode()).hexdigest(),
                                      principal,digest(request),now+300))
            db.commit()
        return {'status':'APPROVED_FOR_PREPARATION','approvalToken':token,
                'expiresAt':now+300,'revisionId':request['revisionId']}

    def prepare(self,principal,payload,rights_policy):
        if not isinstance(payload,dict) or set(payload)!=_FIELDS|{'approvalToken'}:
            raise ValueError('RELEASE_PREPARE_FIELDS_INVALID')
        token=payload['approvalToken']
        if not isinstance(token,str) or not _TOKEN.fullmatch(token):
            raise PlatformDenied('RELEASE_APPROVAL_TOKEN_DENIED')
        request={k:payload[k] for k in _FIELDS}
        source=self._metadata(principal,request)
        if not callable(rights_policy):
            raise PlatformDenied('RELEASE_HOST_RIGHTS_UNCONFIGURED')
        policy_status=rights_policy(request['projectId'],request['revisionId'],
                                    request['artifactId'],principal)
        if policy_status!=_ALLOWED_RIGHTS[request['rightsStatus']]:
            raise PlatformDenied('RELEASE_HOST_RIGHTS_UNVERIFIED')
        pkg={'schemaVersion':'sara.release.package.v1',
             'projectId':request['projectId'],'revisionId':request['revisionId'],
             'artifactSha256':request['artifactId'],'title':request['title'],
             'artistHandle':request['artistHandle'],'genre':request['genre'],
             'coverArtSha256':request['coverArtSha256'],
             'rightsStatus':request['rightsStatus'],
             'external_dsp_published':False,'content_id_entitled':False,
             'coverArtMediaAndRightsQualified':False,
             'publicationState':'PREPARED_ONLY',
             'acceptedSongSpecRevisionId':source['revision']['revisionId']}
        package_id='rp-'+digest(pkg)
        pkg['packageId']=package_id
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("""SELECT a.principal,a.payload_digest,a.expires_at,a.used_at,
                    p.status FROM release_approvals a JOIN accounts p
                    ON p.principal=a.principal WHERE a.token_digest=?""",
                    (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if (row is None or row['principal']!=principal or row['status']!='active'
                or row['used_at'] is not None or row['expires_at']<=int(time.time())
                or not hmac.compare_digest(row['payload_digest'],digest(request))):
                raise PlatformDenied('RELEASE_APPROVAL_DENIED')
            db.execute("""INSERT OR IGNORE INTO release_readiness_packages
                (package_id,principal,package_json) VALUES(?,?,?)""",
                (package_id,principal,canonical(pkg)))
            updated=db.execute("""UPDATE release_approvals SET used_at=?
                WHERE token_digest=? AND used_at IS NULL""",
                (int(time.time()),hashlib.sha256(token.encode()).hexdigest()))
            if updated.rowcount!=1:
                raise PlatformDenied('RELEASE_APPROVAL_ALREADY_USED')
            db.commit()
        return pkg

    def register_voice(self,principal,payload):
        expected={'projectId','revisionId','artifactId','consentAttestationSha256','consentScope'}
        if not isinstance(payload,dict) or set(payload)!=expected:
            raise ValueError('VOICE_REGISTRATION_FIELDS_INVALID')
        if (not isinstance(payload['consentAttestationSha256'],str)
           or not _SHA.fullmatch(payload['consentAttestationSha256'])
           or payload['consentScope'] not in _SCOPES):
            raise ValueError('VOICE_CONSENT_FIELDS_INVALID')
        self._source(principal,payload)
        vid='va-'+secrets.token_hex(16)
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            active=db.execute("SELECT status FROM accounts WHERE principal=?",(principal,)).fetchone()
            if not active or active['status']!='active':
                raise PlatformDenied('VOICE_OWNER_NOT_ACTIVE')
            db.execute("""INSERT INTO voice_assets(id,principal,project,revision,artifact,
                attestation_sha256,scope) VALUES(?,?,?,?,?,?,?)""",
                (vid,principal,payload['projectId'],payload['revisionId'],payload['artifactId'],
                 payload['consentAttestationSha256'],payload['consentScope']))
            db.commit()
        return {'status':'CONSENT_REVIEW_REQUIRED','voiceId':vid,
                'referenceWavSha256':payload['artifactId'],
                'consentAttestationSha256':payload['consentAttestationSha256'],
                'consentScope':payload['consentScope'],'consentVerified':False}

    def host_verify_voice(self,voice_id,host_verifier):
        # Not exposed over HTTP. A separately authorized host owner must
        # authenticate the real attestation, identity and declared scope.
        if not callable(host_verifier):
            raise PlatformDenied('VOICE_HOST_VERIFIER_REQUIRED')
        with self.identity._db() as db:
            row=db.execute("SELECT * FROM voice_assets WHERE id=?",(voice_id,)).fetchone()
        if row is None or row['revoked_at'] is not None:
            raise PlatformDenied('VOICE_ASSET_DENIED')
        evidence={'voiceId':voice_id,'ownerPrincipalId':row['principal'],
                  'referenceWavSha256':row['artifact'],
                  'consentAttestationSha256':row['attestation_sha256'],
                  'consentScope':row['scope']}
        self._source(row['principal'],{'projectId':row['project'],'revisionId':row['revision'],
                 'artifactId':row['artifact']})
        if host_verifier(evidence) is not True:
            raise PlatformDenied('VOICE_CONSENT_NOT_VERIFIED')
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            result=db.execute("""UPDATE voice_assets SET consent_verified=1 WHERE id=?
                AND revoked_at IS NULL AND EXISTS(SELECT 1 FROM accounts
                WHERE principal=voice_assets.principal AND status='active')""",(voice_id,))
            if result.rowcount!=1:
                raise PlatformDenied('VOICE_CONSENT_REVOKED')
            db.commit()
        return {'voiceId':voice_id,'consentVerified':True}

    def authorize_voice(self,principal,voice_id,payload):
        if not isinstance(voice_id,str) or not _VOICE.fullmatch(voice_id):
            raise PlatformDenied('VOICE_ASSET_DENIED')
        if not isinstance(payload,dict) or set(payload)!={'projectId','revisionId','artifactId','consentScope'}:
            raise PlatformDenied('VOICE_USE_SCOPE_DENIED')
        with self.identity._db() as db:
            row=db.execute("""SELECT v.*,a.status FROM voice_assets v JOIN accounts a
                ON a.principal=v.principal WHERE v.id=?""",(voice_id,)).fetchone()
        if (row is None or row['principal']!=principal or row['status']!='active'
            or row['consent_verified']!=1 or row['revoked_at'] is not None
            or any(payload[key]!=row[column] for key,column in (
                 ('projectId','project'),('revisionId','revision'),
                 ('artifactId','artifact'),('consentScope','scope')))):
            raise PlatformDenied('VOICE_USE_DENIED')
        self._source(principal,payload)
        return {'status':'VOICE_CONSENT_VERIFIED','voiceId':voice_id,
                'consentScope':row['scope'],'revisionId':row['revision']}

    def revoke_voice(self,principal,voice_id):
        if not isinstance(voice_id,str) or not _VOICE.fullmatch(voice_id):
            raise PlatformDenied('VOICE_REVOKE_DENIED')
        with self.identity._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("""SELECT a.status,v.principal FROM voice_assets v JOIN accounts a
                ON a.principal=v.principal WHERE v.id=?""",(voice_id,)).fetchone()
            if not row or row['principal']!=principal or row['status']!='active':
                raise PlatformDenied('VOICE_REVOKE_DENIED')
            db.execute("UPDATE voice_assets SET revoked_at=COALESCE(revoked_at,?) WHERE id=?",
                       (int(time.time()),voice_id))
            db.commit()
        return {'status':'REVOKED','voiceId':voice_id}
