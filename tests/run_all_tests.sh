#!/bin/bash
# Run all Phase 3 tests

echo "========================================================================"
echo "ASH-FL Phase 3: Running All Tests"
echo "========================================================================"
echo ""

FAILED=0

echo "[1/4] Running unit tests..."
python3 tests/test_phase3.py
if [ $? -eq 0 ]; then
    echo "✅ Unit tests PASSED"
else
    echo "❌ Unit tests FAILED"
    FAILED=1
fi
echo ""

echo "[2/4] Running comprehensive tests..."
python3 tests/test_comprehensive.py
if [ $? -eq 0 ]; then
    echo "✅ Comprehensive tests PASSED"
else
    echo "❌ Comprehensive tests FAILED"
    FAILED=1
fi
echo ""

echo "[3/4] Running integration tests..."
python3 tests/test_integration.py
if [ $? -eq 0 ]; then
    echo "✅ Integration tests PASSED"
else
    echo "❌ Integration tests FAILED"
    FAILED=1
fi
echo ""

echo "[4/4] Verifying imports..."
cd "$(dirname "$0")/.." && python3 -c "
from recovery import HealthMonitor, CheckpointManager, SelfHealingController
print('✅ All imports work')
"
if [ $? -eq 0 ]; then
    echo "✅ Import verification PASSED"
else
    echo "❌ Import verification FAILED"
    FAILED=1
fi
echo ""

echo "========================================================================"
if [ $FAILED -eq 0 ]; then
    echo "✅ ALL TESTS PASSED - Phase 3 is production-ready!"
else
    echo "❌ SOME TESTS FAILED - Please review"
fi
echo "========================================================================"

exit $FAILED
