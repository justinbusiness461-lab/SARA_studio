"""SJ3 Studio R35 read-only main promotion *preflight*, NEVER a merge authority.

A ticket is supplied by an operator, and the observed main / PR facts must be
independently read from canonical GitHub at promotion time. This pure checker
cannot authenticate those input facts, test logs, media, rights or provenance.
It can reject a stale/weak ticket, but can NEVER authorize a merge.
"""
from __future__ import annotations
import re


class PromotionTicketDenied(ValueError):
    """Malformed or adversarial promotion input."""

_SHA40 = re.compile(r'[0-9a-f]{40}\Z')
_SHA64 = re.compile(r'[0-9a-f]{64}\Z')
_TIME = re.compile(r'20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ\Z')
_OWNER = 'justinbusiness461-lab/SARA_studio'
_TICKET_FIELDS = frozenset({
    'schema','repository','candidatePR','candidateHeadSha',
    'qualifiedAgainstMainSha','qualifiedAgainstBaseSha',
    'qualificationReceiptDigest','requiredSuites','conservation',
    'knownBlockers','prerequisites','continuity','evidenceLevel',
    'owner','timestampUtc',
})
_OBSERVED_FIELDS = frozenset({
    'repository','mainSha','candidatePR','candidateHeadSha','candidateBaseSha',
})


def _sha(v, n):
    if not isinstance(v,str) or not (_SHA40 if n==40 else _SHA64).fullmatch(v) or v=='0'*n:
        raise PromotionTicketDenied('SHA_FORMAT_INVALID')


def _text(v):
    if not isinstance(v,str) or not v or len(v)>160 or v.strip()!=v:
        raise PromotionTicketDenied('TEXT_INVALID')


def _nonnegative_int(v):
    return type(v) is int and v>=0


def _validate(ticket, observed):
    if not isinstance(ticket,dict) or set(ticket)!=_TICKET_FIELDS:
        raise PromotionTicketDenied('TICKET_FIELDS_INVALID')
    if not isinstance(observed,dict) or set(observed)!=_OBSERVED_FIELDS:
        raise PromotionTicketDenied('OBSERVED_FIELDS_INVALID')
    if ticket['schema']!='sj3.studio.promotion-preflight.v1':
        raise PromotionTicketDenied('TICKET_SCHEMA_INVALID')
    for k in ('repository','owner','timestampUtc'):
        _text(ticket[k])
    if ticket['owner']!='STUDIO_ENGINEER_1':
        raise PromotionTicketDenied('MUTATION_OWNER_INVALID')
    if not _TIME.fullmatch(ticket['timestampUtc']):
        raise PromotionTicketDenied('TIME_INVALID')
    for p in (ticket,observed):
        if not _nonnegative_int(p['candidatePR']) or p['candidatePR']<1:
            raise PromotionTicketDenied('PR_INVALID')
    for k in ('candidateHeadSha','qualifiedAgainstMainSha','qualifiedAgainstBaseSha'):
        _sha(ticket[k],40)
    for k in ('mainSha','candidateHeadSha','candidateBaseSha'):
        _sha(observed[k],40)
    if ticket['qualificationReceiptDigest'] is not None:
        _sha(ticket['qualificationReceiptDigest'],64)
    elif ticket['evidenceLevel']=='E3':
        raise PromotionTicketDenied('QUALIFICATION_RECEIPT_REQUIRED_FOR_E3')
    cons=ticket['conservation']
    if not isinstance(cons,dict) or set(cons)!={'result','receiptDigest'} or cons['result'] not in ('PASS','HOLD','FAIL'):
        raise PromotionTicketDenied('CONSERVATION_INVALID')
    if cons['receiptDigest'] is not None:
        _sha(cons['receiptDigest'],64)
    elif cons['result']=='PASS':
        raise PromotionTicketDenied('CONSERVATION_RECEIPT_REQUIRED')
    suites=ticket['requiredSuites']
    if not isinstance(suites,dict) or set(suites)!={'python','node','chromium'}:
        raise PromotionTicketDenied('SUITE_INVENTORY_INVALID')
    for name, row in suites.items():
        if not isinstance(row,dict):
            raise PromotionTicketDenied('SUITE_INVALID_'+name)
        if row.get('result')=='NOT_EXECUTED' and set(row)=={'result'}:
            continue
        if set(row)!={'result','passed','failed','skipped','configured'} or row['result'] not in ('PASS','FAIL','PENDING'):
            raise PromotionTicketDenied('SUITE_INVALID_'+name)
        for k in ('passed','failed','skipped','configured'):
            if not _nonnegative_int(row[k]):
                raise PromotionTicketDenied('SUITE_COUNTER_INVALID')
        if row['configured']==0 or row['passed']+row['failed']+row['skipped']>row['configured']:
            raise PromotionTicketDenied('SUITE_COUNTS_INVALID')
    if ticket['evidenceLevel'] not in ('E0','E1','E2','E3'):
        raise PromotionTicketDenied('EVIDENCE_LEVEL_INVALID')
    if not isinstance(ticket['knownBlockers'],list) or len(ticket['knownBlockers'])>128:
        raise PromotionTicketDenied('BLOCKERS_INVALID')
    for b in ticket['knownBlockers']:_text(b)
    deps=ticket['prerequisites']
    if not isinstance(deps,list) or len(deps)>32:
        raise PromotionTicketDenied('PREREQUISITES_INVALID')
    names=set()
    for dep in deps:
        if not isinstance(dep,dict) or set(dep) not in ({'id','status'},{'id','status','artifactDigest'}):
            raise PromotionTicketDenied('PREREQUISITE_INVALID')
        _text(dep['id'])
        if dep['id'] in names:raise PromotionTicketDenied('PREREQUISITE_DUPLICATE')
        names.add(dep['id'])
        if dep['status'] not in ('QUALIFIED','UNVERIFIED','BLOCKED'):
            raise PromotionTicketDenied('PREREQUISITE_STATUS_INVALID')
        if dep['status']=='QUALIFIED':
            if 'artifactDigest' not in dep:raise PromotionTicketDenied('PREREQUISITE_PROOF_MISSING')
            _sha(dep['artifactDigest'],64)
        elif 'artifactDigest' in dep:
            raise PromotionTicketDenied('UNQUALIFIED_PREREQUISITE_HAS_PROOF')
    _text(ticket['continuity'])
    _text(observed['repository'])


