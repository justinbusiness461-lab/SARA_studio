"""Static and pure-runtime checks; does not deploy or allocate paid GPUs."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "deploy" / "modal_acestep.py"

class ModalDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.contents = SOURCE.read_text(encoding="utf-8")
        self.tree = ast.parse(self.contents, filename=str(SOURCE))
        funcs = [n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in {"_checkpoint_manifest", "_manifest_sha256"}]
        self.assertEqual(len(funcs), 2)
        module = ast.fix_missing_locations(ast.Module(body=funcs, type_ignores=[]))
        namespace = {"hashlib": hashlib, "json": json, "Path": Path}
        exec(compile(module, str(SOURCE), "exec"), namespace)
        self.manifest = namespace["_checkpoint_manifest"]
        self.digest = namespace["_manifest_sha256"]

    def test_manifest_digests_change_only_with_model_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.safetensors").write_bytes(b"model-version-one")
            (root / "unrelated.txt").write_text("not a model")
            first = self.manifest(root)
            self.assertEqual(first["model.safetensors"],
                             hashlib.sha256(b"model-version-one").hexdigest())
            original = self.digest(first)
            (root / "unrelated.txt").write_text("different unrelated text")
            self.assertEqual(self.digest(self.manifest(root)), original)
            (root / "model.safetensors").write_bytes(b"model-version-two")
            self.assertNotEqual(self.digest(self.manifest(root)), original)

    def test_unqualified_and_symlinked_weights_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError):
                self.digest(self.manifest(root))
            (root / "model.safetensors").symlink_to(root / "missing.weights")
            with self.assertRaises(RuntimeError):
                self.manifest(root)

    def test_deployment_requires_pinned_upstream_auth_and_gpu_limits(self):
        const = {target.id: node.value.value
                 for node in self.tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                 for target in node.targets if isinstance(target, ast.Name)}
        self.assertEqual(const["UPSTREAM_REPO"],
                         "https://github.com/ace-step/ACE-Step-1.5.git")
        self.assertEqual(len(const["UPSTREAM_COMMIT"]), 40)
        self.assertEqual(const["MODEL_VOLUME_PATH"], "/models/checkpoints")
        self.assertIn('modal.Secret.from_name(MODEL_SECRET_NAME)', self.contents)
        self.assertIn('@modal.concurrent(max_inputs=1)', self.contents)
        self.assertIn('max_containers=1', self.contents)
        self.assertIn('"ACESTEP_API_KEY": api_key', self.contents)
        self.assertIn('http://127.0.0.1:8001/health', self.contents)
        self.assertIn('scaledown_window=60', self.contents)
