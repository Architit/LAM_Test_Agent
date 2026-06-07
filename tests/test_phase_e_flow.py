# Copyright (c) 2026-06-07 RADRILONIUMA / TRIANIUMA Kingdom. All rights reserved.
from flow.cbfc import CircuitBreakerFlowControl

def test_cbfc():
    cbfc = CircuitBreakerFlowControl(failure_threshold=2)
    assert cbfc.can_execute() == True
    cbfc.record_failure()
    assert cbfc.can_execute() == True
    cbfc.record_failure()
    assert cbfc.can_execute() == False
    cbfc.record_success()
    assert cbfc.can_execute() == True
