"""R10-A RED: no cloud execution; typed bounded trial and existing WAV proof."""
import hashlib, unittest, os
from pathlib import Path
from unittest.mock import patch
from test_platform_identity_and_catalog import fixture_wav

SRC=Path(__file__).resolve().parents[1]/'deploy'/'modal_acestep.py'

class BoundedTrial(unittest.TestCase):
 def setUp(self):
  self.req={'mode':'ZERO_SPEND_DRY_RUN','execute':False,'operation':'FULL_SONG',
    'requestedDurationSec':20,'httpTimeoutSec':120,'maxSpendUsd':1.0,'gpuSecondsCap':120}
  self.env={'SARA_GATE3_SPEND_AUTHORIZED':'1',
    'SARA_ACESTEP_ENDPOINT_URL':'https://stage-example.modal.run',
    'SARA_ACESTEP_API_KEY':'a'*40}
 def test_full_song_dry_run_redacts_host_secret_and_never_authorizes_external_spend(self):
  from m045_modal_trial_runner import prepare_gate3_trial
  receipt=prepare_gate3_trial(SRC,self.req,self.env)
  self.assertEqual(receipt['state'],'DRY_RUN_ONLY')
  self.assertFalse(receipt['gpuAllocated'])
  self.assertFalse(receipt['trialAuthorized'])
  self.assertFalse(receipt['remoteExecutionEnabled'])
  self.assertEqual(receipt['chargesIncurredUsd'],0)
  self.assertEqual(receipt['maxConcurrentInputs'],1)
  self.assertEqual(receipt['maxContainers'],1)
  self.assertEqual(receipt['requestedDurationSec'],20)
  self.assertEqual(len(receipt['sourceSha256']),64)
  self.assertEqual(len(receipt['auditDigest']),64)
  self.assertNotIn(self.env['SARA_ACESTEP_API_KEY'],str(receipt))
  self.assertNotIn(self.env['SARA_ACESTEP_ENDPOINT_URL'],str(receipt))
 def test_spend_flag_absent_disabled_does_not_qualify_trial(self):
  from m045_modal_trial_runner import prepare_gate3_trial
  for flag in (None,'0','true','yes',' 1 '):
   env=dict(self.env)
   if flag is None:env.pop('SARA_GATE3_SPEND_AUTHORIZED')
   else:env['SARA_GATE3_SPEND_AUTHORIZED']=flag
   with self.subTest(flag=flag),self.assertRaises(ValueError):prepare_gate3_trial(SRC,self.req,env)
 def test_malformed_host_request_and_unsafe_budget_rejected(self):
  from m045_modal_trial_runner import prepare_gate3_trial
  for key,value in (('requestedDurationSec',20.1),('requestedDurationSec',0),('httpTimeoutSec',181),
     ('maxSpendUsd',1.01),('maxSpendUsd',float('nan')),('execute',True),('mode','EXECUTE_GPU'),
     ('operation','UNKNOWN'),('gpuSecondsCap',601),('httpTimeoutSec',0)):
   with self.subTest(key=key,value=value),self.assertRaises(ValueError):
    prepare_gate3_trial(SRC,{**self.req,key:value},self.env)
  for key,value in (('SARA_ACESTEP_ENDPOINT_URL','http://stage-example.modal.run'),
      ('SARA_ACESTEP_ENDPOINT_URL','https://attacker.example.com'),
      ('SARA_ACESTEP_ENDPOINT_URL','https://user@stage-example.modal.run'),
      ('SARA_ACESTEP_API_KEY','short')):
   with self.subTest(env=key,value=value),self.assertRaises(ValueError):
    prepare_gate3_trial(SRC,self.req,{**self.env,key:value})
 def test_repaint_requires_exact_source_target_and_declared_preservation_proof(self):
  from m045_modal_trial_runner import prepare_gate3_trial
  with self.assertRaises(ValueError):prepare_gate3_trial(SRC,{**self.req,'operation':'SELECTIVE_REPAINT'},self.env)
 def test_offline_authenticated_wave_audit_has_no_publication_or_fabricated_approval(self):
  from m045_modal_trial_runner import audit_existing_audio
  import tempfile,studio_server as studio
  from test_platform_identity_and_catalog import SPEC
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);principal='artist-a'
   first=studio.project_operation(root,{'expectedCurrentRevisionId':None,'songSpec':SPEC},commit=True,principal_id=principal)
   wave=fixture_wav();digest=hashlib.sha256(wave).hexdigest()
   studio._publish_cas_exact(root,digest,wave)
   rev=studio.project_operation(root,{'projectId':first['manifest']['projectId'],
     'expectedCurrentRevisionId':first['revision']['revisionId'],'songSpec':SPEC,
     'outputArtifactIds':[digest]},commit=True,principal_id=principal)
   ref={'projectId':rev['manifest']['projectId'],'revisionId':rev['revision']['revisionId'],'artifactId':digest}
   r=audit_existing_audio(root,ref,principal)
   self.assertEqual(r['sourceArtifactId'],digest)
   self.assertEqual(r['sampleRateHz'],44100)
   self.assertEqual(r['channels'],2)
   self.assertFalse(r['releaseCleared'])
   self.assertFalse(r['trialAuthorized'])
   self.assertEqual(studio.project_operation(root,{'projectId':ref['projectId']},principal_id=principal)['revision']['revisionId'],ref['revisionId'])
   with self.assertRaises(studio.ProjectConflict):audit_existing_audio(root,ref,'artist-b')

if __name__=='__main__':unittest.main()
