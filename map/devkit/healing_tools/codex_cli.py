# -*- coding: utf-8 -*-
"""
Codex CLI — The Voice of the Kingdom.
"""
import sys
import argparse
from codex_agent.gate import CodexGate

def main():
    parser = argparse.ArgumentParser(description="Codex Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Gate Command (Direct LLM access)
    gate_parser = subparsers.add_parser("gate", help="Access the Ark Gate (LLM)")
    gate_parser.add_argument("query", nargs="+", help="Your question")
    gate_parser.add_argument("--model", default="auto", help="gemini/openai/auto")

    # Status Command
    subparsers.add_parser("status", help="Check gate status")

    args = parser.parse_args()

    if args.command == "gate":
        gate = CodexGate()
        print(gate.ask(" ".join(args.query), model_hint=args.model))
    
    elif args.command == "status":
        gate = CodexGate()
        print("--- Codex Gate Status ---")
        print(f"Gemini Key: {'PRESENT' if gate.google_key else 'MISSING'}")
        print(f"OpenAI Key: {'PRESENT' if gate.openai_key else 'MISSING'}")
        print("The Gate is Ready.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
