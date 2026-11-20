"""R7-C RED: no network, no GPU, no cost, static pinned Modal bounded preflight."""
import unittest
from pathlib import Path

class ZeroSpendModalPreflight(unittest.TestCase):
 def setUp(self):
  self.source=Path(__file__).resolve().parents[1]/"deploy"/"modal_acestep.py"
  self.request={"mode":"ZERO_SPEND_PREFLIGHT","gpuSecondsCap":90,
      "songSecondsCap":30,"maxSpendUsd":0,"execute":False}
 def test_no_external_execution_preflight_has_exact_source_and_gate_holds(self):
  from m045_modal_trial_preflight import zero_spend_modal_preflight
  receipt=zero_spend_modal_preflight(self.source,self.request)
  self.assertEqual(receipt["state"],"PREFLIGHT_ONLY")
  self.assertEqual(receipt["gpuAllocated"],False)
  self.assertEqual(receipt["chargesIncurredUsd"],0)
  self.assertFalse(receipt["trialAuthorized"])
  self.assertFalse(receipt["readyForGpuLaunch"])
  self.assertEqual(receipt["machine"],"L40S")
  self.assertEqual(receipt["maxContainers"],1)
  self.assertEqual(len(receipt["sourceSha256"]),64)
  self.assertEqual(len(receipt["upstreamCommit"]),40)
 def test_positive_spend_execution_or_unbounded_duration_never_preflight(self):
  from m045_modal_trial_preflight import zero_spend_modal_preflight
  for field,value in [("execute",True),("maxSpendUsd",0.01),("gpuSecondsCap",601),
     ("gpuSecondsCap",0),("songSecondsCap",211),("mode","EXECUTE_GPU")]:
   with self.subTest(field=field,value=value),self.assertRaises(ValueError):
    zero_spend_modal_preflight(self.source,{**self.request,field:value})
 def test_unpinned_or_nonconcurrent_deployment_fails_static_qualification(self):
  from m045_modal_trial_preflight import zero_spend_modal_preflight
  src=self.source.read_text()
  for name,content in [("unbounded",src.replace("max_containers=1","max_containers=12")),
                       ("unpinned",src.replace("ca1e85fe9430179831e6bc6be790c332190a3866","main"))]:
   from tempfile import TemporaryDirectory
   with TemporaryDirectory() as d:
    p=Path(d)/"modal_acestep.py";p.write_text(content)
    with self.subTest(name=name),self.assertRaises(ValueError):
     zero_spend_modal_preflight(p,self.request)
