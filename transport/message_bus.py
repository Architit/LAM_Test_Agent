import asyncio
from typing import Callable, Dict, List

class ZeroMQSimulatedBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        
    def subscribe(self, topic: str, callback: Callable):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        
    async def publish(self, topic: str, payload: dict):
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(payload)
                else:
                    callback(payload)
