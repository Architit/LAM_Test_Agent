# -*- coding: utf-8 -*-
"""
The Codex Gate (Phase 8.0)
Universal Interface for the Kingdom's Codex.
Bridges OpenAI, Gemini, and Local Logic.
"""

import os
import sys
import argparse
from typing import Optional, Dict, Any

class CodexGate:
    def __init__(self):
        self.google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self._google_client = None
        self._openai_client = None

    def _get_google_client(self):
        if not self._google_client:
            if not self.google_key:
                raise RuntimeError("Missing GOOGLE_API_KEY for Codex Gate.")
            from google import genai
            self._google_client = genai.Client(api_key=self.google_key)
        return self._google_client

    def _get_openai_client(self):
        if not self._openai_client:
            if not self.openai_key:
                raise RuntimeError("Missing OPENAI_API_KEY for Codex Gate.")
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.openai_key)
        return self._openai_client

    def ask(self, prompt: str, model_hint: str = "auto", sys_prompt: str = "You are the Codex.") -> str:
        """
        Universal query method.
        model_hint: 'gemini', 'openai', 'auto', or specific model name.
        """
        
        # Auto-selection logic
        if model_hint == "auto":
            if self.google_key:
                model_hint = "gemini"
            elif self.openai_key:
                model_hint = "openai"
            else:
                return "Error: No API keys found. The Gate is closed."

        if "gemini" in model_hint or "flash" in model_hint:
            return self._ask_gemini(prompt, sys_prompt, model=model_hint if "gemini" not in model_hint else "gemini-2.0-flash")
        
        if "openai" in model_hint or "gpt" in model_hint:
            return self._ask_openai(prompt, sys_prompt, model=model_hint if "openai" not in model_hint else "gpt-4o")

        return f"Error: Unknown model hint '{model_hint}'."

    def _ask_gemini(self, prompt: str, sys_prompt: str, model: str) -> str:
        client = self._get_google_client()
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"system_instruction": sys_prompt}
            )
            return response.text if response.text else "Error: Empty response from Gemini."
        except Exception as e:
            return f"Gemini Error: {e}"

    def _ask_openai(self, prompt: str, sys_prompt: str, model: str) -> str:
        client = self._get_openai_client()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content or "Error: Empty response from OpenAI."
        except Exception as e:
            return f"OpenAI Error: {e}"

def main():
    parser = argparse.ArgumentParser(description="Codex Gate Interface")
    parser.add_argument("prompt", nargs="+", help="The query for the Codex")
    parser.add_argument("--model", default="auto", help="Model hint (gemini/openai/auto)")
    args = parser.parse_args()
    
    gate = CodexGate()
    print(gate.ask(" ".join(args.prompt), model_hint=args.model))

if __name__ == "__main__":
    main()
