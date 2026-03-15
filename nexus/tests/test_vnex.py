import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# Adjust path for nested directories like memory/trianiuma
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from nexus.src.vnex_core import NexusRouter

def test_vnex_phases():
    engine = NexusRouter()
    
    async def run_test():
        res = await engine.execute("test_payload")
        assert res["status"] == "processed"
        assert res["sys_id"] == "VNEX"
        
    asyncio.run(run_test())
