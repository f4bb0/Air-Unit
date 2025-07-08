#!/bin/bash

# Check if conda environment 'air-unit' exists
if ! conda env list | grep -q "air-unit"; then
    echo "Creating conda environment 'air-unit'..."
    conda create -n air-unit python=3.9 -y
fi

# Activate the conda environment
echo "Activating conda environment 'air-unit'..."
conda activate air-unit

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing packages from requirements.txt..."
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found"
fi

# Run main.py if it exists
if [ -f "main.py" ]; then
    echo "Running main.py..."
    cd modules
    python main.py
else
    echo "Error: main.py not found"
fi
