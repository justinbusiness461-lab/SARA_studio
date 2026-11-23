"""Native payment receipts remain untrusted until host verification and ledger commit."""
import unittest
import studio_server as studio

class NativeReceiptHTTP(unittest.TestCase):
 def setUp(self):
  from test_platform_identity_and_catalog import PlatformHTTP
  self.fx=PlatformHTTP(methodName="test_acc01_entry_does_not_bootstrap_local_user")
  self.fx.setUp();self.addCleanup(self.fx.doCleanups)
  self.previous=studio.PLATFORM_NATIVE_STORE_VERIFIER if hasattr(studio,"PLATFORM_NATIVE_STORE_VERIFIER") else None
  self.addCleanup(lambda:setattr(studio,"PLATFORM_NATIVE_STORE_VERIFIER",self.previous))
  self.account=self.fx.signup()
  self.cookie,_=self.fx.login()
  self.payload={"store":"apple","transactionId":"txn-123","productId":"credits.10","receipt":"test-signed-jws"}
 def send(self,body=None,cookie=None):
  return self.fx.api("/api/billing/native-receipt",self.payload if body is None else body,cookie=self.cookie if cookie is None else cookie)
 def test_unconfigured_host_returns_503_and_forged_browser_credit_fields_rejected(self):
  self.assertEqual(self.send()[0],503)
  self.assertEqual(self.send({**self.payload,"credits":1000000})[0],400)
  self.assertEqual(self.fx.api("/api/credits/balance",cookie=self.cookie)[2]["granted"],0)
 def test_host_verified_receipt_creates_one_ledger_grant(self):
  def host(store,transaction_id,product,receipt,principal):
   if receipt!='test-signed-jws':return None
   return {"store":store,"transactionId":transaction_id,"productId":product,
           "principalId":principal,"credits":10,"verified":True}
  studio.configure_platform_native_store_verifier(host)
  self.assertEqual(self.send({**self.payload,"receipt":"unsigned-payload"})[0],403)
  one=self.send()
  self.assertEqual(one[0],200,one[2])
  self.assertTrue(one[2]["granted"])
  two=self.send()
  self.assertEqual(two[0],200,two[2])
  self.assertFalse(two[2]["granted"])
  self.assertEqual(self.fx.api("/api/credits/balance",cookie=self.cookie)[2]["granted"],10)
  self.fx.signup("second_buyer","other strong password")
  other,_=self.fx.login("second_buyer","other strong password")
  self.assertEqual(self.send(cookie=other)[0],409)
if __name__=="__main__":unittest.main()
