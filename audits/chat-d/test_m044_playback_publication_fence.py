import unittest
from m044_playback_publication_fence import assess
A="a"*64
B="b"*64
def case(selected="R2",playing="R2",published=2,gen=2):
    artifact={"R1":("a1",A),"R2":("b2",B)}
    return {"case":"async_completion","currentRevisionId":"R2","selectedRevisionId":selected,
      "latestRequestGeneration":gen,"history":[
        {"revisionId":r,"sourceRevisionId":r,"current":r=="R2","playable":True,"audioValidation":"PASS","artifactId":artifact[r][0],"decodedPcmSha256":artifact[r][1]} for r in ("R1","R2")],
      "networkCompletions":[{"requestGeneration":published,"revisionId":selected,"artifactId":artifact[selected][0],"published":True}],
      "playback":{"started":True,"requestGeneration":published,"revisionId":playing,
                  "artifactId":artifact[playing][0],"decodedPcmSha256":artifact[playing][1]}}
class Tests(unittest.TestCase):
    def test_current_r2(self): self.assertFalse(assess([case()]))
    def test_stale_r1_fetch(self): self.assertTrue(assess([case(published=1)]))
    def test_missing_generation(self):
        e=case();e["playback"].pop("requestGeneration");self.assertTrue(assess([e]))
    def test_historical_explicit(self):
        e=case(selected="R1",playing="R1",published=3,gen=3);self.assertFalse(assess([e]))
    def test_wrong_playback(self): self.assertTrue(assess([case(playing="R1")]))
    def test_false_current(self):
        e=case();e["history"][0]["current"]=True;self.assertTrue(assess([e]))
if __name__=="__main__": unittest.main()
