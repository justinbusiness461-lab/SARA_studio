"""SJ3 Studio R35 promotion preflight -- read-only, never a merge issuer."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from studio_promotion_ticket import assess_ticket, PromotionTicketDenied

C = 'a'*40
M = 'b'*40
B = 'c'*40
D = 'd'*64

def ticket():
    return {
        'schema': 'sj3.studio.promotion-preflight.v1',
        'repository': 'justinbusiness461-lab/SARA_studio',
        'candidatePR': 44, 'candidateHeadSha': C,
        'qualifiedAgainstMainSha': M, 'qualifiedAgainstBaseSha': B,
        'qualificationReceiptDigest': D,
        'requiredSuites': {
            'python': {'passed': 42, 'failed': 0, 'skipped': 0, 'configured': 42, 'result':'PASS'},
            'node': {'passed': 21, 'failed': 0, 'skipped': 0, 'configured': 21, 'result':'PASS'},
            'chromium': {'passed': 9, 'failed': 0, 'skipped': 0, 'configured': 9, 'result':'PASS'},
        },
        'conservation': {'result': 'PASS', 'receiptDigest': D},
        'knownBlockers': [], 'prerequisites': [],
        'continuity': 'RECOVERY_PACKET_CURRENT',
        'evidenceLevel': 'E3',
        'owner':'STUDIO_ENGINEER_1',
        'timestampUtc':'2026-11-25T23:59:00Z',
    }

def observed():
    return {'repository':'justinbusiness461-lab/SARA_studio',
        'mainSha':M, 'candidatePR':44, 'candidateHeadSha':C,
        'candidateBaseSha':B}

class PromotionGateTests(unittest.TestCase):
    def test_even_completely_consistent_ticket_is_not_authority(self):
        r=assess_ticket(ticket(),observed())
        self.assertEqual(r['status'], 'REQUIRES_INDEPENDENT_REVIEW')
        self.assertFalse(r['mergeAuthorized'])
        self.assertEqual(r['maxEvidenceLevel'],'E2_SOURCE_AND_STRUCTURAL_PRECHECK')

    def test_main_change_stales_ticket_even_if_other_evidence_passes(self):
        x=observed();x['mainSha']='e'*40
        r=assess_ticket(ticket(),x)
        self.assertEqual(r['status'],'STALE_MAIN')
        self.assertFalse(r['mergeAuthorized'])

    def test_candidate_head_change_invalidates_ticket(self):
        x=observed();x['candidateHeadSha']='e'*40
        self.assertEqual(assess_ticket(ticket(),x)['status'],'STALE_CANDIDATE')

    def test_parent_base_change_invalidates_stacked_pr(self):
        x=observed();x['candidateBaseSha']='e'*40
        self.assertEqual(assess_ticket(ticket(),x)['status'],'STALE_BASE')

    def test_repo_and_pr_owner_mismatch_denied(self):
        for mutation in [('repository','justinbusiness461-lab/dj_rezrxtion'),('candidatePR',98)]:
            x=ticket();x[mutation[0]]=mutation[1]
            self.assertEqual(assess_ticket(x,observed())['status'],'WRONG_OWNER')

    def test_incomplete_broken_or_skipped_suites_do_not_qualify(self):
        for name,field,value in [('python','result','PENDING'),('node','failed',1),('chromium','skipped',1),('chromium','passed',0),('python','configured',50)]:
            with self.subTest(name=name,field=field,value=value):
                x=ticket();x['requiredSuites'][name][field]=value
                if field in ('failed','skipped'):
                    x['requiredSuites'][name]['passed']-=value
                self.assertEqual(assess_ticket(x,observed())['status'],'QUALIFICATION_HOLD')

    def test_full_browser_missing_cannot_be_replaced_by_focused_unit(self):
        x=ticket();x['requiredSuites']['chromium']={'result':'NOT_EXECUTED'}
        self.assertEqual(assess_ticket(x,observed())['status'],'QUALIFICATION_HOLD')

    def test_e2_is_not_physical_qualification(self):
        x=ticket();x['evidenceLevel']='E2'
        self.assertEqual(assess_ticket(x,observed())['status'],'QUALIFICATION_HOLD')

    def test_cross_repo_prerequisite_cannot_be_inherited(self):
        x=ticket();x['prerequisites']=[{'id':'DENIAL_01', 'status':'UNVERIFIED'}]
        self.assertEqual(assess_ticket(x,observed())['status'],'CROSS_REPO_HOLD')

    def test_claimed_qualified_prerequisite_still_needs_independent_review(self):
        x=ticket();x['prerequisites']=[{'id':'DENIAL_01','status':'QUALIFIED', 'artifactDigest':D}]
        self.assertEqual(assess_ticket(x,observed())['status'],'REQUIRES_INDEPENDENT_REVIEW')

    def test_known_blocker_denies_qualification(self):
        x=ticket();x['knownBlockers']=['STUDIO_ACCEPTED_PCM_LINEAGE_MISSING']
        self.assertEqual(assess_ticket(x,observed())['status'],'QUALIFICATION_HOLD')

    def test_stale_continuity_denies_qualification(self):
        x=ticket();x['continuity']='RECOVERY_PACKET_STALE'
        self.assertEqual(assess_ticket(x,observed())['status'],'QUALIFICATION_HOLD')

    def test_invalid_or_forged_digest_and_bool_counts_denied(self):
        for fn in [lambda x:x.update(qualificationReceiptDigest='z'*64),
                    lambda x:x.update(qualificationReceiptDigest='0'*64),
                    lambda x:x['requiredSuites']['python'].update(passed=True),
                    lambda x:x['conservation'].update(receiptDigest='0'),
                    lambda x:x.update(candidateHeadSha='a'*39),
                    lambda x:x.update(evidenceLevel='E6')]:
            with self.subTest(fn=fn):
                x=ticket();fn(x)
                with self.assertRaises(PromotionTicketDenied):assess_ticket(x,observed())

    def test_surplus_fields_and_garbage_observation_denied(self):
        x=ticket();x['skipChecks']=True
        with self.assertRaises(PromotionTicketDenied):assess_ticket(x,observed())
        with self.assertRaises(PromotionTicketDenied):assess_ticket(ticket(),{'mainSha':M})

    def test_missing_receipts_allowed_only_as_hold_and_never_as_e3_proof(self):
        x=ticket();x['qualificationReceiptDigest']=None;x['evidenceLevel']='E2';x['conservation']={'result':'HOLD','receiptDigest':None}
        self.assertEqual(assess_ticket(x,observed())['status'],'QUALIFICATION_HOLD')
        x['evidenceLevel']='E3'
        with self.assertRaises(PromotionTicketDenied):assess_ticket(x,observed())

    def test_unknown_prerequisite_state_denied(self):
        x=ticket();x['prerequisites']=[{'id':'DENIAL_01','status':'AUTHENTICATED'}]
        with self.assertRaises(PromotionTicketDenied):assess_ticket(x,observed())

if __name__=='__main__': unittest.main()
