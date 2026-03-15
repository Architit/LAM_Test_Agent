#!/usr/bin/env python3
import sys
import argparse
import os

def validate_task_spec(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: Spec file {file_path} not found.")
        sys.exit(1)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "COMPLETE" in content and "code_evidence_path" not in content:
        print("Error: 'COMPLETE' state found but 'code_evidence_path' is missing.")
        print("Violation of IC_PURGE_THE_LIE_20260314.md: Code is Truth.")
        sys.exit(1)
        
    print(f"Validation passed for {file_path}")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec-file", required=True)
    args = parser.parse_args()
    validate_task_spec(args.spec_file)
