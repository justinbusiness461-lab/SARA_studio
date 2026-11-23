"""R9 host-configured signing and attestations; no browser-side rights authority.

Keys are secrets injected by trusted host startup. Persistent rights decisions
are exact principal/project/revision/artifact/event assertions; *not* legal
proof. Every usage still crosses canonical Studio project/CAS authorization.
"""
from __future__ import annotations
import base64
import binascii
import json
import os
import re
import sqlite3
from pathlib import Path

from m045_soundtrack_grant import HostSigningKeyRing

_SHA = re.compile(r'[0-9a-f]{64}\Z')
_PID = re.compile(r'[a-f0-9]{32}\Z')
_RID = _SHA
_PRINCIPAL = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_EVENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_ALLOWED=frozenset({'ARTIST_ORIGINAL','LICENSE_CLEARED','UNVERIFIED_HELD'})


def _parse_right(record):
    keys={'principalId','projectId','revisionId','artifactId','eventId','status','evidenceSha256'}
    if not isinstance(record,dict) or set(record)!=keys:
        raise ValueError('HOST_RIGHTS_RECORD_FIELDS_INVALID')
    for key,pattern in [('principalId',_PRINCIPAL),('projectId',_PID),
                        ('revisionId',_RID),('artifactId',_SHA),
                        ('evidenceSha256',_SHA)]:
        if not isinstance(record[key],str) or not pattern.fullmatch(record[key]):
            raise ValueError('HOST_RIGHTS_RECORD_IDENTITY_INVALID')
    event=record['eventId']
    if event is not None and (not isinstance(event,str) or not _EVENT.fullmatch(event)):
        raise ValueError('HOST_RIGHTS_RECORD_EVENT_INVALID')
    if record['status'] not in _ALLOWED:
        raise ValueError('HOST_RIGHTS_RECORD_STATUS_INVALID')
    return (record['principalId'],record['projectId'],record['revisionId'],
            record['artifactId'],event or '',record['status'],record['evidenceSha256'])


