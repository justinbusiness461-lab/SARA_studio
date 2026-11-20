"""Native bounded mono stem transcription candidates and loss-reported score exports.
P3 audio DOES NOT become P0 audio merely because notes were estimated.
The source digest establishes identity, NOT project/artifact authorization.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from xml.etree import ElementTree as ET
import hashlib,io,math,struct,wave
PPQ=960
RATE=44100
PITCHES=('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
@dataclass(frozen=True)
class TranscribedNoteEvent:
 event_id:str
 midi_note:int
 pitch_name:str
 start_tick:int
 duration_ticks:int
 velocity:int
 confidence:float
@dataclass(frozen=True)
class AudioToMidiPromotionReceipt:
 source_artifact_sha256:str
 bpm:float
 ppq:int
 quantize_grid_ticks:int
 notes_detected:int
 promoted_preservation_tier:str
 loss_report:dict
 notes:list[TranscribedNoteEvent]

def midi_to_pitch_name(note):
 if type(note)!=int or not 0<=note<=127:raise ValueError('INVALID_MIDI_NOTE')
 return f'{PITCHES[note%12]}{note//12-1}'

def _nearest(value:Fraction)->int:
 return (2*value.numerator+value.denominator)//(2*value.denominator)

def _speed(value):
 if type(value) not in (float,int,str,Fraction) or isinstance(value,bool):raise ValueError('INVALID_BPM')
 try:
  if type(value) is float and not math.isfinite(value):raise ValueError()
  v=Fraction(str(value))
 except (ValueError,ZeroDivisionError) as exc:raise ValueError('INVALID_BPM') from exc
 if not 20<=v<=320:raise ValueError('INVALID_BPM')
 return v

def _decode(data):
 if type(data)!=bytes or not 44<=len(data)<=16*1024*1024:raise ValueError('INVALID_WAV_INPUT')
 try:
  with wave.open(io.BytesIO(data),'rb') as w:
   ch=w.getnchannels();rate=w.getframerate();width=w.getsampwidth();n=w.getnframes()
   if rate!=RATE or width!=2 or ch not in (1,2) or w.getcomptype()!='NONE' or n<1 or n>RATE*20:raise ValueError('UNSUPPORTED_WAV_ENCODING')
   raw=w.readframes(n)
   if len(raw)!=n*ch*2:raise ValueError('TRUNCATED_WAV')
 except (wave.Error,EOFError) as exc:raise ValueError('INVALID_WAV_ENCODING') from exc
 values=struct.unpack('<'+str(n*ch)+'h',raw)
 samples=[values[i]/32768 if ch==1 else (values[i*2]+values[i*2+1])/65536 for i in range(n)]
 return samples,n

def _pitch(window,rate=RATE):
 """Normalized mono autocorrelation after 6:1 short-average reduction.
 Suitable only for isolated sustained monophonic notes, not full-song polyphony.
 """
 if not window:return 0,0.0
 energy=sum(x*x for x in window)/len(window)
 if energy<0.0004:return 0,0.0
 factor=6
 short=[sum(window[i:i+factor])/factor for i in range(0,len(window)-factor+1,factor)]
 sampling=rate/factor
 mn=max(2,round(sampling/1100));mx=min(len(short)//2,round(sampling/48))
 correlations=[]
 for lag in range(mn,mx+1):
  a=short[:-lag];b=short[lag:]
  num=sum(x*y for x,y in zip(a,b))
  den=math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
  correlations.append((num/den if den>1e-12 else 0.0,lag))
 if not correlations:return 0,0.0
 best=max(correlations)[0]
 peaks=[]
 for i in range(1,len(correlations)-1):
  corr,lag=correlations[i]
  if corr>=0.62 and corr>=best-0.065 and corr>=correlations[i-1][0] and corr>=correlations[i+1][0]:peaks.append((lag,corr))
 if not peaks:return 0,best
 lag,score=min(peaks,key=lambda p:p[0])
 note=round(69+12*math.log2((sampling/lag)/440))
 if note<21 or note>108:return 0,score
 return int(note),round(score,4)

def transcribe_wav_to_scorecore_notes(*,wav_bytes,bpm,quantize_subdivision_ticks=240):
 tempo=_speed(bpm)
 if type(quantize_subdivision_ticks)!=int or quantize_subdivision_ticks<=0 or PPQ%quantize_subdivision_ticks:raise ValueError('UNSUPPORTED_GRID')
 mono,n=_decode(wav_bytes)
 window=round(.12*RATE);hop=round(.04*RATE);detections=[]
 for start in range(0,max(1,n-window+1),hop):
  signal=mono[start:start+window]
  if len(signal)<window:break
  pitch,confidence=_pitch(signal)
  detections.append((start,pitch,confidence))
 if not detections:
  return AudioToMidiPromotionReceipt(hashlib.sha256(wav_bytes).hexdigest(),float(tempo),PPQ,quantize_subdivision_ticks,0,'P3_RECONSTRUCTION',{'transcription_is_estimated':True,'polyphony_not_supported':True,'timbre_and_formants_discarded':True,'error':'INSUFFICIENT_AUDIO'},[])
 cleaned=[]
 for j,(start,pitch,conf) in enumerate(detections):
  before=detections[j-1][1] if j else 0
  after=detections[j+1][1] if j+1<len(detections) else 0
  if pitch!=before and pitch!=after and before==after:pitch=before
  cleaned.append((start,pitch,conf))
 runs=[];current=cleaned[0][1];first=cleaned[0][0];scores=[]
 for pos,pitch,conf in cleaned:
  if pitch!=current:
   if current and scores:runs.append((first,pos,current,sum(scores)/len(scores)))
   current=pitch;first=pos;scores=[]
  if pitch:scores.append(conf)
 if current and scores:runs.append((first,n,current,sum(scores)/len(scores)))
 convert=Fraction(PPQ)*tempo/(60*RATE);notes=[];shifts=[]
 for i,(s,e,midi,confidence) in enumerate(runs):
  starttick=_nearest(Fraction(s)*convert/quantize_subdivision_ticks)*quantize_subdivision_ticks
  endtick=_nearest(Fraction(e)*convert/quantize_subdivision_ticks)*quantize_subdivision_ticks
  duration=max(quantize_subdivision_ticks,endtick-starttick)
  if notes and starttick<notes[-1].start_tick+notes[-1].duration_ticks:
   starttick=notes[-1].start_tick+notes[-1].duration_ticks
  if e-s<round(RATE*.075):continue
  shifts.append(float(abs(Fraction(s)*convert-starttick)))
  notes.append(TranscribedNoteEvent(f'tx_{i+1:04d}',midi,midi_to_pitch_name(midi),starttick,duration,95,round(confidence,4)))
 return AudioToMidiPromotionReceipt(hashlib.sha256(wav_bytes).hexdigest(),float(tempo),PPQ,quantize_subdivision_ticks,len(notes),'P3_RECONSTRUCTION',{
  'transcription_is_estimated':True,'polyphony_not_supported':True,'repeated_identical_pitches_may_merge':True,
  'microtiming_quantized_to_ticks':quantize_subdivision_ticks,'max_estimated_start_shift_ticks':max(shifts,default=0),
  'timbre_and_formants_discarded':True,'expression_and_pitch_bends_discarded':True,
  'independent_audio_p0_preservation':False,'requires_human_review':True},notes)

def _validate_notes(notes):
 if not isinstance(notes,(list,tuple)) or len(notes)>8192:raise ValueError('INVALID_NOTE_SET')
 out=[]
 for e in notes:
  if not isinstance(e,TranscribedNoteEvent) or any(type(v)!=int for v in (e.midi_note,e.start_tick,e.duration_ticks,e.velocity)) or not 0<=e.midi_note<=127 or e.start_tick<0 or e.duration_ticks<=0 or e.start_tick+e.duration_ticks>10000000 or not 1<=e.velocity<=127:raise ValueError('INVALID_EVENT')
  out.append(e)
 return sorted(out,key=lambda e:(e.start_tick,e.midi_note,e.event_id))

def export_scorecore_notes_to_musicxml(notes,title='S.A.R.A. Transcribed Part'):
 """Monophonic 4/4 chronological score with rests and cross-bar ties."""
 events=_validate_notes(notes)
 if type(title)!=str or len(title)>200:raise ValueError('INVALID_TITLE')
 root=ET.Element('score-partwise',{'version':'3.1'})
 work=ET.SubElement(root,'work');ET.SubElement(work,'work-title').text=title
 partlist=ET.SubElement(root,'part-list');scorepart=ET.SubElement(partlist,'score-part',{'id':'P1'});ET.SubElement(scorepart,'part-name').text='Transcribed stem candidate'
 part=ET.SubElement(root,'part',{'id':'P1'});measure_ticks=PPQ*4
 end=max((e.start_tick+e.duration_ticks for e in events),default=measure_ticks)
 n_measures=max(1,(end+measure_ticks-1)//measure_ticks)
 if n_measures>3000:raise ValueError('SCORE_TOO_LONG')
 measures=[ET.SubElement(part,'measure',{'number':str(i+1)}) for i in range(n_measures)]
 attrs=ET.SubElement(measures[0],'attributes');ET.SubElement(attrs,'divisions').text=str(PPQ)
 time=ET.SubElement(attrs,'time');ET.SubElement(time,'beats').text='4';ET.SubElement(time,'beat-type').text='4'
 def node(measure,pitch,duration,starttie=False,endtie=False):
  e=ET.SubElement(measure,'note')
  if pitch is None:ET.SubElement(e,'rest')
  else:
   p=ET.SubElement(e,'pitch');pc=pitch%12;steps=['C','C','D','D','E','F','F','G','G','A','A','B']
   ET.SubElement(p,'step').text=steps[pc]
   if pc in (1,3,6,8,10):ET.SubElement(p,'alter').text='1'
   ET.SubElement(p,'octave').text=str(pitch//12-1)
  ET.SubElement(e,'duration').text=str(duration)
  if starttie:ET.SubElement(e,'tie',{'type':'start'})
  if endtie:ET.SubElement(e,'tie',{'type':'stop'})
  if starttie or endtie:
   marks=ET.SubElement(e,'notations')
   if endtie:ET.SubElement(marks,'tied',{'type':'stop'})
   if starttie:ET.SubElement(marks,'tied',{'type':'start'})
 def write_range(start,end,pitch):
  at=start
  while at<end:
   bound=min(end,(at//measure_ticks+1)*measure_ticks)
   node(measures[at//measure_ticks],pitch,bound-at,pitch is not None and bound<end,pitch is not None and at>start)
   at=bound
 cursor=0
 for e in events:
  if e.start_tick<cursor:raise ValueError('OVERLAPPING_POLYPHONIC_EXPORT_UNSUPPORTED')
  if e.start_tick>cursor:write_range(cursor,e.start_tick,None)
  write_range(e.start_tick,e.start_tick+e.duration_ticks,e.midi_note)
  cursor=e.start_tick+e.duration_ticks
 if cursor<n_measures*measure_ticks:write_range(cursor,n_measures*measure_ticks,None)
 return '<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(root,encoding='unicode')+'\n'

def _vlq(value):
 if type(value)!=int or not 0<=value<2**28:raise ValueError('MIDI_DELTA_OUT_OF_RANGE')
 data=[value&127];value>>=7
 while value:data.insert(0,0x80|(value&127));value>>=7
 return bytes(data)

def _track(events):
 payload=bytearray();last=0
 for at,priority,data in sorted(events,key=lambda e:(e[0],e[1])):
  if at<last:raise ValueError('MIDI_EVENT_ORDER')
  payload+=_vlq(at-last)+data;last=at
 payload+=b'\x00\xff\x2f\x00'
 return b'MTrk'+struct.pack('>I',len(payload))+payload

def export_scorecore_notes_to_smf(notes,*,bpm,smf_type=1):
 events=_validate_notes(notes);tempo=_speed(bpm)
 if type(smf_type)!=int or smf_type not in (0,1):raise ValueError('SMF_TYPE_UNSUPPORTED')
 micros=round(60000000/float(tempo))
 if not 1<=micros<=0xFFFFFF:raise ValueError('MIDI_TEMPO_OVERFLOW')
 tempo_event=(0,0,b'\xff\x51\x03'+micros.to_bytes(3,'big'))
 midi=[]
 for e in events:
  midi.append((e.start_tick,2,bytes((0x90,e.midi_note,e.velocity))))
  midi.append((e.start_tick+e.duration_ticks,1,bytes((0x80,e.midi_note,0))))
 tracks=[_track([tempo_event]+midi)] if smf_type==0 else [_track([tempo_event]),_track(midi)]
 return b'MThd'+struct.pack('>IHHH',6,smf_type,len(tracks),PPQ)+b''.join(tracks)