def assess_ticket(ticket:dict, observed:dict)->dict:
    """Reject unsafe evidence; at strongest request independent human/CI review.

    `observed` must come from fresh, authenticated main/PR GitHub readbacks;
    this function cannot determine that fact by itself. No tool invocation,
    filesystem mutation, branch update or merge is performed.
    """
    _validate(ticket,observed)
    if ticket['repository']!=_OWNER or observed['repository']!=_OWNER or ticket['candidatePR']!=observed['candidatePR']:
        decision='WRONG_OWNER'
    elif ticket['qualifiedAgainstMainSha']!=observed['mainSha']:
        decision='STALE_MAIN'
    elif ticket['candidateHeadSha']!=observed['candidateHeadSha']:
        decision='STALE_CANDIDATE'
    elif ticket['qualifiedAgainstBaseSha']!=observed['candidateBaseSha']:
        decision='STALE_BASE'
    elif any(dep['status']!='QUALIFIED' for dep in ticket['prerequisites']):
        decision='CROSS_REPO_HOLD'
    elif (ticket['knownBlockers'] or ticket['conservation']['result']!='PASS' or
          ticket['continuity']!='RECOVERY_PACKET_CURRENT' or
          ticket['qualificationReceiptDigest'] is None or
          ticket['evidenceLevel']!='E3' or
          any(row.get('result')!='PASS' or row['failed'] or row['skipped'] or
              row['passed']!=row['configured'] for row in ticket['requiredSuites'].values())):
        decision='QUALIFICATION_HOLD'
    else:
        decision='REQUIRES_INDEPENDENT_REVIEW'
    return {'schema':'sj3.studio.promotion-preflight.result.v1',
            'status':decision, 'mergeAuthorized':False,
            'maxEvidenceLevel':'E2_SOURCE_AND_STRUCTURAL_PRECHECK',
            'candidateHeadSha':observed['candidateHeadSha'],
            'observedMainSha':observed['mainSha'],
            'verificationNote':'Caller must independently authenticate GitHub readback, tests, rights, prerequisite issuers and qualification receipts before separate serial main promotion.'}
