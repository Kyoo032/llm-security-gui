"""
Results Manager
Handles saving, loading, and analyzing test results
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import csv


class ResultsManager:
    """Manages test results storage and analysis"""
    
    def __init__(self, results_dir: str = None):
        if results_dir is None:
            results_dir = os.path.expanduser("~/.llm_red_team_results")
        
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
    
    def save_results(self, results: List[Dict], filename: str = None) -> str:
        """Save test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"red_team_results_{timestamp}.json"
        
        filepath = os.path.join(self.results_dir, filename)
        
        # Add metadata
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'successful_bypasses': sum(1 for r in results if r.get('success')),
            'results': results
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def load_results(self, filename: str) -> Optional[Dict]:
        """Load results from file"""
        filepath = os.path.join(self.results_dir, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    def list_results(self) -> List[str]:
        """List all saved result files"""
        files = []
        for f in os.listdir(self.results_dir):
            if f.endswith('.json'):
                files.append(f)
        return sorted(files, reverse=True)
    
    def export_csv(self, results: List[Dict], filepath: str):
        """Export results to CSV"""
        if not results:
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    def export_json(self, results: List[Dict], filepath: str):
        """Export results to JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
    
    def generate_summary(self, results: List[Dict]) -> Dict:
        """Generate a summary of test results"""
        if not results:
            return {}
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success'))
        
        # Group by probe
        by_probe = {}
        for r in results:
            probe = r.get('probe', 'Unknown')
            if probe not in by_probe:
                by_probe[probe] = {'total': 0, 'successful': 0}
            by_probe[probe]['total'] += 1
            if r.get('success'):
                by_probe[probe]['successful'] += 1
        
        # Group by payload
        by_payload = {}
        for r in results:
            payload = r.get('payload', 'Unknown')
            if payload not in by_payload:
                by_payload[payload] = {'total': 0, 'successful': 0}
            by_payload[payload]['total'] += 1
            if r.get('success'):
                by_payload[payload]['successful'] += 1
        
        return {
            'total_tests': total,
            'successful_bypasses': successful,
            'blocked': total - successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'by_probe': by_probe,
            'by_payload': by_payload
        }
    
    def get_vulnerable_combinations(self, results: List[Dict]) -> List[Dict]:
        """Get all successful bypass combinations"""
        return [r for r in results if r.get('success')]
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate a text report of results"""
        summary = self.generate_summary(results)
        
        report = "=" * 60 + "\n"
        report += "LLM RED TEAM TEST REPORT\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        report += "SUMMARY\n"
        report += "-" * 40 + "\n"
        report += f"Total Tests: {summary.get('total_tests', 0)}\n"
        report += f"Successful Bypasses: {summary.get('successful_bypasses', 0)}\n"
        report += f"Blocked: {summary.get('blocked', 0)}\n"
        report += f"Success Rate: {summary.get('success_rate', 0):.1f}%\n\n"
        
        report += "RESULTS BY PROBE\n"
        report += "-" * 40 + "\n"
        for probe, stats in summary.get('by_probe', {}).items():
            rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"• {probe}: {stats['successful']}/{stats['total']} ({rate:.1f}%)\n"
        
        report += "\nRESULTS BY PAYLOAD\n"
        report += "-" * 40 + "\n"
        for payload, stats in summary.get('by_payload', {}).items():
            rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"• {payload}: {stats['successful']}/{stats['total']} ({rate:.1f}%)\n"
        
        report += "\n" + "=" * 60 + "\n"
        
        return report
