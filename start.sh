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

# Check for video devices
echo "Checking for video devices..."
VIDEO_DEVICES=$(ls /dev/video* 2>/dev/null)

if [ -z "$VIDEO_DEVICES" ]; then
    echo "No video devices found"
else
    echo "Found video devices: $VIDEO_DEVICES"
    
    # Start GStreamer for each video device in separate screen sessions
    port=10000
    for device in $VIDEO_DEVICES; do
        session_name="gst_$(basename $device)"
        echo "Starting GStreamer for $device on port $port in screen session: $session_name"
        
        screen -dmS "$session_name" bash -c "
            gst-launch-1.0 v4l2src device=$device ! \
            image/jpeg,width=1280,height=720,framerate=30/1 ! \
            jpegdec ! \
            videoconvert ! \
            x264enc tune=zerolatency speed-preset=ultrafast intra-refresh=true key-int-max=30 ! \
            h264parse ! \
            mpegtsmux ! \
            srtsink uri='srt://47.109.142.1:$port?mode=caller&streamid=SRT_0n1in3&latency=50'
        "
        
        port=$((port + 10))
        if [ $port -gt 10090 ]; then
            echo "Warning: Maximum port 10090 reached, stopping device assignment"
            break
        fi
    done
    
    echo "All GStreamer sessions started. Use 'screen -list' to see running sessions."
    echo "To attach to a session, use: screen -r <session_name>"
fi

# Run main.py if it exists
if [ -f "main.py" ]; then
    echo "Running main.py..."
    cd modules
    python main.py
else
    echo "Error: main.py not found"
fi
