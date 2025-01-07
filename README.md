# AudioCaptureAlert
OBS Studio plugin providing real-time audio input monitoring with configurable silence detection and alert notifications.

## Use Cases
- Monitors and alerts if Mic becomes unplugged or runs out of battery.
- Monitors and alerts if an audio capture device is not playing audio (Double PC streaming setup).

## Features
- Real-time monitoring of audio input devices
- Configurable delay before showing source selected for alert
- Select an image or media source for alert
- Can be enabled only when recording or streaming automatically

## Installation
1. Copy the plugin files to your OBS plugins directory
2. Restart OBS Studio
3. Configure through OBS settings
NOTES:
    This is a python plugin for OBS. You might have to install python and link it in the scripts section of OBS.

## Usage
1. Select audio input device to monitor
2. Set silence detection threshold
3. Choose alert (Image or Media Source)
4. Save settings and enable monitoring

## Support
For issues or feature requests, please open an issue on GitHub.
