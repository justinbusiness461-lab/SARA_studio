"""R25 browser fixture: real preexisting staging graph or host-only synthetic CI fallback.
Never publishes source media or grants. Browser inputs never supply rights.
"""
import hashlib,io,json,os,socketserver,struct,sys,wave
from pathlib import Path

# Certification gate is deliberately evaluated before importing Studio or constructing
# synthetic audio. CI fixture mode remains available only when strict mode is OFF.
strict_value = os.environ.get('SARA_R25_REAL_MEDIA_STRICT', '0')
if strict_value not in ('0', '1'):
 raise SystemExit('R27_REAL_MEDIA_STRICT_INVALID: expected 0 or 1')
strict_real_media = strict_value == '1'
real_root = os.environ.get('SARA_R25_REAL_MEDIA_ROOT')
real_receipts = os.environ.get('SARA_R25_REAL_MEDIA_RECEIPTS')
if strict_real_media:
 if not real_root or not real_receipts:
  raise SystemExit('R27_REAL_MEDIA_REQUIRED: real root and receipts must both be set')
 if not Path(real_root).is_dir():
  raise SystemExit('R27_REAL_MEDIA_ROOT_NOT_FOUND')
 for receipt_name in ('private_ingestion_receipt.json', 'private_r2_receipt.json'):
  if not (Path(real_receipts) / receipt_name).is_file():
   raise SystemExit('R27_REAL_MEDIA_RECEIPT_MISSING: ' + receipt_name)

sys.path.insert(0,'tools')
import studio_server as studio
from m045_artist_master_ingestion import ingest_three_song_batch,commit_verified_edit
from r25_strict_staging_binding import StrictStagingDenied, verify_real_staging
TITLES=('Turn The Noise Back On','If This Is All I Get','Outlaws and Echoes')
real=os.environ.get('SARA_R25_REAL_MEDIA_ROOT')
root=Path(real or sys.argv[1]).resolve()
principal='artist-r25-private-staging' if real else 'r25-test-local-host'
if real:
 evidence=Path(os.environ['SARA_R25_REAL_MEDIA_RECEIPTS'])
 imported=json.loads((evidence/'private_ingestion_receipt.json').read_text())
 latest=json.loads((evidence/'private_r2_receipt.json').read_text())
 originals=imported['songs']
 assert len(originals)==3 and {s['title'] for s in originals}==set(TITLES)
 if strict_real_media:
  try:
   # Only verified artist source hashes, lawful Studio R1 media and an
   # immutable R1->R2 chain may qualify the strict physical browser run.
   verify_real_staging(root,principal,originals,latest,
                       studio.project_operation,studio.project_audio_bytes)
  except StrictStagingDenied as exc:
   raise SystemExit('R32_REAL_MEDIA_STAGING_DENIED: ' + str(exc)) from exc
elif (root/'.r25_fixture_receipt.json').is_file():
 old=json.loads((root/'.r25_fixture_receipt.json').read_text())
 originals=old['originals'];latest=old['latest']
else:
 imports={};catalogs={}
 for i,title in enumerate(TITLES):
  b=io.BytesIO()
  with wave.open(b,'wb') as w:
   w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
   w.writeframes(struct.pack('<hh',500+i,-500-i)*(21*44100))
  p=root.parent/(f'r25-demo-{i}.wav');p.write_bytes(b.getvalue())
  sha=hashlib.sha256(b.getvalue()).hexdigest()
  imports[title]=p
  catalogs[title]={'title':title,'principalId':principal,'sourceSha256':sha,
    'projectId':str(i+1)*32,'rightsEvidenceSha256':str(i+1)*64,
    'rightsStatus':'UNVERIFIED_HELD','privatePilotAuthorized':True,
    'commercialReleaseAuthorized':False,
    'pilotSection':{'id':'pilot','sampleRate':44100,'startSample':44100,'endSampleExclusive':21*44100}}
 def catalog(pid,title,sha):
  v=catalogs[title]
  assert pid==principal and v['sourceSha256']==sha
  return v
 created=ingest_three_song_batch(root=root,principal_id=principal,sources_by_title=imports,host_catalog_lookup=catalog)
 originals=created['songs']
 first=originals[0];a=studio.project_audio_bytes(root,{'projectId':first['projectId'],'revisionId':first['revisionId'],'artifactId':first['artifactId']},principal_id=principal)
 original=io.BytesIO(a);edit=io.BytesIO()
 with wave.open(original,'rb') as reader:
  with wave.open(edit,'wb') as writer:
   writer.setnchannels(reader.getnchannels());writer.setframerate(reader.getframerate());writer.setsampwidth(reader.getsampwidth())
   pcm=bytearray(reader.readframes(reader.getnframes()));pcm[0:2]=struct.pack('<h',int.from_bytes(pcm[0:2],'little',signed=True)+1)
   writer.writeframes(bytes(pcm))
 outpath=root.parent/'r25-fixture-r2.wav';outpath.write_bytes(edit.getvalue())
 latest=commit_verified_edit(root=root,principal_id=principal,project_id=first['projectId'],expected_r1_revision_id=first['revisionId'],edited_wav_path=outpath,host_edit_verifier=lambda e: e['principalId']==principal and e['projectId']==first['projectId'] and e['sourceRevisionId']==first['revisionId'])
 (root/'.r25_fixture_receipt.json').write_text(json.dumps({'originals':originals,'latest':latest}))
studio.EXPORT_ROOT=root;studio.PLATFORM_MODE=False;studio.LOCAL_PRINCIPAL_ID=principal
songs=[]
for r in originals:
 current=studio.project_operation(root,{'projectId':r['projectId']},principal_id=principal)
 songs.append({'title':r['title'],'projectId':r['projectId'],
  'r1':{'revisionId':r['revisionId'],'artifactId':r['artifactId']},
  'selected':{'revisionId':current['revision']['revisionId'],'artifactId':current['revision']['outputArtifactIds'][0]}})
class Server(socketserver.ThreadingTCPServer):allow_reuse_address=True;daemon_threads=True
with Server(('127.0.0.1',0),studio.StudioHandler) as srv:
 studio.PORT=srv.server_address[1]
 print(json.dumps({'port':studio.PORT,'songs':songs,'stagingRealMedia':bool(real),'strictRealMedia':strict_real_media}),flush=True)
 srv.serve_forever()