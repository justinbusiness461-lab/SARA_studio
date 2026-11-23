"""R17 RED: Modal billing exposure, durable call ID and deterministic cancel.
No real Modal SDK action, deploy, inference or external GPU calls permitted."""
import ast
import json
import pathlib
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import Mock,patch

DEPLOY=pathlib.Path(__file__).resolve().parents[1]/'deploy'/'modal_acestep.py'

class FakeCall:
    def __init__(self,*,result=None,timeout=False):
        self.result=result or {'done':True}
        self.timeout=timeout
        self.cancel_requests=[]
        self.get_calls=[]
    def cancel(self,terminate_containers=False):
        self.cancel_requests.append(terminate_containers)
    def get(self,timeout=None):
        self.get_calls.append(timeout)
        if self.timeout:raise TimeoutError('still pending')
        return self.result

class BillingDeployment(unittest.TestCase):
    def test_deploy_function_bounded_one_gpu_one_input_and_no_retry(self):
        source=DEPLOY.read_text()
        tree=ast.parse(source)
        target=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='serve_acestep_api')
        decorators=[d for d in target.decorator_list if isinstance(d,ast.Call)]
        function=next(d for d in decorators if isinstance(d.func,ast.Attribute) and d.func.attr=='function')
        params={k.arg:ast.literal_eval(k.value) for k in function.keywords
                if k.arg in ('gpu','timeout','scaledown_window','max_containers','min_containers','retries','single_use_containers')}
        self.assertEqual(params,{'gpu':'L40S','timeout':120,'scaledown_window':30,
                                 'max_containers':1,'min_containers':0,'retries':0,
                                 'single_use_containers':True})
        web=next(d for d in decorators if isinstance(d.func,ast.Attribute) and d.func.attr=='web_server')
        startup=next(k.value for k in web.keywords if k.arg=='startup_timeout')
        self.assertLessEqual(ast.literal_eval(startup),120)
        self.assertIn('max_inputs=1',source)
    def test_gpu_exposure_math_is_reference_not_hard_total_bill_cap(self):
        from m045_modal_live_client import compute_modal_l40s_exposure_reference
        result=compute_modal_l40s_exposure_reference(
            gpu_rate_usd_per_second=Decimal('0.000542'),
            runtime_seconds=120,scaledown_window_seconds=30,max_containers=1)
        self.assertEqual(result['runtimeOnlyGpuUsd'],'0.065040')
        self.assertEqual(result['runtimePlusIdleGpuUsd'],'0.081300')
        self.assertLess(Decimal(result['runtimePlusIdleGpuUsd']),Decimal('1.00'))
        self.assertFalse(result['totalProviderBillingCapVerified'])
        self.assertEqual(result['scope'],'SINGLE_FUNCTION_INPUT_GPU_ONLY_REFERENCE')
        for count in (0,2):
            with self.subTest(containers=count),self.assertRaises(ValueError):
                compute_modal_l40s_exposure_reference(
                    gpu_rate_usd_per_second=Decimal('0.000542'),
                    runtime_seconds=120,scaledown_window_seconds=30,max_containers=count)
        with self.assertRaises(ValueError):
            compute_modal_l40s_exposure_reference(
                gpu_rate_usd_per_second=Decimal('0.000542'),
                runtime_seconds=600,scaledown_window_seconds=30,max_containers=1)

class ModalCallLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stage=pathlib.Path(self.temp.name)/'att_qa_local.stage'
        self.stage.mkdir()
        self.call_id='fc-r17hostownedabc123456'
        self.call=FakeCall()
        self.resolve=Mock(return_value=self.call)
    def make(self):
        from m045_modal_live_client import ModalFunctionCallSupervisor
        return ModalFunctionCallSupervisor(
            stage_dir=self.stage,principal_id='owner-r17',
            project_id='project-r17',source_revision_id='rev-r17',
            attempt_id='att_qa_local',
            host_call_resolver=self.resolve)
    def test_bind_durable_call_identity_and_cold_restart_poll_no_resubmit(self):
        host=self.make()
        self.assertEqual(host.bind(self.call_id)['state'],'CALL_ID_DURABLE')
        path=self.stage/'modal-function-call.json'
        self.assertTrue(path.is_file())
        record=json.loads(path.read_text())
        self.assertEqual(record['callId'],self.call_id)
        self.assertEqual(record['projectId'],'project-r17')
        self.assertEqual(self.make().poll()['status'],'COMPLETED_UNVERIFIED')
        self.assertEqual(self.resolve.call_count,1)
        self.assertEqual(self.call.get_calls,[0])
    def test_idempotent_bind_exact_owner_and_wrong_call_id_conflict(self):
        host=self.make()
        host.bind(self.call_id)
        self.assertEqual(host.bind(self.call_id)['state'],'CALL_ID_DURABLE')
        with self.assertRaises((ValueError,PermissionError)):
            host.bind('fc-otherhostabc12345678')
        from m045_modal_live_client import ModalFunctionCallSupervisor
        foreign=ModalFunctionCallSupervisor(stage_dir=self.stage,
          principal_id='foreign',project_id='project-r17',
          source_revision_id='rev-r17',attempt_id='att_qa_local',
          host_call_resolver=self.resolve)
        with self.assertRaises((ValueError,PermissionError)):foreign.poll()
        self.resolve.assert_not_called()
    def test_timeout_cancels_with_container_termination_and_never_certifies_hard_billing(self):
        host=self.make()
        host.bind(self.call_id)
        receipt=host.cancel_on_uncertain('HTTP_TIMEOUT')
        self.assertEqual(self.call.cancel_requests,[True])
        self.assertEqual(receipt['status'],'CANCEL_DISPATCHED_UNVERIFIED')
        self.assertFalse(receipt['containerTerminationVerified'])
        self.assertFalse(receipt['billingHardCapVerified'])
        record=json.loads((self.stage/'modal-function-call.json').read_text())
        self.assertEqual(record['state'],'CANCEL_DISPATCHED_UNVERIFIED')
        self.assertEqual(record['callId'],self.call_id)
    def test_cancellation_failure_is_durable_and_not_blindly_retried(self):
        host=self.make();host.bind(self.call_id)
        self.call.cancel=Mock(side_effect=RuntimeError('control plane unreachable'))
        with self.assertRaises(RuntimeError):host.cancel_on_uncertain('HTTP_TIMEOUT')
        self.assertEqual(self.call.cancel.call_count,1)
        record=json.loads((self.stage/'modal-function-call.json').read_text())
        self.assertEqual(record['state'],'CANCEL_INTENT_DURABLE')
        with self.assertRaises((ValueError,PermissionError)):
            host.cancel_on_uncertain('HTTP_TIMEOUT')
        self.assertEqual(self.call.cancel.call_count,1)
    def test_pending_poll_remains_pending_and_never_resubmits(self):
        self.call.timeout=True
        host=self.make();host.bind(self.call_id)
        self.assertEqual(host.poll()['status'],'PENDING')
        self.assertEqual(host.poll()['status'],'PENDING')
        self.assertEqual(self.resolve.call_count,2)
        self.assertEqual(self.call.get_calls,[0,0])
        self.assertEqual(json.loads((self.stage/'modal-function-call.json').read_text())['state'],'CALL_ID_DURABLE')
    def test_untrusted_modal_call_id_is_not_remote_cancel_authority(self):
        from m045_modal_live_client import cancel_remote_attempt,poll_remote_attempt
        with self.assertRaises((ValueError,PermissionError)):
            cancel_remote_attempt(self.call_id)
        with self.assertRaises((ValueError,PermissionError)):
            poll_remote_attempt(self.call_id)
        self.resolve.assert_not_called()
    def test_cold_restart_cancel_request_once_and_status_recovery(self):
        one=self.make();one.bind(self.call_id)
        second=self.make()
        second.cancel_on_uncertain('CLIENT_ABORT')
        self.assertEqual(self.call.cancel_requests,[True])
        with self.assertRaises((ValueError,PermissionError)):
            second.cancel_on_uncertain('CLIENT_ABORT')
        self.assertEqual(self.call.cancel_requests,[True])
        self.assertEqual(self.make().poll()['status'],'COMPLETED_UNVERIFIED')