class HostRightsRegistry:
    """Dedicated host-private SQLite policy ledger, disjoint from user SQLite.

    Host code can import signed/independently reviewed policy decisions and revoke;
    a client never receives a mutation or policy-import endpoint. A revoked row
    cannot be resurrected by a restart replay of the original JSON.
    """
    def __init__(self,studio_root):
        root=Path(studio_root).resolve()
        folder=root/'.host-rights'
        if folder.is_symlink():raise ValueError('HOST_RIGHTS_STORAGE_SYMLINK')
        folder.mkdir(mode=0o700,parents=True,exist_ok=True)
        os.chmod(folder,0o700)
        self.db_path=folder/'rights.sqlite3'
        if self.db_path.is_symlink():raise ValueError('HOST_RIGHTS_STORAGE_SYMLINK')
        with self._db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS rights (
                principal TEXT NOT NULL,
                project_id TEXT NOT NULL,
                revision_id TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                revocation_reason TEXT,
                PRIMARY KEY(principal,project_id,revision_id,artifact_id,event_id));
            ''')
        os.chmod(self.db_path,0o600)

    def _db(self):
        db=sqlite3.connect(self.db_path,timeout=20,isolation_level=None)
        db.execute('PRAGMA busy_timeout=20000')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        db.row_factory=sqlite3.Row
        return db

    def import_attestations(self,records):
        if not isinstance(records,list) or len(records)>10000:
            raise ValueError('HOST_RIGHTS_REGISTRY_RECORD_SET_INVALID')
        parsed=[_parse_right(r) for r in records]
        if len(set((v[0],v[1],v[2],v[3],v[4]) for v in parsed))!=len(parsed):
            raise ValueError('HOST_RIGHTS_REGISTRY_DUPLICATE')
        with self._db() as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                for p,pid,rid,aid,event,status,evidence in parsed:
                    existing=db.execute('''SELECT status,evidence_sha256,revoked FROM rights
                        WHERE principal=? AND project_id=? AND revision_id=?
                            AND artifact_id=? AND event_id=?''',(p,pid,rid,aid,event)).fetchone()
                    if existing:
                        if existing['revoked'] or existing['status']!=status or existing['evidence_sha256']!=evidence:
                            raise ValueError('HOST_RIGHTS_REATTESTATION_REVIEW_REQUIRED')
                    else:
                        db.execute('''INSERT INTO rights(principal,project_id,revision_id,artifact_id,
                            event_id,status,evidence_sha256) VALUES(?,?,?,?,?,?,?)''',
                            (p,pid,rid,aid,event,status,evidence))
                db.commit()
            except Exception:
                db.rollback()
                raise

    def revoke(self,record,reason):
        p,pid,rid,aid,event,_,_= _parse_right(record)
        if not isinstance(reason,str) or not 1<=len(reason)<=200:
            raise ValueError('HOST_REVOCATION_REASON_REQUIRED')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            updated=db.execute('''UPDATE rights SET revoked=1,revocation_reason=?
                  WHERE principal=? AND project_id=? AND revision_id=?
                      AND artifact_id=? AND event_id=?''',
                      (reason,p,pid,rid,aid,event)).rowcount
            db.commit()
        if updated!=1:raise ValueError('HOST_RIGHTS_NOT_REGISTERED')

    def _status(self,principal,pid,rid,aid,event):
        for value,pattern in [(principal,_PRINCIPAL),(pid,_PID),(rid,_RID),(aid,_SHA)]:
            if not isinstance(value,str) or not pattern.fullmatch(value):return None
        if event and (not isinstance(event,str) or not _EVENT.fullmatch(event)):return None
        with self._db() as db:
            row=db.execute('''SELECT status,revoked FROM rights WHERE
                 principal=? AND project_id=? AND revision_id=? AND artifact_id=? AND event_id=?''',
                 (principal,pid,rid,aid,event)).fetchone()
        if not row or row['revoked']:return None
        return row['status']

    def has_retained_principal(self,principal):
        if not isinstance(principal,str) or not _PRINCIPAL.fullmatch(principal):
            raise ValueError('HOST_RIGHTS_PRINCIPAL_INVALID')
        with self._db() as db:
            return db.execute('SELECT 1 FROM rights WHERE principal=? LIMIT 1',
                              (principal,)).fetchone() is not None

    def scratch(self,principal,pid,rid,event,digest):
        status=self._status(principal,pid,rid,digest,event)
        return status if status in ('ARTIST_ORIGINAL','LICENSE_CLEARED') else None

    def publication(self,pid,rid,aid,principal):
        status=self._status(principal,pid,rid,aid,'')
        return {'ARTIST_ORIGINAL':'ARTIST_OWNED','LICENSE_CLEARED':'LICENSE_CLEARED'}.get(status)

    def cinema(self,pid,rid,aid,principal):
        status=self._status(principal,pid,rid,aid,'')
        return {'ARTIST_ORIGINAL':'ARTIST_OWNED','LICENSE_CLEARED':'LICENSED_FOR_CINEMA'}.get(status)


def _parse_keyring(raw,active_id):
    if not isinstance(active_id,str) or not _EVENT.fullmatch(active_id):
        raise ValueError('HOST_ACTIVE_KEY_ID_INVALID')
    try: doc=json.loads(raw)
    except (TypeError,ValueError) as error:
        raise ValueError('HOST_SIGNING_KEYS_JSON_INVALID') from error
    if not isinstance(doc,dict) or set(doc)!={'keys'} or not isinstance(doc['keys'],list) or not 1<=len(doc['keys'])<=64:
        raise ValueError('HOST_SIGNING_KEYS_SCHEMA_INVALID')
    keys={};revoked=set()
    for item in doc['keys']:
        if (not isinstance(item,dict) or
            not {'keyId','secretBase64'}<=set(item)<= {'keyId','secretBase64','revoked'}):
            raise ValueError('HOST_SIGNING_KEY_ENTRY_INVALID')
        kid=item['keyId']
        if not isinstance(kid,str) or not _EVENT.fullmatch(kid) or kid in keys:
            raise ValueError('HOST_SIGNING_KEY_ID_DUPLICATE')
        if item.get('revoked',False) not in (True,False):
            raise ValueError('HOST_SIGNING_KEY_REVOKED_INVALID')
        try:
            secret=base64.b64decode(item['secretBase64'],validate=True)
        except (TypeError,ValueError,binascii.Error) as error:
            raise ValueError('HOST_SIGNING_KEY_BASE64_INVALID') from error
        if len(secret)<32:raise ValueError('HOST_SIGNING_KEY_STRENGTH_INVALID')
        keys[kid]=secret
        if item.get('revoked',False):revoked.add(kid)
    ring=HostSigningKeyRing(active_id,keys,frozenset(revoked))
    ring.require_active_key()
    return ring


def configure_host_authorities_from_env(root):
    """Trusted host startup only. Invalid/partial env -> no partial install.

    Environment secret format is a deployment contract, NOT a legal rights
    certification. The host must independently authenticate the provenance
    of every license/artist ownership attestation before setting env values.
    """
    import studio_server as studio
    vars=('SARA_HOST_SIGNING_KEYS_JSON','SARA_ACTIVE_KEY_ID','SARA_SAMPLE_RIGHTS_REGISTRY_JSON')
    values=[os.environ.get(name) for name in vars]
    if all(value is None for value in values):
        return {'configured':False,'reason':'HOST_AUTHORITIES_UNCONFIGURED'}
    if any(not value for value in values):
        raise ValueError('HOST_AUTHORITIES_PARTIAL_CONFIGURATION')
    ring=_parse_keyring(values[0],values[1])
    try: records=json.loads(values[2])
    except ValueError as error:
        raise ValueError('HOST_RIGHTS_REGISTRY_JSON_INVALID') from error
    if not isinstance(records,list):raise ValueError('HOST_RIGHTS_REGISTRY_JSON_INVALID')
    # Validate all BEFORE any persistent side effect or process-global install.
    for record in records:_parse_right(record)
    registry=HostRightsRegistry(root)
    registry.import_attestations(records)
    studio.configure_m045_soundtrack_grant(ring,registry.cinema)
    studio.configure_platform_scratch_sample_rights(registry.scratch)
    studio.configure_platform_publication_rights(registry.publication)
    return {'configured':True,'activeKeyId':ring.active_key_id,
            'policyRecords':len(records),'rightsAuthority':'HOST_PRIVATE_SQLITE',
            'rightsClearance':'HOST_ATTESTED_NOT_INDEPENDENTLY_LICENSE_CERTIFIED'}
