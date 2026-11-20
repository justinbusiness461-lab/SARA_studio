"""Native rhythm arithmetic and DJ harmonic transition candidates.
No SongSpec/revision/CAS authority or donor implementation imported.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
import io, math, struct, wave

SUBDIVISION_STEPS_PER_BEAT = {'8th':2,'8th_triplet':3,'16th':4,'16th_triplet':6}
VELOCITY_TIERS={'ghost':45,'normal':95,'accent':127}
_CAMELOT={
 'G# minor':(1,'A'),'Ab minor':(1,'A'),'B major':(1,'B'),
 'D# minor':(2,'A'),'Eb minor':(2,'A'),'F# major':(2,'B'),'Gb major':(2,'B'),
 'A# minor':(3,'A'),'Bb minor':(3,'A'),'C# major':(3,'B'),'Db major':(3,'B'),
 'F minor':(4,'A'),'G# major':(4,'B'),'Ab major':(4,'B'),
 'C minor':(5,'A'),'D# major':(5,'B'),'Eb major':(5,'B'),
 'G minor':(6,'A'),'A# major':(6,'B'),'Bb major':(6,'B'),
 'D minor':(7,'A'),'F major':(7,'B'),
 'A minor':(8,'A'),'C major':(8,'B'),
 'E minor':(9,'A'),'G major':(9,'B'),
 'B minor':(10,'A'),'D major':(10,'B'),
 'F# minor':(11,'A'),'Gb minor':(11,'A'),'A major':(11,'B'),
 'C# minor':(12,'A'),'Db minor':(12,'A'),'E major':(12,'B')}

@dataclass(frozen=True)
class SubdivisionStepEvent:
 event_id:str
 bar:int
 step_index:int
 subdivision:str
 velocity_tier:str
 instrument_role:str
 midi_note:int
 sample_position:int
 midi_velocity:int

@dataclass(frozen=True)
class HarmonicTransitionAnalysis:
 source_key:str
 target_key:str
 source_camelot:str
 target_camelot:str
 harmonic_relation:str
 harmonic_score:float
 source_bpm:float
 target_bpm:float
 effective_target_bpm:float
 tempo_ratio:float
 bpm_compatible:bool

def _fraction_positive(value,name,minimum=None,maximum=None):
 if type(value) not in (int,float,str,Fraction) or isinstance(value,bool):raise ValueError('INVALID_'+name)
 try:
  if isinstance(value,float) and not math.isfinite(value):raise ValueError()
  f=Fraction(str(value)) if not isinstance(value,Fraction) else value
 except (ValueError,ZeroDivisionError,OverflowError) as exc:raise ValueError('INVALID_'+name) from exc
 if f<=0 or (minimum is not None and f<minimum) or (maximum is not None and f>maximum):raise ValueError('INVALID_'+name)
 return f

def _round_nearest(f):
 """Nonnegative rational sample coordinates, nearest with half-up ties."""
 return (2*f.numerator+f.denominator)//(2*f.denominator)

def derive_subdivision_step_sample(*,bpm,bar,step_index,subdivision,beats_per_bar=4,swing_ratio='0.5',sample_rate=44100):
 """Bar is 1-based. Binary grids swing every second step in each pair.
 Triplets are ternary and never get silent extra swing distortion.
 """
 speed=_fraction_positive(bpm,'BPM',20,320)
 ratio=_fraction_positive(swing_ratio,'SWING',Fraction(1,2),Fraction(3,4))
 if subdivision not in SUBDIVISION_STEPS_PER_BEAT:raise ValueError('UNSUPPORTED_SUBDIVISION')
 if type(bar)!=int or type(step_index)!=int or type(beats_per_bar)!=int or type(sample_rate)!=int or not 1<=bar<=100000 or not 1<=beats_per_bar<=12 or sample_rate not in (44100,48000):raise ValueError('INVALID_GRID_BOUNDARY')
 per_beat=SUBDIVISION_STEPS_PER_BEAT[subdivision]
 if not 0<=step_index<per_beat*beats_per_bar:raise ValueError('STEP_INDEX_OUT_OF_BOUNDS')
 position=Fraction((bar-1)*beats_per_bar)+Fraction(step_index,per_beat)
 if per_beat in (2,4) and step_index%2:
  position+=(ratio-Fraction(1,2))*Fraction(2,per_beat)
 return _round_nearest(position*60*sample_rate/speed)

def build_subdivision_pattern_events(*,bpm,bar,subdivision,steps,beats_per_bar=4,swing_ratio='0.5',sample_rate=44100):
 if not isinstance(steps,list) or len(steps)>10000:raise ValueError('INVALID_STEP_ARRAY')
 ids=set();positions=set();result=[]
 for item in steps:
  if not isinstance(item,dict):raise ValueError('INVALID_STEP')
  eid=item.get('event_id');idx=item.get('step_index');midi=item.get('midi_note');vel=item.get('velocity_tier','normal');role=item.get('instrument_role')
  if not isinstance(eid,str) or not eid or eid in ids or type(idx)!=int or type(midi)!=int or not 0<=midi<=127 or vel not in VELOCITY_TIERS or not isinstance(role,str) or not role:raise ValueError('INVALID_OR_DUPLICATE_STEP')
  pos=derive_subdivision_step_sample(bpm=bpm,bar=bar,step_index=idx,subdivision=subdivision,beats_per_bar=beats_per_bar,swing_ratio=swing_ratio,sample_rate=sample_rate)
  if idx in positions:raise ValueError('DUPLICATE_STEP_POSITION')
  ids.add(eid);positions.add(idx)
  result.append(SubdivisionStepEvent(eid,bar,idx,subdivision,vel,role,midi,pos,VELOCITY_TIERS[vel]))
 return sorted(result,key=lambda e:(e.step_index,e.event_id))

def analyze_harmonic_and_tempo_compatibility(*,source_key,target_key,source_bpm,target_bpm,max_tempo_drift_pct=6.0):
 if source_key not in _CAMELOT or target_key not in _CAMELOT:raise ValueError('UNRECOGNIZED_MUSICAL_KEY')
 a=_fraction_positive(source_bpm,'BPM',20,320);b=_fraction_positive(target_bpm,'BPM',20,320)
 allowed=_fraction_positive(max_tempo_drift_pct,'TEMPO_TOLERANCE',None,100)
 x,lx=_CAMELOT[source_key];y,ly=_CAMELOT[target_key];distance=min((x-y)%12,(y-x)%12)
 if (x,lx)==(y,ly):relation,score='EXACT_MATCH',1.0
 elif x==y and lx!=ly:relation,score='RELATIVE_MAJOR_MINOR',0.92
 elif distance==1 and lx==ly:relation,score='ADJACENT_FIFTH',0.88
 elif distance==2 and lx==ly:relation,score='ENERGY_BOOST',0.78
 else:relation,score='CLASH',0.25
 options=(b,b*2,b/2)
 effective=min(options,key=lambda n:(abs(n/a-1),abs(n-b)))
 ratio=effective/a
 return HarmonicTransitionAnalysis(source_key,target_key,f'{x}{lx}',f'{y}{ly}',relation,score,float(a),float(b),float(effective),float(ratio),abs(ratio-1)*100<=allowed)

def _decode_pcm16(data):
 if type(data)!=bytes or len(data)>16*1024*1024:raise ValueError('INVALID_WAV_SIZE')
 try:
  with wave.open(io.BytesIO(data),'rb') as w:
   if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype())!=(2,2,44100,'NONE'):raise ValueError('PCM16_44100_STEREO_REQUIRED')
   n=w.getnframes();pcm=w.readframes(n)
   if n<1 or len(pcm)!=4*n:raise ValueError('TRUNCATED_WAV')
   return n,pcm
 except (wave.Error,EOFError) as e:raise ValueError('INVALID_WAV') from e

def crossfade_pcm16_wavs(source,target,*,fade_samples,equal_power=True):
 """Bounded deterministic two-deck transition; no resample or authorization."""
 n,a=_decode_pcm16(source);m,b=_decode_pcm16(target)
 if type(fade_samples)!=int or not 1<=fade_samples<=min(n,m):raise ValueError('INVALID_FADE_RANGE')
 x=struct.unpack('<'+'h'*(2*n),a);y=struct.unpack('<'+'h'*(2*m),b)
 out=bytearray(a[:4*(n-fade_samples)])
 for i in range(fade_samples):
  phase=(i+1)/(fade_samples+1)
  ga=math.cos(phase*math.pi/2) if equal_power else 1-phase
  gb=math.sin(phase*math.pi/2) if equal_power else phase
  for ch in (0,1):
   v=round(x[2*(n-fade_samples+i)+ch]*ga+y[2*i+ch]*gb)
   out+=struct.pack('<h',max(-32768,min(32767,v)))
 out+=b[4*fade_samples:]
 with io.BytesIO() as f:
  with wave.open(f,'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(bytes(out))
  return f.getvalue()
