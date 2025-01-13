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
2. Add obs.dll to system path
    This plugin dynamically links into the obs library at runtime so make sure obs.
        
        To add `obs.dll` to the system path in Windows, follow these steps:

        1. **Locate `obs.dll`**: Find the directory where `obs.dll` is located. This is usually in the `bin` folder of your OBS Studio installation directory.
        (Right click obs select open file location)

        2. **Open System Environment Variables**:
        - Right-click on the `This PC` or `My Computer` icon on your desktop or in File Explorer.
        - Select `Properties`.
        - Click on `Advanced system settings` on the left side.
        - In the System Properties window, click on the `Environment Variables` button.

        3. **Edit the System Path**:
        - In the Environment Variables window, under the `System variables` section, find the variable named `Path` and select it.
        - Click on the `Edit` button.
        - In the Edit Environment Variable window, click on the `New` button.
        - Enter the full path to the directory containing `obs.dll` (e.g., `C:\Program Files\obs-studio\bin`).

        4. **Save Changes**:
        - Click `OK` to close each of the open windows.
        - Restart PC may be required, but was not for me.

2. Restart OBS Studio
3. Configure through OBS settings
NOTES:
    This is a python plugin for OBS. You might have to install python and link it in the Tools->Scripts - Python Settings of OBS.

## Usage
1. Select audio input device to monitor
2. Set silence detection threshold
3. Choose alert (Image or Media Source)
4. Save settings and enable monitoring

## Support
For issues or feature requests, please open an issue on GitHub.
