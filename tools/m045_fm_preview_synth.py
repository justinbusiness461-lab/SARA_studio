"""Independent four-operator FM preview synth (no provider, no CAS write).
Deterministic stereo PCM16, bounded song duration. Not a quality-certified master.
"""
from __future__ import annotations
from fractions import Fraction
import io,math,struct,wave
SAMPLE_RATE=44100
PATCHES={
 'fm_bass':((1.0,1.0,2.0,3.0),(1.5,0.8,0.4),0.16),
 'fm_epiano':((1.0,2.0,3.0,4.0),(1.1,0.6,0.2),0.46),
 'fm_lead':((1.0,1.0,4.0,2.0),(2.1,0.9,0.7),0.6),
}
def _frac(v,label):
 if type(v) not in (int,float,str,Fraction) or isinstance(v,bool):raise ValueError('INVALID_'+label)
 try:
  if isinstance(v,float) and not math.isfinite(v):raise ValueError()
  x=Fraction(str(v))
 except (ValueError,ZeroDivisionError) as e:raise ValueError('INVALID_'+label) from e
 if x<=0:raise ValueError('INVALID_'+label)
 return x

def _round(x):return (2*x.numerator+x.denominator)//(2*x.denominator)

def render_fm_preview_wav(*,notes,bpm,ppq=960,total_bars=4,beats_per_bar=4,patch='fm_bass'):
 if not isinstance(notes,list) or len(notes)>256:raise ValueError('INVALID_NOTE_ARRAY')
 if type(ppq)!=int or ppq!=960 or type(total_bars)!=int or type(beats_per_bar)!=int or not 1<=total_bars<=64 or not 1<=beats_per_bar<=12:raise ValueError('UNSUPPORTED_TIMEBASE')
 if patch not in PATCHES:raise ValueError('UNKNOWN_FM_PATCH')
 speed=_frac(bpm,'BPM')
 if not 20<=speed<=320:raise ValueError('BPM_OUT_OF_RANGE')
 max_ticks=total_bars*beats_per_bar*ppq
 per_tick=Fraction(60*SAMPLE_RATE,1)/(speed*ppq)
 total=_round(max_ticks*per_tick)
 if total>12*SAMPLE_RATE:raise ValueError('PREVIEW_TOO_LONG')
 left=[0.0]*total;right=[0.0]*total
 ratios,indices,decay=PATCHES[patch]
 for event in notes:
  if not isinstance(event,dict):raise ValueError('NOTE_REQUIRED')
  midi=event.get('midi_note');start=event.get('start_tick');length=event.get('duration_ticks');velocity=event.get('velocity',100)
  if any(type(v)!=int for v in (midi,start,length,velocity)) or not 0<=midi<=127 or start<0 or length<=0 or start+length>max_ticks or not 1<=velocity<=127:raise ValueError('INVALID_NOTE')
  a=_round(start*per_tick);b=min(total,_round((start+length)*per_tick))
  if b<=a:raise ValueError('NOTE_COLLAPSED_BY_QUANTIZATION')
  hz=440*2**((midi-69)/12)
  pan=((midi%12)-5.5)/44
  lg=0.27*(velocity/127)*math.cos((pan+1)*math.pi/4)
  rg=0.27*(velocity/127)*math.sin((pan+1)*math.pi/4)
  attack=max(1,int(0.005*SAMPLE_RATE));release=max(1,min(int(0.015*SAMPLE_RATE),(b-a)//3))
  for j in range(b-a):
   tm=j/SAMPLE_RATE
   env=math.exp(-tm/decay)*min(1,j/attack,(b-a-j)/release)
   # Four operators: OP4->OP3->OP2->OP1; carrier OP1.
   p4=math.sin(2*math.pi*ratios[3]*hz*tm)
   p3=math.sin(2*math.pi*ratios[2]*hz*tm+indices[2]*p4)
   p2=math.sin(2*math.pi*ratios[1]*hz*tm+indices[1]*p3)
   sig=env*math.sin(2*math.pi*ratios[0]*hz*tm+indices[0]*p2)
   left[a+j]+=sig*lg;right[a+j]+=sig*rg
 raw=bytearray(total*4)
 for i,(l,r) in enumerate(zip(left,right)):
  struct.pack_into('<hh',raw,4*i,int(32767*math.tanh(l)),int(32767*math.tanh(r)))
 buf=io.BytesIO()
 with wave.open(buf,'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(SAMPLE_RATE);w.writeframes(raw)
 return buf.getvalue()
