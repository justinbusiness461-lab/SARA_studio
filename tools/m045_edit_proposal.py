"""Non-authoritative fail-closed compound artist command compilation.
Validates exact canonical targets. NEVER commits SongSpec or audio.
"""
import re


def compile_compound_plan(command, song_spec):
    if not isinstance(command,str) or not 1<=len(command)<=2048 or not isinstance(song_spec,dict):
        raise ValueError('COMPOUND_INVALID_REQUEST')
    clauses=[s.strip().lower().rstrip('.') for s in re.split(r'\s*(?:,|;|\band\b)\s*',command,flags=re.I) if s.strip()]
    if not 1<=len(clauses)<=12:raise ValueError('COMPOUND_UNBOUNDED_CLAUSES')
    sections=song_spec.get('structure',{}).get('sections',[])
    tracks=song_spec.get('tracks',[])
    def section_named(name):
        vals=[s for s in sections if str(s.get('name','')).lower()==name or str(s.get('id','')).lower()==name.replace(' ','')]
        if len(vals)!=1:raise ValueError('COMPOUND_AMBIGUOUS_SECTION')
        return vals[0]
    def track_named(name):
        vals=[t for t in tracks if str(t.get('track_id','')).lower()==name or str(t.get('name','')).lower()==name]
        if len(vals)!=1:raise ValueError('COMPOUND_AMBIGUOUS_TRACK')
        return vals[0]
    locked_sections={s['id'] for s in sections if s.get('sonic_lock') is True}
    locked_tracks={t['track_id'] for t in tracks if t.get('sonic_lock') is True}
    preserved=set(locked_sections);operations=[];seen=set()
    for clause in clauses:
        if re.fullmatch(r'(?:keep|preserve|lock) (?:the )?(?:hook|chorus) (?:exactly )?(?:locked|unchanged|the same)?',clause):
            preserved.add(section_named('chorus')['id']);continue
        if re.fullmatch(r'(?:slow down|slow|relax) (?:the )?(?:middle verse|verse 2|second verse)(?: a little)?',clause):
            # The real ScoreCore SongSpec uses repeated name='Verse' and
            # canonical start_tick IDs, not necessarily a literal 'v2' ID.
            verses=sorted([s for s in sections if str(s.get('type','')).lower()=='verse'
                or str(s.get('name','')).lower() in ('verse','verse 2','second verse')
                or s.get('id')=='v2'],key=lambda s:s.get('start_tick',0))
            if len(verses)>=2:sec=verses[1]
            elif len(verses)==1 and (str(verses[0].get('name','')).lower() in ('verse 2','second verse')
                    or verses[0].get('id')=='v2'):sec=verses[0]
            else:raise ValueError('COMPOUND_SECOND_VERSE_NOT_IDENTIFIABLE')
            if sec['id'] in locked_sections:raise ValueError('COMPOUND_LOCKED_SECTION')
            key=('vocalPhrasing',sec['id']);operation={'kind':'vocalPhrasing','sectionId':sec['id'],'preservationTier':'P3','targetScope':{'sectionId':sec['id']},'status':'PROPOSAL_ONLY'}
        elif re.fullmatch(r'(?:darken (?:the )?bass|make (?:the )?bass darker|give (?:the )?bass a darker tone)',clause):
            track=track_named('bass')
            if track['track_id'] in locked_tracks:raise ValueError('COMPOUND_LOCKED_TRACK')
            key=('filter',track['track_id']);operation={'kind':'filter','trackId':track['track_id'],'preservationTier':'P2','targetScope':{'trackId':track['track_id']},'status':'PROPOSAL_ONLY'}
        elif re.fullmatch(r'(?:add|insert) (?:a |some )?(?:weird )?metallic (?:percussion(?: sound)?|sound)',clause):
            track=track_named('percussion')
            if track['track_id'] in locked_tracks:raise ValueError('COMPOUND_LOCKED_TRACK')
            key=('metallic',track['track_id']);operation={'kind':'metallic','trackId':track['track_id'],'preservationTier':'P2','targetScope':{'trackId':track['track_id']},'status':'PROPOSAL_ONLY'}
        else:
            if 'hook' in clause or 'chorus' in clause:raise ValueError('COMPOUND_LOCKED_OR_UNSUPPORTED_HOOK')
            raise ValueError('COMPOUND_UNSUPPORTED_CLAUSE')
        if key in seen:raise ValueError('COMPOUND_COLLIDING_OPERATIONS')
        seen.add(key);operations.append(operation)
    if not operations:raise ValueError('COMPOUND_NO_EDIT')
    return {'schemaVersion':'sara.compound-edit-plan.v1','operations':operations,'preservedSectionIds':sorted(preserved),'revisionCommitted':False,'audioPreservationProof':'NOT_CLAIMED','requiresApproval':True}