class LocalhostFunctionCallCancellation(unittest.TestCase):
    def setUp(self):
        from test_m045_modal_live_client import ModalLoopbackContract
        self.fx=ModalLoopbackContract('test_http500_and_timeout_denied_without_current_promotion_or_auto_retry')
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.call=FakeCall()
        self.resolver=Mock(return_value=self.call)
        self.supervisors=[]
    def host_factory(self,stage_dir,principal_id,scope):
        from m045_modal_live_client import ModalFunctionCallSupervisor
        stage=pathlib.Path(stage_dir).resolve()
        host=ModalFunctionCallSupervisor(stage_dir=stage,
            principal_id=principal_id,project_id=scope['projectId'],
            source_revision_id=scope['baseRevisionId'],
            attempt_id=stage.name[:-len('.stage')],
            host_call_resolver=self.resolver)
        host.bind('fc-r17trustedspawnabc123')
        self.supervisors.append(host)
        return host
    def test_localhost_http_timeout_automatically_dispatches_terminate_containers(self):
        from m045_modal_live_client import RemoteSubmissionUncertain
        from platform_identity import PlatformDenied
        self.fx.server.delay=.45
        provider=self.fx.adapter(http_timeout_sec=.08,host_call_supervisor_factory=self.host_factory)
        token=self.fx.token()
        before=self.fx.current()
        with self.assertRaises(RemoteSubmissionUncertain):
            self.fx.execute(token=token,transport=provider)
        self.assertEqual(self.call.cancel_requests,[True])
        self.assertEqual(self.fx.current(),before)
        state=json.loads(self.supervisors[0].path.read_text())['state']
        self.assertEqual(state,'CANCEL_DISPATCHED_UNVERIFIED')
        with self.assertRaises((ValueError,RuntimeError,PermissionError)):
            self.fx.execute(token=token,transport=provider)
        self.assertEqual(self.call.cancel_requests,[True])
    def test_localhost_http500_triggers_cancel_and_durable_uncertain(self):
        from m045_modal_live_client import RemoteSubmissionUncertain
        self.fx.server.status=500
        before=self.fx.current()
        with self.assertRaises(RemoteSubmissionUncertain):
            self.fx.execute(transport=self.fx.adapter(host_call_supervisor_factory=self.host_factory))
        self.assertEqual(self.call.cancel_requests,[True])
        self.assertEqual(self.fx.current(),before)
    def test_prebound_supervisor_bypasses_factory_must_be_denied_before_socket(self):
        from m045_modal_live_client import ModalFunctionCallSupervisor
        stage=self.fx.f.root/'att_unbound_r17.stage'
        stage.mkdir()
        unbound=ModalFunctionCallSupervisor(stage_dir=stage,
            principal_id=self.fx.user['principalId'],
            project_id=self.fx.src['projectId'],
            source_revision_id=self.fx.scope['baseRevisionId'],
            attempt_id='att_unbound_r17',
            host_call_resolver=self.resolver)
        unbound.bind('fc-r17foreigncallabc123')
        before=self.fx.current()
        with self.assertRaises((ValueError,PermissionError)):
            self.fx.execute(transport=self.fx.adapter(host_call_supervisor=unbound))
        self.assertEqual(self.fx.server.request_log,[])
        self.assertEqual(self.fx.current(),before)
    def test_wrong_staging_directory_factory_cannot_cancel_unrelated_call(self):
        from m045_modal_live_client import ModalFunctionCallSupervisor
        def malicious_factory(stage,principal,scope):
            wrong=self.fx.f.root/'att_wrong_r17.stage'
            wrong.mkdir(exist_ok=True)
            other=ModalFunctionCallSupervisor(stage_dir=wrong,
                principal_id=principal,project_id=scope['projectId'],
                source_revision_id=scope['baseRevisionId'],
                attempt_id='att_wrong_r17',host_call_resolver=self.resolver)
            other.bind('fc-r17wrongstagedabc123')
            return other
        before=self.fx.current()
        with self.assertRaises((ValueError,PermissionError)):
            self.fx.execute(transport=self.fx.adapter(host_call_supervisor_factory=malicious_factory))
        self.assertEqual(self.fx.server.request_log,[])
        self.assertEqual(self.fx.current(),before)
        self.resolver.assert_not_called()
    def test_client_timeout_gt_120_rejected_before_http_socket(self):
        with self.assertRaises((ValueError,PermissionError)):
            self.fx.execute(transport=self.fx.adapter(http_timeout_sec=121))
        self.assertEqual(self.fx.server.request_log,[])
        self.assertEqual(self.call.cancel_requests,[])

if __name__=='__main__':unittest.main()
