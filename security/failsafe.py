class P0SafetyFailsafe:
    def __init__(self):
        self.lockdown = False
        
    def trigger_lockdown(self):
        self.lockdown = True
        
    def execute_safely(self, func):
        if self.lockdown:
            raise Exception("P0 Lockdown Active. Execution blocked.")
        return func()
