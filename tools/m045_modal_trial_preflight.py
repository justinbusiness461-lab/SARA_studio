"""Source-only zero-spend Modal ACE-Step preflight. NO Modal import, API or GPU."""
from __future__ import annotations
import ast
import hashlib
import re
from pathlib import Path

PIN=re.compile(r"[0-9a-f]{40}\Z")
_REQUIRED={"mode","gpuSecondsCap","songSecondsCap","maxSpendUsd","execute"}

def _keyword(call,key):
    for item in call.keywords:
        if item.arg==key:return ast.literal_eval(item.value)
    raise ValueError("MODAL_SOURCE_CAP_MISSING_"+key)

def zero_spend_modal_preflight(source,request):
    """Refuse execution/payment while reporting static source-qualified limits.

    The return is NOT permission to deploy, not a pricing quote, and not an
    independently validated checkpoint or remote inference result.
    """
    if not isinstance(request,dict) or set(request)!=_REQUIRED:
        raise ValueError("MODAL_PREFLIGHT_FIELDS_INVALID")
    if (request["mode"]!="ZERO_SPEND_PREFLIGHT" or
        request["execute"] is not False or
        type(request["maxSpendUsd"]) is not int or request["maxSpendUsd"]!=0 or
        type(request["gpuSecondsCap"]) is not int or
        not 1<=request["gpuSecondsCap"]<=600 or
        type(request["songSecondsCap"]) is not int or
        not 1<=request["songSecondsCap"]<=210):
        raise ValueError("MODAL_ZERO_SPEND_POLICY_VIOLATION")
    path=Path(source)
    data=path.read_bytes()
    tree=ast.parse(data,filename=str(path))
    consts={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant):
            for tgt in node.targets:
                if isinstance(tgt,ast.Name):consts[tgt.id]=node.value.value
    if (consts.get("UPSTREAM_REPO")!="https://github.com/ace-step/ACE-Step-1.5.git"
        or not isinstance(consts.get("UPSTREAM_COMMIT"),str)
        or not PIN.fullmatch(consts["UPSTREAM_COMMIT"])):
        raise ValueError("MODAL_UPSTREAM_SOURCE_NOT_PINNED")
    service=next((node for node in tree.body
       if isinstance(node,ast.FunctionDef) and node.name=="serve_acestep_api"),None)
    if service is None:raise ValueError("MODAL_SERVICE_FUNCTION_MISSING")
    function_deco=next((x for x in service.decorator_list
        if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
        and x.func.attr=="function"),None)
    concurrent_deco=next((x for x in service.decorator_list
        if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
        and x.func.attr=="concurrent"),None)
    if function_deco is None or concurrent_deco is None:
        raise ValueError("MODAL_CONCURRENCY_OWNER_MISSING")
    try:
        gpu=_keyword(function_deco,"gpu")
        max_containers=_keyword(function_deco,"max_containers")
        timeout=_keyword(function_deco,"timeout")
        cold_window=_keyword(function_deco,"scaledown_window")
        max_inputs=_keyword(concurrent_deco,"max_inputs")
    except (TypeError,ValueError) as exc:
        raise ValueError("MODAL_STATIC_DEPLOY_CAPS_INVALID") from exc
    if (gpu!="L40S" or max_containers!=1 or max_inputs!=1
            or type(timeout) is not int or not 1<=timeout<=600
            or type(cold_window) is not int or not 0<=cold_window<=60
            or request["gpuSecondsCap"]>timeout):
        raise ValueError("MODAL_GPU_CAPS_UNQUALIFIED")
    return {"state":"PREFLIGHT_ONLY","model":"ACE-Step 1.5",
        "machine":gpu,"maxContainers":max_containers,"maxConcurrentInputs":max_inputs,
        "serviceTimeoutSeconds":timeout,"idleScaleDownSeconds":cold_window,
        "requestedGpuSecondsCap":request["gpuSecondsCap"],
        "requestedSongSecondsCap":request["songSecondsCap"],
        "budgetCapUsd":0,"chargesIncurredUsd":0,
        "gpuAllocated":False,"networkCallsMade":0,
        "sourceSha256":hashlib.sha256(data).hexdigest(),
        "upstreamCommit":consts["UPSTREAM_COMMIT"],
        "checkpointDigest":"NOT_EXAMINED",
        "priceQuote":"NOT_VERIFIED",
        "trialAuthorized":False,"readyForGpuLaunch":False,
        "gateHolds":["OPERATOR_SPEND_APPROVAL_REQUIRED",
             "HOST_PRICING_AND_CREDENTIALS_NOT_QUALIFIED",
             "CHECKPOINT_BYTES_NOT_PHYSICALLY_VERIFIED",
             "REAL_INFERENCE_AND_CREATIVE_AUDIO_NOT_RUN"]}