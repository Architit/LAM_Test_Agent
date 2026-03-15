import pytest
import asyncio
import sys
import os

# Add root to sys.path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from map.src.vlrm_core import VilamiMapCore

def test_vlrm_phases():
    vlrm = VilamiMapCore()
    
    async def run_test():
        res = await vlrm.generate_map("nexus_zone")
        assert res["status"] == "mapped"
        assert res["vector_indexed"] == True
        
    asyncio.run(run_test())
