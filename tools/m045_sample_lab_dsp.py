"""Deterministic bounded PCM16 Stereo SampleLab transforms; no CAS writes."""
import io,math,struct,wave

def _read(data):
    if not isinstance(data,bytes) or len(data)>16*1024*1024:raise ValueError('SAMPLE_BYTES_INVALID')
    try:
        with wave.open(io.BytesIO(data),'rb') as w:
            if w.getcomptype()!='NONE' or w.getsampwidth()!=2 or w.getnchannels()!=2 or w.getframerate() not in (44100,48000):raise ValueError('SAMPLE_FORMAT_UNSUPPORTED')
            if w.getnframes()>w.getframerate()*10:raise ValueError('SAMPLE_FX_INPUT_EXCEEDS_TEN_SECOND_PREVIEW')
            return w.getframerate(),list(struct.iter_unpack('<hh',w.readframes(w.getnframes())))
    except (wave.Error,EOFError,struct.error) as ex:raise ValueError('SAMPLE_DECODE_INVALID') from ex

def _write(rate,samples):
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<hh',max(-32768,min(32767,round(a))),max(-32768,min(32767,round(b)))) for a,b in samples))
    return out.getvalue()

def slice_sample(source,start_frame,end_frame):
    """Exact frame-selective read: never expand an entire long WAV into tuples."""
    if not isinstance(source,bytes) or len(source)>16*1024*1024:raise ValueError('SAMPLE_BYTES_INVALID')
    if type(start_frame)!=int or type(end_frame)!=int or start_frame<0 or end_frame<=start_frame:
        raise ValueError('SAMPLE_SLICE_BOUNDS')
    try:
        with wave.open(io.BytesIO(source),'rb') as w:
            if w.getcomptype()!='NONE' or w.getsampwidth()!=2 or w.getnchannels()!=2 or w.getframerate() not in (44100,48000):raise ValueError('SAMPLE_FORMAT_UNSUPPORTED')
            if end_frame>w.getnframes() or end_frame-start_frame>w.getframerate()*10:raise ValueError('SAMPLE_SLICE_BOUNDS')
            rate=w.getframerate();w.setpos(start_frame);frames=w.readframes(end_frame-start_frame)
    except (wave.Error,EOFError) as exc:raise ValueError('SAMPLE_DECODE_INVALID') from exc
    if len(frames)!=(end_frame-start_frame)*4:raise ValueError('SAMPLE_TRUNCATED')
    output=io.BytesIO()
    with wave.open(output,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes(frames)
    return output.getvalue()

def resonant_lowpass(source,cutoff_hz,q=0.707):
    rate,frames=_read(source)
    if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in (cutoff_hz,q)) or not 20<=cutoff_hz<=rate*.45 or not .5<=q<=5:raise ValueError('FILTER_PARAMETERS_INVALID')
    omega=2*math.pi*cutoff_hz/rate;alpha=math.sin(omega)/(2*q)
    a0=1+alpha;a1=-2*math.cos(omega)/a0;a2=(1-alpha)/a0
    b0=((1-math.cos(omega))/2)/a0;b1=(1-math.cos(omega))/a0;b2=b0
    history=[[0.0]*4 for _ in range(2)];output=[]
    for pair in frames:
        values=[]
        for ch,x0 in enumerate(pair):
            x0=float(x0);x1,x2,y1,y2=history[ch]
            y0=b0*x0+b1*x1+b2*x2-a1*y1-a2*y2
            history[ch]=[x0,x1,y0,y1];values.append(y0)
        output.append(values)
    return _write(rate,output)

def metallic_comb(source,delay_ms=3,feedback=.55):
    rate,frames=_read(source)
    if not isinstance(delay_ms,(int,float)) or not isinstance(feedback,(int,float)) or not math.isfinite(delay_ms) or not math.isfinite(feedback) or not 1<=delay_ms<=30 or not 0<=feedback<=.85:raise ValueError('COMB_PARAMETERS_INVALID')
    delay=max(1,round(rate*delay_ms/1000));ring=[[0.0,0.0] for _ in range(delay)];out=[]
    for i,(a,b) in enumerate(frames):
        slot=i%delay;old=ring[slot];result=[a+feedback*old[0],b+feedback*old[1]]
        ring[slot]=result;out.append(result)
    return _write(rate,out)


def rate_pitch_shift(source,semitones=0):
    """P3 varispeed: pitch and duration are COUPLED; NOT independent time-stretch."""
    rate,frames=_read(source)
    if type(semitones) not in (int,float) or not math.isfinite(semitones) or abs(semitones)>24:
        raise ValueError('VARISPEED_SEMITONES_INVALID')
    factor=2**(semitones/12)
    count=max(1,int(round(len(frames)/factor)))
    if count>rate*90:raise ValueError('VARISPEED_DURATION_UNQUALIFIED')
    shifted=[]
    for i in range(count):
        position=i*factor;left=min(len(frames)-1,int(position));right=min(len(frames)-1,left+1)
        t=min(1.,position-left)
        shifted.append(tuple(frames[left][channel]*(1-t)+frames[right][channel]*t for channel in range(2)))
    return _write(rate,shifted)


def apply_effect_graph(source,nodes,output_id):
    """Bounded single-parent DAG of deterministic audio effects; no browser/cache-owned graph."""
    if not isinstance(nodes,list) or not 1<=len(nodes)<=16 or not isinstance(output_id,str):
        raise ValueError('FX_GRAPH_INVALID')
    values={'source':source}
    for node in nodes:
        if not isinstance(node,dict) or set(node) not in (
            {'id','operation','input','cutoffHz','q'},
            {'id','operation','input','delayMs','feedback'},
            {'id','operation','input','semitones'},
            {'id','operation','input','startFrame','endFrame'}):
            raise ValueError('FX_NODE_SCHEMA_INVALID')
        key=node['id'];parent=node['input'];op=node['operation']
        if not isinstance(key,str) or not key or key in values or parent not in values:
            raise ValueError('FX_GRAPH_CYCLE_OR_MISSING_PARENT')
        sound=values[parent]
        if op=='lowpass' and 'cutoffHz' in node:
            result=resonant_lowpass(sound,cutoff_hz=node['cutoffHz'],q=node['q'])
        elif op=='metallic_comb' and 'delayMs' in node:
            result=metallic_comb(sound,delay_ms=node['delayMs'],feedback=node['feedback'])
        elif op=='rate_pitch' and 'semitones' in node:
            result=rate_pitch_shift(sound,semitones=node['semitones'])
        elif op=='slice' and 'startFrame' in node:
            result=slice_sample(sound,start_frame=node['startFrame'],end_frame=node['endFrame'])
        else:raise ValueError('FX_OPERATION_UNSUPPORTED')
        values[key]=result
    if output_id not in values or output_id=='source':raise ValueError('FX_OUTPUT_UNQUALIFIED')
    return values[output_id]