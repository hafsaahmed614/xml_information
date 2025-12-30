#!/usr/bin/env python3
"""
Regression and Validation Tests for SPL Parser
"""

import unittest
import json
import os
import shutil
from pathlib import Path
try:
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

from src.spl_parser import SPLParser

class TestRegressionAndValidation(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Paths
        cls.root_dir = Path(__file__).parent.parent
        cls.examples_dir = cls.root_dir / 'data' / 'examples'
        cls.schema_path = cls.root_dir / 'data' / 'schemas' / 'dailymed_spl_schema.json'
        cls.golden_dir = cls.root_dir / 'tests' / 'fixtures' / 'golden'
        
        # Create golden dir if not exists (for initial run/setup)
        cls.golden_dir.mkdir(parents=True, exist_ok=True)
        
        # Load schema
        with open(cls.schema_path, 'r') as f:
            cls.schema = json.load(f)
            
        cls.parser = SPLParser()
        cls.xml_files = sorted(list(cls.examples_dir.glob('*.xml')))

    def test_schema_validation(self):
        """Validate that all example files parse to JSON that matches the schema."""
        if not JSONSCHEMA_AVAILABLE:
            self.skipTest("jsonschema library not available")
            
        for xml_file in self.xml_files:
            with self.subTest(file=xml_file.name):
                doc = self.parser.parse_file(str(xml_file))
                doc_dict = doc.to_dict()
                
                try:
                    validate(instance=doc_dict, schema=self.schema)
                except ValidationError as e:
                    self.fail(f"Schema validation failed for {xml_file.name}: {e.message}")

    def test_regression(self):
        """Compare current output against golden files."""
        # If no golden files exist, we might want to generate them (or fail if strict)
        # For this setup, we'll generate them if missing, but typically you'd commit them.
        
        for xml_file in self.xml_files:
            golden_file = self.golden_dir / f"{xml_file.stem}.json"
            
            doc = self.parser.parse_file(str(xml_file))
            current_json = doc.to_dict()
            
            if not golden_file.exists():
                # Allow creating golden files if they don't exist (initial bootstrap)
                with open(golden_file, 'w') as f:
                    json.dump(current_json, f, indent=2, sort_keys=True)
                print(f"Created golden file for {xml_file.name}")
                continue
                
            with open(golden_file, 'r') as f:
                golden_json = json.load(f)
            
            # Normalize timestamps for comparison (parsed_at varies)
            current_json['source']['parsed_at'] = "IGNORE"
            golden_json['source']['parsed_at'] = "IGNORE"
            
            # Use json.dumps to compare string representations for easier diff reading on failure
            current_str = json.dumps(current_json, indent=2, sort_keys=True)
            golden_str = json.dumps(golden_json, indent=2, sort_keys=True)
            
            self.assertEqual(current_str, golden_str, f"Regression failure for {xml_file.name}")

if __name__ == '__main__':
    unittest.main()
