#!/usr/bin/env bash
# run_tests.sh — Run all pytest tests via uv for the Nutrition Tracker backend.
# Usage: bash tests/run_tests.sh  (must be run from the nutrition-tracker/ root)

set -e

echo "============================================================"
echo "  Nutrition Tracker Backend — Test Runner (uv)"
echo "============================================================"
echo ""

echo "[1/2] Running all tests with uv..."
echo ""

uv run --project . pytest backend/tests/ -v --tb=short 2>&1

EXIT_CODE=$?

echo ""
echo "============================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "  ✅ ALL TESTS PASSED"
else
    echo "  ❌ SOME TESTS FAILED (exit code: $EXIT_CODE)"
fi
echo "============================================================"

exit $EXIT_CODE
