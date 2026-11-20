"""Independent Round7 physical fixture readback; DOES NOT authorize production media."""
import hashlib,io,json,subprocess,sys,tempfile,wave
from pathlib import Path
sys.path[:0]=["/tmp/sara-round7/tools","/tmp/sara-round7/tests"]
import studio_server as studio
from test_platform_round7_scratch_rights import RightsBoundScratchHTTP
from test_platform_round7_mix_owner import OwnedMixRecipe
from m045_stem_reconstruction_owner import authorized_reconstruct_mix
from m045_modal_trial_preflight import zero_spend_modal_preflight
def probe(wav_bytes,filename):
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/filename
  path.write_bytes(wav_bytes)
  metadata=subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
    "-show_entries","stream=codec_name,channels,sample_rate,duration",
    "-of","json",str(path)],capture_output=True,text=True,check=True,timeout=20)
  stream=json.loads(metadata.stdout)["streams"][0]
  data=subprocess.run(["ffmpeg","-v","error","-i",str(path),
    "-f","s16le","-acodec","pcm_s16le","-ar","44100","-ac","2",
    "pipe:1"],capture_output=True,check=True,timeout=20).stdout
  with wave.open(io.BytesIO(wav_bytes),"rb") as f:
   frames=f.getnframes()
   assert data==f.readframes(frames)
  assert stream["sample_rate"]=="44100" and stream["channels"]==2
  assert stream["codec_name"]=="pcm_s16le"
  return {"wavSha256":hashlib.sha256(wav_bytes).hexdigest(),
    "pcmSha256":hashlib.sha256(data).hexdigest(),"frames":frames,
    "byteLength":len(wav_bytes),"ffprobe":stream,
    "decodedBytesMatchedCanonicalPCM":True}
s=RightsBoundScratchHTTP(methodName="test_host_denial_then_verified_rights_produces_exact_pcm_wav_revision")
s.setUp()
try:
 s.configure_rights("ARTIST_ORIGINAL")
 status,headers,result=s.render()
 assert status==200,result
 audio=studio.project_audio_bytes(s.fx.root,{"projectId":s.ref["projectId"],
   "revisionId":result["revisionId"],"artifactId":result["artifactId"]},
    principal_id=s.owner["principalId"])
 scratch=probe(audio,"scratch-rights-fixture.wav")
 scratch.update({"ownerResult":result,"sampleAssetSha256":s.sample_id,
   "originalArtifactSha256":s.ref["artifactId"],
   "rightsAttestedBy":"test fixture host callback only"})
finally:
 s.doCleanups()
m=OwnedMixRecipe(methodName="test_exact_authorized_recipe_produces_revision_bound_wav_and_cold_reconstruction")
m.setUp()
try:
 result=authorized_reconstruct_mix(m.fx.root,m.request,m.owner["principalId"])
 data=studio.project_audio_bytes(m.fx.root,{"projectId":m.pid,
   "revisionId":result["revisionId"],"artifactId":result["artifactId"]},
   principal_id=m.owner["principalId"])
 mix=probe(data,"dry-stem-fixture.wav")
 mix.update({"ownerResult":result,"stemSha256":m.ids,
   "recipeDigest":result["recipeSha256"],"sourceRights":"UNVERIFIED_HELD"})
finally:
 m.doCleanups()
modal=zero_spend_modal_preflight("/tmp/sara-round7/deploy/modal_acestep.py",{
 "mode":"ZERO_SPEND_PREFLIGHT","gpuSecondsCap":90,
 "songSecondsCap":30,"maxSpendUsd":0,"execute":False})
receipt={"schema":"sara.platform.r7.physical_proof.v1",
"sourceKind":"DETERMINISTIC_TEST_FIXTURES_NOT_REAL_ARTIST_AUDIO",
"scratch":scratch,"dryStemMix":mix,"modalZeroSpendPreflight":modal,
"externalGPUCall":False,"creativeApproved":False,"releaseCleared":False}
output=Path("/tmp/r7-physical-fixtures.json")
output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print(json.dumps({"fixtureReceiptSha256":hashlib.sha256(output.read_bytes()).hexdigest(),
 "scratchWavSha256":scratch["wavSha256"],"scratchFrames":scratch["frames"],
 "mixWavSha256":mix["wavSha256"],"mixFrames":mix["frames"],
 "modalGpuAllocated":modal["gpuAllocated"],"modalChargesUsd":modal["chargesIncurredUsd"]}))
