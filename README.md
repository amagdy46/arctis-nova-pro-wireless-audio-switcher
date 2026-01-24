# SteelSeries Arctis Nova Pro Wireless Audio Switcher for Linux

Automatically switch audio output between your SteelSeries Arctis Nova Pro Wireless headset and speakers when you turn the headset on/off.

## The Problem

When you turn off the Arctis Nova Pro Wireless headset, Linux doesn't detect this because the USB DAC (base station) remains connected. This means audio continues playing to a disconnected headset instead of switching to your speakers.

## The Solution

A lightweight Python daemon that monitors the headset's power state via the HID protocol and automatically switches PipeWire/WirePlumber audio output.

## How It Works

The script communicates with the headset's base station over HID (Human Interface Device) protocol:
- Sends status query command `0x06 0xb0` to interface 4
- Reads response byte 15 for headset state:
  - `0x01` = Headset OFF
  - `0x08` = Headset ON
  - `0x02` = Headset charging
- Switches default audio sink using `wpctl`

Protocol details from [HeadsetControl](https://github.com/Sapd/HeadsetControl).

## Requirements

- Linux with PipeWire and WirePlumber
- Python 3.6+
- SteelSeries Arctis Nova Pro Wireless (Vendor: 1038, Product: 12e0 or 12e5)

## Installation

### 1. Find your speaker sink name

```bash
wpctl status
```

Look for your speaker under "Sinks". Note the name (e.g., "Starship/Matisse").

Example output:
```
Audio
 ├─ Sinks:
 │      52. Arctis Nova Pro Wireless Analog Stereo [vol: 1.00]
 │      57. Starship/Matisse HD Audio Controller Analog Stereo [vol: 0.40]
```

### 2. Install the script

```bash
# Create directory
mkdir -p ~/.local/bin

# Copy the script
cp arctis-audio-switcher.py ~/.local/bin/

# Make it executable
chmod +x ~/.local/bin/arctis-audio-switcher.py
```

**Edit the script** to set your speaker name (headphones are auto-detected):
```python
HEADPHONE_SINK_NAME = "Arctis Nova Pro"  # Usually don't need to change
SPEAKER_SINK_NAME = "Starship/Matisse"   # Change this to match your speakers
```

The script finds sinks by name, so it works even if sink IDs change after reboot.

### 3. Set up udev rules (allows access without root)

```bash
sudo cp 99-steelseries-arctis-nova-pro.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 4. Install the systemd service

```bash
# Copy service file
cp arctis-audio-switcher.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable and start
systemctl --user enable --now arctis-audio-switcher.service
```

## Usage

Once installed, the service runs automatically:

- **Turn headset ON** → Audio switches to headset
- **Turn headset OFF** → Audio switches to speakers

### Commands

```bash
# Check status
systemctl --user status arctis-audio-switcher

# View logs
journalctl --user -u arctis-audio-switcher -f

# Restart
systemctl --user restart arctis-audio-switcher

# Stop
systemctl --user stop arctis-audio-switcher

# Disable
systemctl --user disable arctis-audio-switcher
```

## Troubleshooting

### Permission denied on /dev/hidraw*

Make sure the udev rules are installed and reload them:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

You may need to unplug and replug the USB connection.

### Service fails to start

Check which hidraw devices exist:
```bash
ls -la /dev/hidraw*
```

Verify the device is detected:
```bash
for i in /dev/hidraw*; do
  echo "=== $i ==="
  cat /sys/class/hidraw/$(basename $i)/device/uevent 2>/dev/null | grep -E "HID_NAME|HID_PHYS"
done
```

Look for `SteelSeries Arctis Nova Pro Wireless` with `input4` in the path.

### Sink not found

If the script can't find your sink, check that the name pattern in the configuration matches your device. Run `wpctl status` and look for your speaker name under "Sinks".

## Supported Devices

- SteelSeries Arctis Nova Pro Wireless (1038:12e0)
- SteelSeries Arctis Nova Pro Wireless X (1038:12e5)

## Credits

- Protocol reverse engineering: [HeadsetControl](https://github.com/Sapd/HeadsetControl) by Sapd
- Additional protocol docs: [Arctis-on-Linux](https://github.com/dfanara/Arctis-on-Linux) by dfanara

## License

MIT License - See [LICENSE](LICENSE) for details.
