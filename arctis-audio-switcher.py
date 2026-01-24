#!/usr/bin/env python3
"""
SteelSeries Arctis Nova Pro Wireless Audio Switcher

Monitors the headphone's on/off state via HID protocol and automatically
switches PipeWire audio output between headphones and speakers.

Protocol based on HeadsetControl:
https://github.com/Sapd/HeadsetControl/blob/master/lib/devices/steelseries_arctis_nova_pro_wireless.hpp
"""

import os
import subprocess
import time
import sys
import select
import glob

# Force unbuffered output for systemd
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# =============================================================================
# CONFIGURATION - Edit these values for your setup
# =============================================================================

# Audio sink names (partial match, case-insensitive)
HEADPHONE_SINK_NAME = "Arctis Nova Pro"
SPEAKER_SINK_NAME = "Starship/Matisse"  # Change this to match your speakers

# Poll interval in seconds
POLL_INTERVAL = 1.0

# =============================================================================
# Device constants (don't change unless you know what you're doing)
# =============================================================================

VENDOR_ID = "1038"
PRODUCT_IDS = ["12E0", "12E5"]  # Nova Pro Wireless and Nova Pro Wireless X

# HID command to poll battery/status (from HeadsetControl)
POLL_COMMAND = bytes([0x06, 0xb0] + [0x00] * 29)

# Response codes (response[15] contains status)
HEADSET_OFFLINE = 0x01
HEADSET_CHARGING = 0x02
HEADSET_ONLINE = 0x08


def find_hidraw_device():
    """Find the correct hidraw device for the Arctis Nova Pro (interface 4)."""
    hidraw_devices = glob.glob("/dev/hidraw*")

    for device in sorted(hidraw_devices):
        try:
            device_num = device.replace("/dev/hidraw", "")
            sysfs_path = f"/sys/class/hidraw/hidraw{device_num}/device"
            uevent_path = os.path.join(sysfs_path, "uevent")

            if not os.path.exists(uevent_path):
                continue

            with open(uevent_path, "r") as f:
                uevent = f.read().upper()

            # Check vendor ID
            if VENDOR_ID not in uevent:
                continue

            # Check product ID
            if not any(pid in uevent for pid in PRODUCT_IDS):
                continue

            # Check if this is interface 4 (the control interface)
            if "INPUT4" not in uevent:
                print(f"Skipping {device} - not interface 4")
                continue

            print(f"Found Arctis Nova Pro on {device} (interface 4)")
            return device

        except Exception:
            continue

    return None


def get_headset_state(fd):
    """Poll the headset state and return ON, OFF, or None on error."""
    try:
        os.write(fd, POLL_COMMAND)

        # Wait for response with timeout
        r, _, _ = select.select([fd], [], [], 0.5)
        if not r:
            return None

        response = os.read(fd, 128)
        if len(response) < 16:
            return None

        status_byte = response[15]

        if status_byte == HEADSET_OFFLINE:
            return "OFF"
        elif status_byte in (HEADSET_ONLINE, HEADSET_CHARGING):
            return "ON"
        else:
            return None

    except Exception as e:
        print(f"Error polling headset: {e}")
        return None


def find_sink_id(name_pattern):
    """Find a sink ID by name pattern using wpctl status."""
    try:
        result = subprocess.run(
            ["wpctl", "status"],
            capture_output=True,
            text=True,
            check=False
        )

        in_sinks_section = False
        for line in result.stdout.split("\n"):
            # Detect Sinks section
            if "Sinks:" in line:
                in_sinks_section = True
                continue

            # Stop at next section
            if in_sinks_section and (":" in line and "│" not in line):
                break

            if in_sinks_section and name_pattern.lower() in line.lower():
                # Parse sink ID from lines like: " │      52. Arctis Nova Pro Wireless Analog Stereo [vol: 0.95]"
                # Look for "Analog Stereo" to get the playback sink, not the device
                if "Analog Stereo" in line or "Stereo" in line:
                    parts = line.split(".")
                    if len(parts) >= 2:
                        # Extract the number before the dot
                        num_part = parts[0].strip().split()[-1]
                        if num_part.isdigit():
                            return int(num_part)

        return None
    except Exception as e:
        print(f"Error finding sink: {e}")
        return None


def switch_audio(sink_name_pattern, friendly_name):
    """Switch the default audio sink by name pattern."""
    sink_id = find_sink_id(sink_name_pattern)
    if sink_id is None:
        print(f"WARNING: Could not find sink matching '{sink_name_pattern}'")
        return

    print(f"Switching audio to {friendly_name} (sink {sink_id})")
    subprocess.run(["wpctl", "set-default", str(sink_id)], check=False)


def main():
    print("SteelSeries Arctis Nova Pro Audio Switcher starting...")

    device = find_hidraw_device()
    if not device:
        print("ERROR: Could not find Arctis Nova Pro HID device (interface 4)")
        print("Make sure the device is connected and udev rules are in place")
        sys.exit(1)

    print(f"Using device: {device}")

    try:
        fd = os.open(device, os.O_RDWR)
    except PermissionError:
        print(f"ERROR: Permission denied accessing {device}")
        print("Make sure udev rules are installed and you've re-plugged the device")
        sys.exit(1)

    last_state = None
    print("Monitoring headset state...")

    try:
        while True:
            state = get_headset_state(fd)

            if state and state != last_state:
                print(f"Headset state changed: {last_state} -> {state}")

                if state == "ON":
                    switch_audio(HEADPHONE_SINK_NAME, "Headphones")
                elif state == "OFF":
                    switch_audio(SPEAKER_SINK_NAME, "Speakers")

                last_state = state

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
