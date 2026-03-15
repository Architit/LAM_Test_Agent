class CircuitBreakerFlowControl:
    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.failures = 0
        self.state = "CLOSED"
        
    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            
    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"
        
    def can_execute(self) -> bool:
        return self.state == "CLOSED"
