#!/bin/bash

# Fix USB device permissions for current user
# This script adds user to necessary groups and sets up udev rules

echo "Fixing USB device permissions..."

# Get current username
USERNAME=$(whoami)

# Add user to necessary groups
echo "Adding user $USERNAME to dialout, tty, and video groups..."
sudo usermod -a -G dialout,tty,video $USERNAME

# Create udev rules for USB devices
echo "Creating udev rules for USB devices..."
sudo tee /etc/udev/rules.d/99-usb-permissions.rules > /dev/null << 'EOF'
# USB serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="*", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"

# Video devices
SUBSYSTEM=="video4linux", MODE="0666", GROUP="video"
KERNEL=="video*", MODE="0666", GROUP="video"

# General USB devices
SUBSYSTEM=="usb", MODE="0666"
EOF

# Reload udev rules
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

# Show current user groups
echo "Current user groups:"
groups $USERNAME

echo ""
echo "Permission fix completed!"
echo "Please log out and log back in (or reboot) for group changes to take effect."
echo "After relogging, you should be able to access /dev/ttyUSB* devices without sudo."

# Make the device accessible immediately (temporary fix)
if [ -e /dev/ttyUSB1 ]; then
    sudo chmod 666 /dev/ttyUSB1
    echo "Temporary fix applied to /dev/ttyUSB1"
fi
