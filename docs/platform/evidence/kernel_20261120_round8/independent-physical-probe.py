"""R8 physical media probe; synthetic only, no commercial sample or paid GPU."""
import hashlib,io,json,struct,subprocess,sys,tempfile,time,wave
from pathlib import Path
sys.path[:0]=['/tmp/sara-round8/tools','/tmp/sara-round8/tests']
import studio_server as studio
from test_platform_round8_owner_full210 import Owned210SecondAudio

original=studio.project_audio_bytes
evidence={}
def intercept(*args,**kwargs):
    data=original(*args,**kwargs)
    if len(data)>30_000_000:evidence['wav']=data
    return data
studio.project_audio_bytes=intercept
case=Owned210SecondAudio(methodName='test_210s_full_wav_has_exact_source_membership_history_and_pcm_readback')
try:
    case.setUp()
    case.test_210s_full_wav_has_exact_source_membership_history_and_pcm_readback()
finally:
    studio.project_audio_bytes=original
    case.doCleanups()
raw=evidence['wav']
with wave.open(io.BytesIO(raw),'rb') as wav:
    frames=wav.getnframes()
    assert frames==44100*210
    pcm=wav.readframes(frames)
    assert len(pcm)==frames*4
expected=hashlib.sha256()
frame=struct.pack('<hh',26214,-26214)
for start in range(0,frames,16384):
    expected.update(frame*min(16384,frames-start))
actual=hashlib.sha256(pcm).hexdigest()
assert expected.hexdigest()==actual,('failed sample identity',expected.hexdigest(),actual)
with tempfile.TemporaryDirectory() as d:
    path=Path(d)/'mix-210-seconds.wav'
    path.write_bytes(raw)
    meta=subprocess.run(['ffprobe','-v','error','-select_streams','a:0',
            '-show_entries','stream=codec_name,channels,sample_rate,duration',
            '-of','json',str(path)],capture_output=True,text=True,timeout=30,check=True)
    audio=json.loads(meta.stdout)['streams'][0]
    assert audio['codec_name']=='pcm_s16le'
    assert audio['channels']==2 and audio['sample_rate']=='44100'
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(path),
                 '-f','s16le','-acodec','pcm_s16le','-ar','44100',
                 '-ac','2','pipe:1'],capture_output=True,timeout=50,check=True).stdout
    assert hashlib.sha256(decoded).hexdigest()==actual
    assert len(decoded)==frames*4
receipt={'schema':'sara.mix.r8.physical.v1','source':'DETERMINISTIC_SYNTHETIC_F64_STEM',
  'sample_rate':44100,'channels':2,'seconds':210,'frames':frames,
  'sample_level_exact':True,'decoded_pcm_sha256':actual,
  'expected_pcm_sha256':expected.hexdigest(),
  'wav_sha256':hashlib.sha256(raw).hexdigest(),
  'wav_bytes':len(raw),'ffprobe':audio,
  'ffmpeg_pcm_identity':True,'commercial_rights':'UNVERIFIED_HELD',
  'creative_approval':False,'release_qualified':False}
out=Path('/tmp/r8-independent-physical.json')
out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(json.dumps(receipt,sort_keys=True))
