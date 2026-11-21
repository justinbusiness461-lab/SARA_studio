"""Independent FFmpeg readback of an actual authenticated canonical DAW archive."""
import hashlib,io,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
sys.path[:0]=['/tmp/studio-r10/tools','/tmp/studio-r10/tests']
from test_m045_daw_export import DawHttp
fx=DawHttp(methodName='test_unauthorized_and_master_without_dry_source_fail_closed')
fx.setUp()
try:
 bound=fx.build_canonical_mix()
 response,headers,raw=fx.request_bundle()
 assert response==200 and headers['Content-Type']=='application/zip'
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  manifest=json.loads(z.read('daw_manifest.json'))
  assert all(hashlib.sha256(z.read(name)).hexdigest()==digest
             for name,digest in manifest['fileSha256'].items())
  assert manifest['masterArtifactId']==bound['artifactId'] and manifest['reconstructionExact']
  assert manifest['midiPpq']==480 and manifest['creativeStemsExact'] is False
  details=[]
  with tempfile.TemporaryDirectory(prefix='sara-r10-ffprobe-') as folder:
   for name in ('master_44k1_16b.wav','stems/creative_01.wav'):
    wav=Path(folder)/(name.replace('/','_'))
    wav.write_bytes(z.read(name))
    result=subprocess.run(['ffprobe','-v','error','-select_streams','a:0',
      '-show_entries','stream=codec_name,sample_rate,channels,duration',
      '-of','json',str(wav)],text=True,capture_output=True,check=True,timeout=8)
    stream=json.loads(result.stdout)['streams'][0]
    assert stream['codec_name']=='pcm_s16le' and stream['sample_rate']=='44100' and stream['channels']==2
    details.append({'path':name,'sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),
                    'codec':stream['codec_name'],'sampleRate':int(stream['sample_rate']),
                    'channels':stream['channels'],'seconds':stream.get('duration')})
 report={'schema':'sara.r10.daw.ffprobe.witness.v1','testFixture':'SYNTHETIC_ONLY',
         'productSha':'8fadf6d02b2ab347ba3c25b97301295bb6ec2cd7',
         'sourceProjectRevisionId':manifest['sourceProjectRevisionId'],
         'reconstructedProjectRevisionId':manifest['projectRevisionId'],
         'zipSha256':hashlib.sha256(raw).hexdigest(),'zipBytes':len(raw),
         'masterSha256':manifest['masterArtifactId'],'verifiedZipEntries':len(manifest['fileSha256']),
         'rawStemSha256':manifest['stemArtifactIds'],
         'independentDecodedStreams':details,'rightsStatus':manifest['rightsStatus'],
         'releaseCleared':False,'newProjectRevisionCreatedByExport':False,
         'productionQualified':False,'creativeApproved':False}
 out=Path('/tmp/r10-physical-daw-witness.json');out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
 print('PHYSICAL_FFPROBE_PASS',json.dumps({'entryHashes':len(manifest['fileSha256']),
  'archiveSha256':report['zipSha256'],'streams':len(details)}))
finally:
 fx.doCleanups()
