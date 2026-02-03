"""
Garak CLI Runner
Handles integration with Garak command-line tool
Reference: Based on verified working configuration from Garak Setup & Learnings
"""

import subprocess
import os
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime


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
        self.results_dir = os.path.expanduser("~/.garak_results")
        os.makedirs(self.results_dir, exist_ok=True)
    
    def _find_garak(self) -> Optional[str]:
        """Find Garak executable"""
        try:
            result = subprocess.run(
                ['which', 'garak'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def is_installed(self) -> bool:
        """Check if Garak is installed"""
        return self.garak_path is not None
    
    def get_version(self) -> Optional[str]:
        """Get Garak version"""
        try:
            result = subprocess.run(
                ['garak', '--version'],
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
        try:
            result = subprocess.run(
                ['garak', '--list_probes'],
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
        try:
            result = subprocess.run(
                ['garak', '--list_detectors'],
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
        try:
            result = subprocess.run(
                ['garak', '--list_generators'],
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
        cmd = ['garak']
        
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
            
            return process.returncode == 0, output, report_path
            
        except subprocess.TimeoutExpired:
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
        
        import yaml
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
