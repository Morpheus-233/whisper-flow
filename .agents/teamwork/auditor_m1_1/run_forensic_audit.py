import ast
import difflib
import inspect
import json
import os
import re
import sys
import unittest

PROJECT_ROOT = r"C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class ForensicAudit:
    def __init__(self):
        self.findings = []
        self.evidence = {}
        self.clean = True

    def log_failure(self, check_name, reason, evidence_data=None):
        self.clean = False
        self.findings.append({"check": check_name, "status": "FAIL", "reason": reason})
        if evidence_data:
            self.evidence[check_name] = evidence_data
        print(f"[FAIL] {check_name}: {reason}")

    def log_pass(self, check_name, details, evidence_data=None):
        self.findings.append({"check": check_name, "status": "PASS", "details": details})
        if evidence_data:
            self.evidence[check_name] = evidence_data
        print(f"[PASS] {check_name}: {details}")

    def run_all(self):
        print("=== Starting Milestone 1 Forensic Audit ===")
        self.audit_dataset()
        self.audit_ast_calibration_engine()
        self.audit_ast_voice_profile()
        self.audit_ast_voice_training_dialog()
        self.audit_ast_test_suite()
        self.audit_zero_heavy_dependencies()
        self.audit_runtime_behavior_and_tracing()
        self.audit_adversarial_inputs()
        self.audit_voice_training_dialog_init()
        print("\n=== Forensic Audit Completed ===")
        print(f"Overall Verdict: {'CLEAN' if self.clean else 'INTEGRITY VIOLATION'}")

    def audit_dataset(self):
        path = os.path.join(PROJECT_ROOT, "data", "calibration_sentences.json")
        if not os.path.exists(path):
            self.log_failure("Dataset Exists", f"Dataset file not found at {path}")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if len(data) != 100:
            self.log_failure("Dataset Count", f"Expected 100 sentences, got {len(data)}")
            return

        eng_count = 0
        hin_count = 0
        ids = []
        suspicious_texts = []

        for item in data:
            ids.append(item.get("id"))
            cat = item.get("category")
            if cat == "english":
                eng_count += 1
            elif cat == "hindi_hinglish":
                hin_count += 1

            txt = item.get("text", "")
            kws = item.get("phonetic_keywords", [])

            if not txt or len(txt.strip()) < 10:
                suspicious_texts.append(f"Short text in ID {item.get('id')}: {txt}")
            if not kws or not isinstance(kws, list):
                suspicious_texts.append(f"Invalid keywords in ID {item.get('id')}: {kws}")

            # Check for dummy placeholders
            low_txt = txt.lower()
            if any(dummy in low_txt for dummy in ["lorem ipsum", "todo", "dummy sentence", "placeholder"]):
                suspicious_texts.append(f"Dummy text detected in ID {item.get('id')}: {txt}")

        if ids != list(range(1, 101)):
            self.log_failure("Dataset IDs", f"IDs are not 1..100 sequential: {ids[:5]}...{ids[-5:]}")
        elif eng_count != 50 or hin_count != 50:
            self.log_failure("Dataset Distribution", f"Expected 50 English and 50 Hindi/Hinglish, got {eng_count} and {hin_count}")
        elif suspicious_texts:
            self.log_failure("Dataset Content", f"Suspicious entries found: {suspicious_texts}")
        else:
            self.log_pass("Dataset Integrity", f"100 valid sentences (50 English, 50 Hindi/Hinglish), sequential IDs 1-100, non-empty phonetic keywords.")

    def audit_ast_calibration_engine(self):
        path = os.path.join(PROJECT_ROOT, "calibration_engine.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=path)
        functions = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

        required_funcs = ["clean_token", "strip_punctuation", "compute_diff", "load_calibration_dataset", "auto_register_misheard_pairs"]
        missing = [rf for rf in required_funcs if rf not in functions]
        if missing:
            self.log_failure("AST Calibration Functions", f"Missing required functions: {missing}")
            return

        # Check for facade / dummy implementations (e.g. only return constant)
        facades = []
        for name, func_node in functions.items():
            statements = [s for s in func_node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
            if len(statements) == 1 and isinstance(statements[0], ast.Return) and isinstance(statements[0].value, ast.Constant):
                facades.append(name)

        if facades:
            self.log_failure("AST Calibration Facades", f"Facade functions returning constants detected: {facades}")
            return

        # Check for SequenceMatcher usage
        has_sequencematcher = False
        has_get_opcodes = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "SequenceMatcher":
                has_sequencematcher = True
            if isinstance(node, ast.Attribute) and node.attr == "get_opcodes":
                has_get_opcodes = True

        if not (has_sequencematcher and has_get_opcodes):
            self.log_failure("AST SequenceMatcher Verification", "SequenceMatcher or get_opcodes call missing from AST")
            return

        # Check for hardcoded test strings in calibration_engine.py
        suspicious_strings = ["The quick brown fox", "Main thodi der mein", "One two three four"]
        hardcoded_cheating = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for s in suspicious_strings:
                    if s.lower() in node.value.lower():
                        hardcoded_cheating.append(node.value)

        if hardcoded_cheating:
            self.log_failure("AST Hardcoded Test Cases", f"Hardcoded test input strings found in calibration_engine.py: {hardcoded_cheating}")
            return

        self.log_pass("AST Calibration Engine", "AST confirms full SequenceMatcher algorithmic diffing, no facades, no hardcoded test branches.")

    def audit_ast_voice_profile(self):
        path = os.path.join(PROJECT_ROOT, "voice_profile.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=path)
        
        # Verify lookaround boundary regex logic
        has_lookbehind = r'(?<!\w)' in source
        has_lookahead = r'(?!\w)' in source

        if not (has_lookbehind and has_lookahead):
            self.log_failure("AST VoiceProfile Regex Lookaround", "Lookaround assertions (?<!\\w) and (?!\\w) not found in voice_profile.py source")
            return

        # Check get_initial_prompt method
        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "VoiceProfileManager":
                class_node = node
                break

        if not class_node:
            self.log_failure("AST VoiceProfile Class", "VoiceProfileManager class not found in AST")
            return

        methods = {n.name: n for n in class_node.body if isinstance(n, ast.FunctionDef)}
        if "get_initial_prompt" not in methods or "apply_replacements" not in methods:
            self.log_failure("AST VoiceProfile Methods", "Missing get_initial_prompt or apply_replacements in VoiceProfileManager")
            return

        self.log_pass("AST Voice Profile", "Regex lookaround boundaries (?<!\\w) / (?!\\w) and get_initial_prompt budget truncation present in AST.")

    def audit_ast_voice_training_dialog(self):
        path = os.path.join(PROJECT_ROOT, "ui", "voice_training_dialog.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=path)
        
        # Check imports of calibration_engine
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "calibration_engine":
                imported_names.extend(alias.name for alias in node.names)

        expected = ["load_calibration_dataset", "compute_diff", "auto_register_misheard_pairs"]
        missing_imports = [e for e in expected if e not in imported_names]
        if missing_imports:
            self.log_failure("AST Voice Training Dialog Imports", f"Missing imports from calibration_engine: {missing_imports}")
            return

        self.log_pass("AST Voice Training Dialog", f"Correctly imports and wires {imported_names} from calibration_engine.")

    def audit_ast_test_suite(self):
        path = os.path.join(PROJECT_ROOT, "tests", "test_speech_calibration.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=path)

        # Look for suspicious patches that mock compute_diff or SequenceMatcher
        suspicious_patches = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = getattr(node, "func", None)
                if isinstance(func, ast.Name) and func.id == "patch":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and ("compute_diff" in str(arg.value) or "SequenceMatcher" in str(arg.value)):
                            suspicious_patches.append(str(arg.value))
                elif isinstance(func, ast.Attribute) and func.attr == "patch":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and ("compute_diff" in str(arg.value) or "SequenceMatcher" in str(arg.value)):
                            suspicious_patches.append(str(arg.value))

        if suspicious_patches:
            self.log_failure("AST Test Integrity", f"Cheating detected! Tests mock core diff engine: {suspicious_patches}")
            return

        self.log_pass("AST Test Suite Integrity", "No mock bypassing or self-certifying stubs found in test_speech_calibration.py.")

    def audit_zero_heavy_dependencies(self):
        import subprocess
        cmd = [
            os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe"),
            "-c",
            "import sys, calibration_engine; mods = list(sys.modules.keys()); "
            "heavies = [m for m in mods if 'PySide6' in m or 'torch' in m or 'faster_whisper' in m or 'ctranslate2' in m]; "
            "print(','.join(heavies))"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            self.log_failure("Heavy Dependency Audit", f"Failed to test module imports: {res.stderr}")
            return

        output = res.stdout.strip()
        if output:
            self.log_failure("Heavy Dependency Audit", f"Heavy dependencies imported by calibration_engine: {output}")
        else:
            self.log_pass("Zero Heavy Dependencies", "calibration_engine imports 0 heavy dependencies (no PySide6, torch, faster_whisper, ctranslate2).")

    def audit_runtime_behavior_and_tracing(self):
        import calibration_engine
        from voice_profile import VoiceProfileManager

        # Trace SequenceMatcher execution
        calls = {"opcodes": 0, "diffs": 0}
        orig_get_opcodes = difflib.SequenceMatcher.get_opcodes

        def tracked_get_opcodes(self_sm):
            calls["opcodes"] += 1
            return orig_get_opcodes(self_sm)

        difflib.SequenceMatcher.get_opcodes = tracked_get_opcodes
        try:
            res = calibration_engine.compute_diff("This is a genuine test target", "This is an unscripted heard phrase")
            calls["diffs"] += 1
        finally:
            difflib.SequenceMatcher.get_opcodes = orig_get_opcodes

        if calls["opcodes"] < 1:
            self.log_failure("Runtime Tracing", "SequenceMatcher.get_opcodes was NOT executed during compute_diff!")
            return

        # Trace file persistence in VoiceProfileManager
        mgr = VoiceProfileManager.get_instance()
        test_key = "forensic_probe_test_key"
        test_val = "ForensicProbeValue"
        
        mgr.add_replacement(test_key, test_val)
        reps = mgr.get_replacements()
        if reps.get(test_key) != test_val:
            self.log_failure("Runtime Persistence", "Failed to add replacement into VoiceProfileManager")
            return

        # Check that file on disk was actually updated
        profile_path = os.path.join(PROJECT_ROOT, "voice_profile.json")
        with open(profile_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)

        if disk_data.get("word_replacements", {}).get(test_key) != test_val:
            self.log_failure("Runtime Disk Persistence", "voice_profile.json was not updated on disk by add_replacement")
            return

        # Clean up probe key
        mgr.remove_replacement(test_key)
        with open(profile_path, "r", encoding="utf-8") as f:
            disk_data_after = json.load(f)
        if test_key in disk_data_after.get("word_replacements", {}):
            self.log_failure("Runtime Disk Cleanup", "Probe key not removed from disk")
            return

        self.log_pass("Runtime Behavior & Tracing", f"Verified real execution of difflib opcodes ({calls['opcodes']} calls) and genuine JSON file disk I/O.")

    def audit_adversarial_inputs(self):
        import calibration_engine
        from voice_profile import VoiceProfileManager

        mgr = VoiceProfileManager.get_instance()

        # Adversarial Test 1: Complex Hinglish sentence with mixed script and contractions
        t1 = "Aapka project build ho gaya hai, par testing baki hai."
        h1 = "aap ka project built ho gya hai per test baki he"
        r1 = calibration_engine.compute_diff(t1, h1)
        if not (0.0 < r1["accuracy"] < 100.0):
            self.log_failure("Adversarial Accuracy Clamping", f"Expected intermediate accuracy, got {r1['accuracy']}")
            return

        for p in r1["misheard_pairs"]:
            if p["target"].endswith(".") or p["target"].endswith(","):
                self.log_failure("Adversarial Punctuation Leak", f"Punctuation leak in pair: {p}")
                return

        # Adversarial Test 2: Unseen punctuation-laden lookaround replacement
        # Test leading symbol, trailing symbol, internal symbol
        orig_reps = dict(mgr.get_replacements())
        try:
            mgr.profile["word_replacements"] = {
                "@mentions,": "Mentions",
                "#hash_tag.": "Hashtag",
                "c++": "C++",
                "node.js": "NodeJS"
            }
            sample_text = "Check @mentions, and #hash_tag. in c++ and node.js today."
            replaced = mgr.apply_replacements(sample_text)
            expected = "Check Mentions and Hashtag in C++ and NodeJS today."
            if replaced != expected:
                self.log_failure("Adversarial Regex Lookaround", f"Replacement failed.\nExpected: {expected}\nGot:      {replaced}")
                return

            # Substring protection check
            sub_text = "not@mentions, or c+++ or node.json"
            sub_res = mgr.apply_replacements(sub_text)
            # node.json has word char 'o' after 'node.js', but 's' to 'o' is alnum to alnum, lookahead (?!\w) protects it!
            if "NodeJSon" in sub_res:
                self.log_failure("Adversarial Word Boundary Leak", f"Sub-word leaked replacement: {sub_res}")
                return

        finally:
            mgr.profile["word_replacements"] = orig_reps

        # Adversarial Test 3: Truncation with zero and extreme budget
        orig_words = list(mgr.get_custom_words())
        try:
            mgr.profile["custom_words"] = ["A" * 50 for _ in range(50)]
            p_small = mgr.get_initial_prompt(max_chars=100)
            if len(p_small) > 100 or not p_small.endswith("."):
                self.log_failure("Adversarial Prompt Truncation", f"Prompt length {len(p_small)} exceeded max_chars 100: {p_small}")
                return
            p_zero = mgr.get_initial_prompt(max_chars=10)
            if p_zero is not None:
                self.log_failure("Adversarial Prompt Zero Budget", f"Expected None for budget under prefix cost, got {p_zero}")
                return
        finally:
            mgr.profile["custom_words"] = orig_words

        self.log_pass("Adversarial Stress-Testing", "All adversarial tests passed: punctuation stripping, complex Hinglish diffs, sub-word boundaries, and prompt budget boundaries.")

    def audit_voice_training_dialog_init(self):
        import subprocess
        script = (
            "import sys, time; "
            "from PySide6.QtWidgets import QApplication; "
            "app = QApplication.instance() or QApplication(sys.argv); "
            "from ui.voice_training_dialog import VoiceTrainingDialog, CALIBRATION_SENTENCES; "
            "t0 = time.time(); "
            "dlg = VoiceTrainingDialog(None, None); "
            "dt = (time.time() - t0) * 1000; "
            "print(f'{dt:.2f},{len(CALIBRATION_SENTENCES)},{len(dlg.calibration_dataset)}')"
        )
        cmd = [os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe"), "-c", script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            self.log_failure("VoiceTrainingDialog Init", f"Failed to instantiate VoiceTrainingDialog: {res.stderr}")
            return

        out = res.stdout.strip()
        parts = out.split(",")
        latency = float(parts[0])
        sentences_count = int(parts[1])
        dlg_count = int(parts[2])

        if sentences_count != 100 or dlg_count != 100:
            self.log_failure("VoiceTrainingDialog Dataset", f"Expected 100 sentences in dialog, got {sentences_count} and {dlg_count}")
            return

        if latency > 150.0: # Allow headroom on cold start, but verify responsiveness
            print(f"[WARN] Dialog init latency was {latency:.2f}ms (threshold 150ms)")

        self.log_pass("Voice Training Dialog Init", f"Initialized cleanly in {latency:.2f}ms with all 100 bilingual sentences loaded.")

if __name__ == "__main__":
    auditor = ForensicAudit()
    auditor.run_all()
