import pytest
import asyncio
from transport.message_bus import ZeroMQSimulatedBus

def test_message_bus():
    bus = ZeroMQSimulatedBus()
    received = []
    
    def callback(payload):
        received.append(payload)
        
    bus.subscribe("test_topic", callback)
    
    async def run_test():
        await bus.publish("test_topic", {"data": "hello"})
        
    asyncio.run(run_test())
    
    assert len(received) == 1
    assert received[0]["data"] == "hello"
