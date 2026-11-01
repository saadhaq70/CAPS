#!/bin/bash
# Legacy command; starts the unified live-data dashboard.

echo "=========================================="
echo "ASH-FL Interactive Dashboard"
echo "=========================================="
echo ""
echo "Starting Streamlit server..."
echo "Dashboard will open at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

streamlit run unified_dashboard.py
