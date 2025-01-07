"""
OBS Audio Capture Alert Plugin
Monitors audio input devices and enables a specified source when silence is detected.

Features:
- Configurable silence threshold (in dB and duration)
- Supports enabling image, media or video sources
- Real-time audio level monitoring
- Configurable check interval timer so as to use fewer resources
- Event logging option for debugging
"""

import obspython as obs
from types import SimpleNamespace
from ctypes import *
from ctypes.util import find_library
import math

# Load the OBS library
obsffi = CDLL(find_library("obs"))
G = SimpleNamespace()

def wrap(funcname, restype, argtypes):
    """Simplify wrapping ctypes functions in obsffi"""
    func = getattr(obsffi, funcname)
    func.restype = restype
    func.argtypes = argtypes
    globals()["g_" + funcname] = func

class Source(Structure):
    pass

class Volmeter(Structure):
    pass

# Define the callback type for the volmeter
volmeter_callback_t = CFUNCTYPE(None, c_void_p, POINTER(c_float), POINTER(c_float), POINTER(c_float))

# Wrap OBS functions
wrap("obs_get_source_by_name", POINTER(Source), argtypes=[c_char_p])
wrap("obs_source_release", None, argtypes=[POINTER(Source)])
wrap("obs_volmeter_create", POINTER(Volmeter), argtypes=[c_int])
wrap("obs_volmeter_destroy", None, argtypes=[POINTER(Volmeter)])
wrap("obs_volmeter_add_callback", None, argtypes=[POINTER(Volmeter), volmeter_callback_t, c_void_p])
wrap("obs_volmeter_remove_callback", None, argtypes=[POINTER(Volmeter), volmeter_callback_t, c_void_p])
wrap("obs_volmeter_attach_source", c_bool, argtypes=[POINTER(Volmeter), POINTER(Source)])

# Volmeter callback function
@volmeter_callback_t
def volmeter_callback(data, mag, peak, input):
    G.noise = float(peak[0])  # Peak volume in dB

# Function to write volume to a file
def output_to_file(volume):
    with open("current_db_volume_of_source_status.txt", "w", encoding="utf-8") as f:
        f.write(f"Peak Volume: {volume} dB\n")

# Constants and global variables
OBS_FADER_LOG = 2
G.lock = False
G.start_delay = 1  # Delay before starting to monitor
G.duration = 0
G.noise = -math.inf  # Default value for noise (silence)
G.tick = 10000  # Default timer tick in milliseconds (10 seconds)
G.tick_mili = G.tick * 0.001
G.mic_source_name = ""  # Name of the audio capture source
G.image_source_name = ""  # Name of the image source to enable
G.media_source_name = ""  # Name of the media source to enable
G.video_source_name = ""  # Name of the video capture device to enable
G.volmeter = None  # Placeholder for the volmeter instance
G.callback = output_to_file  # Callback function for writing volume
G.silence_duration = 0  # Duration of silence in seconds
G.silence_threshold = 60  # Default silence threshold in seconds (1 minute)
G.silence_db_threshold = -60  # Silence threshold in dB (adjust as needed)
G.last_log_time = 0  # Last time the log file was written
G.plugin_enabled = False  # Plugin disabled by default
G.enable_only_active = False  # Only enable when streaming/recording
G.event_logging = True  # Event logging enabled by default

class _Functions:
    def __init__(self, source_name=None):
        self.source_name = source_name

    def set_visible_all(self, visible):
        """Cycle through all scenes, manually toggling visibility of the source"""
        if G.event_logging:
            print(f"Attempting to set visibility of '{self.source_name}' to {visible}")
        scenes = obs.obs_frontend_get_scenes()
        if not scenes:
            if G.event_logging:
                print("No scenes found!")
            return
        for scene in scenes:
            scene_test = obs.obs_scene_from_source(scene)
            if not scene_test:
                if G.event_logging:
                    print(f"Failed to get scene from source")
                continue
            in_scene = obs.obs_scene_find_source(scene_test, self.source_name)
            if in_scene:
                if G.event_logging:
                    print(f"Found source '{self.source_name}' in scene '{obs.obs_source_get_name(scene)}'")
                obs.obs_sceneitem_set_visible(in_scene, visible)
                if G.event_logging:
                    print(f"Set visibility of '{self.source_name}' to {visible}")
            else:
                if G.event_logging:
                    print(f"Source '{self.source_name}' not found in scene '{obs.obs_source_get_name(scene)}'")
        obs.source_list_release(scenes)

