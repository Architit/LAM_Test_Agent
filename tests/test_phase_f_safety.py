import pytest
from security.failsafe import P0SafetyFailsafe

def test_failsafe():
    failsafe = P0SafetyFailsafe()
    
    def dummy_task():
        return "success"
        
    assert failsafe.execute_safely(dummy_task) == "success"
    
    failsafe.trigger_lockdown()
    with pytest.raises(Exception, match="P0 Lockdown Active"):
        failsafe.execute_safely(dummy_task)
