#!/bin/bash
cd "$(dirname "$0")"

# Try different Python paths
if command -v python3 &> /dev/null; then
    echo "Using python3"
    python3 manage.py migrate
elif command -v /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 &> /dev/null; then
    echo "Using full path python3"
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 manage.py migrate
elif command -v python &> /dev/null; then
    echo "Using python"
    python manage.py migrate
else
    echo "Python not found"
    exit 1
fi