# Event loop for monitoring audio levels
def event_loop():
    """Check audio levels every tick interval."""
    global G
    
    # Check if plugin should be active based on streaming/recording state
    if G.enable_only_active:
        output_active = obs.obs_frontend_streaming_active() or obs.obs_frontend_recording_active()
        if not output_active:
            if G.event_logging:
                print("Not streaming or recording - plugin inactive")
            return
    
    if G.event_logging:
        print(f"G.noise = {G.noise} dB (Silence Duration: {G.silence_duration}s)")
    if G.duration > G.start_delay:
        if not G.lock:
            if G.event_logging:
                print("Initializing volmeter...")
            source = g_obs_get_source_by_name(G.mic_source_name.encode("utf-8"))
            if not source:
                print(f"Error: Audio Capture source '{G.mic_source_name}' not found!")
                return
            G.volmeter = g_obs_volmeter_create(OBS_FADER_LOG)
            if not G.volmeter:
                print("Error: Failed to create volmeter!")
                g_obs_source_release(source)
                return
            g_obs_volmeter_add_callback(G.volmeter, volmeter_callback, None)
            if g_obs_volmeter_attach_source(G.volmeter, source):
                g_obs_source_release(source)
                G.lock = True
                if G.event_logging:
                    print("Volmeter attached to Audio Capture source.")
            else:
                print("Error: Failed to attach volmeter to Audio Capture source!")
                g_obs_volmeter_destroy(G.volmeter)
                g_obs_source_release(source)
                return
        # Check for silence
        if G.noise <= G.silence_db_threshold or math.isinf(G.noise):  # Silence or -inf
            G.silence_duration += G.tick / 1000  # Increment silence duration by tick interval in seconds
            if G.silence_duration >= G.silence_threshold:
                if G.event_logging:
                    print(f"Silence detected for {G.silence_threshold} seconds. Enabling image source.")
                enable_source(True)
        else:
            G.silence_duration = 0
            enable_source(False)
        # Write to log file every tick interval
        G.callback(G.noise)
    else:
        G.duration += G.tick_mili  # Increment duration by tick interval

def enable_source(enable):
    """Enable or disable the specified source (image, media or video)."""
    source_name = G.image_source_name or G.media_source_name or G.video_source_name
    if not source_name:
        print("Error: No source selected!")
        return
    # Use the _Functions class to set visibility
    func = _Functions(source_name)
    func.set_visible_all(enable)
    if G.event_logging:
        print(f"Source '{source_name}' {'enabled' if enable else 'disabled'}")

def script_unload():
    # Remove timer
    obs.timer_remove(event_loop)
    # Clean up volmeter
    if G.volmeter:
        g_obs_volmeter_remove_callback(G.volmeter, volmeter_callback, None)
        g_obs_volmeter_destroy(G.volmeter)
        print("Volmeter and callback removed.")
    else:
        print("No volmeter to clean up.")

def script_defaults(settings):
    obs.obs_data_set_default_int(settings, "tick_interval", 10)  # Default to 10 seconds
    obs.obs_data_set_default_int(settings, "silence_threshold", 60)  # Default to 60 seconds

