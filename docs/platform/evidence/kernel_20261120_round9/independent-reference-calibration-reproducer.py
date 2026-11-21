"""Independent FFmpeg ebur128 comparison on four actual deterministic PCM16 vectors."""
from pathlib import Path
import tempfile,subprocess,json,hashlib,math,re,sys
sys.path[:0]=['/tmp/r9/tools','/tmp/r9/tests']
from test_m045_round9_bs1770_reference import fixture
from m045_bs1770_reference import measure_reference_pcm16
spec=[('997_stereo_44k1',fixture(44100)),('997_stereo_48k',fixture(48000)),('997_plus_silence',fixture(48000,duration=4.0,silence_start=2)),('fs4_intersample',fixture(48000,frequency=12000,amplitude=.98,phase=math.pi/4))]
rows=[]
with tempfile.TemporaryDirectory(prefix='sara-r9-physical-meter-') as td:
 for name,wav in spec:
  p=Path(td)/(name+'.wav');p.write_bytes(wav)
  result=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','info','-i',str(p),'-filter_complex','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,check=True,timeout=20)
  summary=result.stderr.rsplit('Summary:',1)[-1]
  loudness=float(re.search(r'Integrated loudness:\s*I:\s*(-?[\d.]+)\s*LUFS',summary)[1])
  true_peak=float(re.search(r'True peak:\s*Peak:\s*(-?[\d.]+)\s*dBFS',summary)[1])
  own=measure_reference_pcm16(wav)
  lu_delta=abs(own['integrated_lufs']-loudness);db_delta=abs(own['true_peak_dbtp']-true_peak)
  assert lu_delta<=.15 and db_delta<=.15,(name,lu_delta,db_delta)
  rows.append({'id':name,'waveSha256':hashlib.sha256(wav).hexdigest(),'referenceIntegratedLufs':own['integrated_lufs'],'referenceTruePeakDbtp':own['true_peak_dbtp'],'independentFfmpegIntegratedLufs':loudness,'independentFfmpegTruePeakDbtp':true_peak,'deltaLU':round(lu_delta,4),'deltaDB':round(db_delta,4)})
report={'schema':'sara.m045.bs1770.reference.compare.v1','sourceProductCommit':'b8e3848608ce29d9692f95787a93015c97ba9c1d','vectors':rows,'independentCalibrationCertificate':False,'scope':'SYNTHETIC_ONLY','comparison':'FFMPEG_EBUR128_PEAK_TRUE','allPass':True}
Path('/tmp/r9-calibration-physical.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps({'vectors':len(rows),'maxLU':max(x['deltaLU'] for x in rows),'maxDB':max(x['deltaDB'] for x in rows)}))
