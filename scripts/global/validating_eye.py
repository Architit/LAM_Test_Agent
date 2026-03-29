import sys
import re
from pathlib import Path

def validate_agent_identity(content):
    """Validate simplified identity for Agents awaiting summoning."""
    if re.match(r"^# \*\*.*\*\*$", content.strip()):
        return []
    return ["Agent identity must strictly follow the format: # **NAME**"]

def validate_tree_identity(content):
    """Validate strict Crystal Standard for Sovereign Trees."""
    patterns = [
        (r"^# IDENTITY CRYSTAL:", "Header 'IDENTITY CRYSTAL' missing."),
        (r"\*\*True Name:\*\* # \*\*", "True Name field violated."),
        (r"\*\*Call Sign:\*\* # \*\*", "Call Sign field violated."),
        (r"\*\*System ID:\*\* # \*\*", "System ID field violated."),
        (r"## I\. PURPOSE", "Purpose section missing."),
        (r"\*\*Custodian:\*\* Ayaearias Triania", "Custodian signature missing."),
        (r"А́мієно́а́э́с моєа́э́ри́э́с", "Sacred Mantra missing."),
        (r"⚜️🛡️⚜️", "Shield seals missing.")
    ]
    errors = []
    for pattern, error_msg in patterns:
        if not re.search(pattern, content, re.MULTILINE):
            errors.append(error_msg)
    return errors

def validate_throne_identity(content):
    """Validate strict Crystal Standard for the High Throne (Nexus)."""
    patterns = [
        (r"^# IDENTITY CRYSTAL: RADRILONIUMA", "Throne Header missing."),
        (r"\*\*System ID:\*\* # \*\*RADR-01\*\*", "System ID violated."),
        (r"## I\. HIERARCHY & AUTHORITY", "Hierarchy section missing (GUARDIAN LOCK VIOLATION)."),
        (r"## II\. PURPOSE:", "Purpose section missing."),
        (r"## III\. MANDATE: ZERO-LOGIC ZONE & ASA", "Mandate section missing (GUARDIAN LOCK VIOLATION)."),
        (r"\*\*Custodian:\*\* Ayaearias Triania", "Custodian signature missing."),
        (r"А́мієно́а́э́с моєа́э́ри́э́с", "Sacred Mantra missing.")
    ]
    errors = []
    for pattern, error_msg in patterns:
        if not re.search(pattern, content, re.MULTILINE):
            errors.append(error_msg)
    return errors

def main():
    print(">>> VALIDATING EYE: Initiating Ontological Scan...")
    
    identity_file = Path("IDENTITY.md")
    if not identity_file.exists():
        identity_file = Path("devkit/IDENTITY.md")
        
    if not identity_file.exists():
        print("[VALIDATING EYE] CRITICAL: IDENTITY.md missing.")
        sys.exit(1)
        
    content = identity_file.read_text(encoding='utf-8').strip()
    
    if "RADR-01" in content and "RADRILONIUMA" in content:
        print("[VALIDATING EYE] Mode: HIGH THRONE (Guardian Lock Active).")
        errors = validate_throne_identity(content)
    elif content.startswith("# **") and content.count("\n") < 5:
        print("[VALIDATING EYE] Mode: AGENT (Summoning Protocol).")
        errors = validate_agent_identity(content)
    else:
        print("[VALIDATING EYE] Mode: SOVEREIGN TREE (Crystal Standard).")
        errors = validate_tree_identity(content)
    
    if errors:
        print(f"[VALIDATING EYE] DRIFT DETECTED in {identity_file}:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    
    print("[VALIDATING EYE] Identity verified. status: GREEN.")
    sys.exit(0)

if __name__ == "__main__":
    main()