def script_properties():
    props = obs.obs_properties_create()
    
    # Audio Capture Source Section
    mic_list = obs.obs_properties_add_list(props, "mic_source_name", "Audio Capture Source",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_properties_add_text(props, "mic_source_help", 
        "Select the audio input device to monitor for silence.\nThis should be your microphone or audio capture source.",
        obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "sep1", "──────────────────────────────", obs.OBS_TEXT_INFO)

    # Source Selection Section
    source_list = obs.obs_properties_add_list(props, "combined_source", "Source",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    obs.obs_properties_add_text(props, "source_help",
        "Select the image, media or video source to enable when silence is detected.\nThis will be shown when your mic is silent.",
        obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "sep2", "──────────────────────────────", obs.OBS_TEXT_INFO)
    obs.obs_property_list_add_string(source_list, "Select a Source", "")

    # Timer Settings Section
    tick_interval = obs.obs_properties_add_int(props, "tick_interval", "Timer Interval (seconds)", 1, 60, 1)
    obs.obs_properties_add_text(props, "tick_interval_help",
        "How often (in seconds) to check audio levels.\nLower values are more responsive but use more CPU.",
        obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "sep3", "──────────────────────────────", obs.OBS_TEXT_INFO)

    # Silence Threshold Section
    silence_threshold = obs.obs_properties_add_int(props, "silence_threshold", "Silence Threshold Duration (seconds)", 1, 600, 1)
    obs.obs_properties_add_text(props, "silence_threshold_help",
        "How long (in seconds) of silence is required before enabling the source.\nPrevents brief pauses from triggering.",
        obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "sep4", "──────────────────────────────", obs.OBS_TEXT_INFO)

    # Plugin Control Section
    plugin_enabled = obs.obs_properties_add_bool(props, "plugin_enabled", "Enable Plugin Globally")
    obs.obs_properties_add_text(props, "plugin_enabled_help",
        "Enable the plugin.\nWhen not checked the plugin is disabled regardless of any other option.",
        obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "sep5", "──────────────────────────────", obs.OBS_TEXT_INFO)
    enable_only_active = obs.obs_properties_add_bool(props, "enable_only_active", "Enable only when streaming/recording")
    obs.obs_properties_add_text(props, "enable_only_active_help",
        "Only enable the plugin when actively streaming or recording.\nWhen disabled, plugin works in all OBS states.",
        obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "sep6", "──────────────────────────────", obs.OBS_TEXT_INFO)

    # Logging Section
    event_logging = obs.obs_properties_add_bool(props, "event_logging", "Enable Event Logging")
    obs.obs_properties_add_text(props, "event_logging_help",
        "Enable detailed logging of plugin events to the OBS log file.\nUseful for debugging but may impact performance.",
        obs.OBS_TEXT_INFO)
    obs.obs_properties_add_text(props, "sep6", "──────────────────────────────", obs.OBS_TEXT_INFO)

    # Populate dropdowns with available sources
    sources = obs.obs_enum_sources()
    if sources:
        for source in sources:
            source_id = obs.obs_source_get_id(source)
            name = obs.obs_source_get_name(source)
            # Add audio and video sources to the audio capture dropdown
            if source_id in ["wasapi_input_capture", "wasapi_output_capture", "coreaudio_input_capture", "dshow_input"]:
                obs.obs_property_list_add_string(mic_list, name, name)
            # Add image, media and video sources to combined dropdown
            if source_id == "image_source":  # OBS image source ID
                obs.obs_property_list_add_string(source_list, f"Image: {name}", f"Image: {name}")
            elif source_id == "ffmpeg_source":  # OBS media source ID
                obs.obs_property_list_add_string(source_list, f"Media: {name}", f"Media: {name}")
            elif source_id == "dshow_input":  # OBS video capture device ID
                obs.obs_property_list_add_string(source_list, f"Video: {name}", f"Video: {name}")
        obs.source_list_release(sources)
    return props

def script_update(settings):
    G.mic_source_name = obs.obs_data_get_string(settings, "mic_source_name")
    # Parse combined source selection
    combined_source = obs.obs_data_get_string(settings, "combined_source")
    if G.event_logging:
        print(f"Raw combined source selection: '{combined_source}'")
    if combined_source and combined_source.startswith("Image:"):
        G.image_source_name = combined_source[6:].strip()  # Remove "Image:" prefix and trim whitespace
        G.media_source_name = ""
        G.video_source_name = ""
        if G.event_logging:
            print(f"Selected image source: {G.image_source_name}")
    elif combined_source and combined_source.startswith("Media:"):
        G.media_source_name = combined_source[6:].strip()  # Remove "Media:" prefix and trim whitespace
        G.image_source_name = ""
        G.video_source_name = ""
        if G.event_logging:
            print(f"Selected media source: {G.media_source_name}")
    elif combined_source and combined_source.startswith("Video:"):
        G.video_source_name = combined_source[6:].strip()  # Remove "Video:" prefix and trim whitespace
        G.image_source_name = ""
        G.media_source_name = ""
        if G.event_logging:
            print(f"Selected video source: {G.video_source_name}")
    else:
        G.image_source_name = ""
        G.media_source_name = ""
        G.video_source_name = ""
        if G.event_logging:
            print("No valid source selected")
    G.tick = (obs.obs_data_get_int(settings, "tick_interval") or 10) * 1000  # Convert seconds to milliseconds, default to 10
    G.silence_threshold = obs.obs_data_get_int(settings, "silence_threshold") or 60  # Default to 60
    # Get current values before updating
    prev_plugin_enabled = G.plugin_enabled
    prev_enable_only_active = G.enable_only_active
    
    # Update settings
    G.plugin_enabled = obs.obs_data_get_bool(settings, "plugin_enabled")
    G.enable_only_active = obs.obs_data_get_bool(settings, "enable_only_active")
    G.event_logging = obs.obs_data_get_bool(settings, "event_logging")
    
    # Reset silence duration if plugin enabled state changed
    if prev_plugin_enabled != G.plugin_enabled or prev_enable_only_active != G.enable_only_active:
        G.silence_duration = 0
        if G.event_logging:
            print("Reset silence duration due to plugin state change")
    
    # Remove existing timer if any
    obs.timer_remove(event_loop)
    # Only add timer if plugin is enabled
    if G.plugin_enabled:
        obs.timer_add(event_loop, G.tick)
    if G.event_logging:
        print(f"Audio Capture Source: {G.mic_source_name}")
        print(f"Image Source: {G.image_source_name}")
        print(f"Video Source: {G.video_source_name}")
        print(f"Timer Interval: {G.tick / 1000} seconds")
        print(f"Silence Threshold Duration: {G.silence_threshold} seconds")
        print(f"Plugin Enabled: {G.plugin_enabled}")
    # Removed the else clause that was causing log spam

# Add the event loop to the OBS timer
if G.plugin_enabled:
    obs.timer_add(event_loop, G.tick)
