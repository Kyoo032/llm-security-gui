"""
Garak CLI Runner
Handles integration with Garak command-line tool
Reference: Based on verified working configuration from Garak Setup & Learnings
"""

import subprocess
import os
import json
import shutil
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import time

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

# Validation patterns for command injection prevention
_SAFE_MODEL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-./]+$')
_SAFE_PROBE_PATTERN = re.compile(r'^[a-zA-Z0-9_.]+$')
_ALLOWED_MODEL_TYPES = {'huggingface', 'openai', 'replicate', 'local'}


class GarakRunner:
    """
    Runner for Garak CLI commands
    
    Environment Setup (Verified Working):
    - OS: WSL2 + Ubuntu 22.04
    - Python: 3.10+ (required for Garak)
    - GPU: GTX 1650 (4GB VRAM) via WSL
    - Auth: huggingface-cli login or HF_TOKEN env var
    """
    
    # Verified working models for 4GB VRAM
    VERIFIED_MODELS = [
        'distilgpt2',           # Recommended for testing
        'gpt2',
        'gpt2-medium',
        'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
    ]
    
    # Garak probe categories
    PROBE_CATEGORIES = {
        'encoding': 'Test encoding-based bypasses (base64, rot13, etc.)',
        'dan': '"Do Anything Now" jailbreak variants',
        'promptinject': 'Direct prompt injection attacks',
        'lmrc': 'Language Model Risk Cards',
        'atkgen': 'Attack generation probes',
        'gcg': 'Greedy Coordinate Gradient attacks',
    }
    
    def __init__(self):
        self.garak_path = self._find_garak()
        self.garak_cmd = [self.garak_path] if self.garak_path else None
        self.results_dir = os.path.expanduser("~/.garak_results")
        os.makedirs(self.results_dir, exist_ok=True)

    def _ensure_garak(self):
        if not self.garak_cmd:
            raise RuntimeError("Garak not found. Install with: pip install garak")

    def _validate_model_name(self, model_name: str) -> bool:
        """Validate model name to prevent command injection."""
        if not model_name or len(model_name) > 256:
            return False
        return bool(_SAFE_MODEL_NAME_PATTERN.match(model_name))

    def _validate_probe(self, probe: str) -> bool:
        """Validate probe name to prevent command injection."""
        if not probe or len(probe) > 128:
            return False
        return bool(_SAFE_PROBE_PATTERN.match(probe))
    
    def _find_garak(self) -> Optional[str]:
        """Find Garak executable"""
        return shutil.which('garak')
    
    def is_installed(self) -> bool:
        """Check if Garak is installed"""
        return self.garak_path is not None
    
    def get_version(self) -> Optional[str]:
        """Get Garak version"""
        self._ensure_garak()
        try:
            result = subprocess.run(
                self.garak_cmd + ['--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def list_probes(self) -> List[str]:
        """Get list of available probes"""
        self._ensure_garak()
        try:
            result = subprocess.run(
                self.garak_cmd + ['--list_probes'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
        except Exception:
            pass
        return list(self.PROBE_CATEGORIES.keys())
    
    def list_detectors(self) -> List[str]:
        """Get list of available detectors"""
        self._ensure_garak()
        try:
            result = subprocess.run(
                self.garak_cmd + ['--list_detectors'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
        except Exception:
            pass
        return []
    
    def list_generators(self) -> List[str]:
        """Get list of available generators"""
        self._ensure_garak()
        try:
            result = subprocess.run(
                self.garak_cmd + ['--list_generators'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
        except Exception:
            pass
        return []
    
    def build_command(
        self,
        model_name: str,
        probes: List[str],
        model_type: str = 'huggingface',
        config_file: Optional[str] = None
    ) -> List[str]:
        """
        Build Garak CLI command

        Example commands from reference:
        - garak --model_type huggingface --model_name gpt2 --probes encoding
        - garak --model_type huggingface --model_name distilgpt2 --probes promptinject.HijackHateHumansMini
        - garak --config your_config.yaml
        """
        self._ensure_garak()

        # Validate inputs to prevent command injection
        if not self._validate_model_name(model_name):
            raise ValueError(f"Invalid model name: {model_name}")
        for probe in probes:
            if not self._validate_probe(probe):
                raise ValueError(f"Invalid probe name: {probe}")
        if model_type not in _ALLOWED_MODEL_TYPES:
            raise ValueError(f"Invalid model type: {model_type}")

        cmd = list(self.garak_cmd)
        
        if config_file:
            cmd.extend(['--config', config_file])
        else:
            cmd.extend(['--model_type', model_type])
            cmd.extend(['--model_name', model_name])
            
            if probes:
                probe_str = ','.join(probes)
                cmd.extend(['--probes', probe_str])
        
        return cmd
    
    def build_command_string(
        self,
        model_name: str,
        probes: List[str],
        model_type: str = 'huggingface'
    ) -> str:
        """Build command as string for display"""
        cmd = self.build_command(model_name, probes, model_type)
        return ' '.join(cmd)
    
    def run_scan(
        self,
        model_name: str,
        probes: List[str],
        model_type: str = 'huggingface',
        timeout: int = 3600,
        callback=None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Run Garak scan
        
        Returns:
            Tuple of (success, output, report_path)
        """
        cmd = self.build_command(model_name, probes, model_type)
        start_time = time.time()
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            output_lines = []
            report_path = None
            
            if process.stdout:
                for line in process.stdout:
                    output_lines.append(line)
                    if callback:
                        callback(line)
                    
                    # Look for report path in output
                    if 'report' in line.lower() and '.json' in line:
                        # Extract report path
                        parts = line.split()
                        for part in parts:
                            if '.json' in part:
                                report_path = part.strip()
                                break
            
            process.wait(timeout=timeout)
            output = ''.join(output_lines)

            if not report_path:
                report_path = self._find_recent_report(start_time)
            
            return process.returncode == 0, output, report_path
            
        except subprocess.TimeoutExpired:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                process.kill()
            return False, "Scan timed out", None
        except Exception as e:
            return False, str(e), None
    
    def create_config(
        self,
        model_name: str,
        probes: List[str],
        verbose: bool = True,
        parallel_requests: int = 1
    ) -> str:
        """
        Create Garak YAML config file
        
        From reference:
        - verbose: true
        - parallel_requests: <num>
        - probe_spec: <specific probes>
        """
        config = {
            'run': {
                'verbose': verbose,
                'parallel_requests': parallel_requests
            },
            'plugins': {
                'model_type': 'huggingface',
                'model_name': model_name,
                'probe_spec': ','.join(probes) if probes else ''
            }
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_path = os.path.join(self.results_dir, f"garak_config_{timestamp}.yaml")
        if yaml is None:
            raise RuntimeError("PyYAML not installed. Install with: pip install pyyaml")
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return config_path
    
    def parse_report(self, report_path: str) -> Optional[Dict]:
        """Parse Garak JSON/HTML report"""
        if not os.path.exists(report_path):
            return None
        
        try:
            with open(report_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _find_recent_report(self, since_ts: float) -> Optional[str]:
        """Find the most recent report created after a given timestamp."""
        if not os.path.isdir(self.results_dir):
            return None

        candidates = []
        for name in os.listdir(self.results_dir):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self.results_dir, name)
            try:
                if os.path.getmtime(path) >= (since_ts - 1):
                    candidates.append(path)
            except Exception:
                continue

        if not candidates:
            return None
        return max(candidates, key=os.path.getmtime)
    
    def get_probe_info(self, probe_name: str) -> str:
        """Get information about a probe"""
        return self.PROBE_CATEGORIES.get(
            probe_name, 
            f"Probe: {probe_name}"
        )
    
    @staticmethod
    def get_install_instructions() -> str:
        """Get Garak installation instructions"""
        return """
=== GARAK INSTALLATION ===

1. Install Garak:
   pip install garak

2. Verify installation:
   garak --version
   garak --list_probes

3. Set up HuggingFace authentication:
   huggingface-cli login
   # OR
   export HF_TOKEN=your_token_here

4. Test with a lightweight model:
   garak --model_type huggingface --model_name distilgpt2 --probes encoding

=== ENVIRONMENT (Verified Working) ===
- OS: WSL2 + Ubuntu 22.04
- Python: 3.10+
- GPU: GTX 1650 (4GB VRAM) - use lightweight models only
- Verified models: distilgpt2, gpt2, gpt2-medium, TinyLlama-1.1B

=== QUICK REFERENCE ===
garak --list_probes
garak --list_detectors  
garak --list_generators
garak --config your_config.yaml
"""


# Quick reference commands
GARAK_QUICK_COMMANDS = {
    'list_probes': 'garak --list_probes',
    'list_detectors': 'garak --list_detectors',
    'list_generators': 'garak --list_generators',
    'version': 'garak --version',
    'encoding_gpt2': 'garak --model_type huggingface --model_name gpt2 --probes encoding',
    'dan_distilgpt2': 'garak --model_type huggingface --model_name distilgpt2 --probes dan',
    'promptinject': 'garak --model_type huggingface --model_name distilgpt2 --probes promptinject.HijackHateHumansMini',
}
