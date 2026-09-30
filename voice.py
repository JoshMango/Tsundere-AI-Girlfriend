"""Text-to-speech using Microsoft Edge's free neural voices (edge-tts) played through pygame."""  # explains what this file is for

import asyncio  # edge-tts is asynchronous, so we need asyncio to run it
import os  # used to delete the temporary audio files
import re  # regular expressions, used to strip *actions* out of the spoken text
import tempfile  # creates temporary mp3 files for each spoken line
import threading  # lets speech run in the background without freezing the window

import edge_tts  # library that downloads synthesized speech from Edge's TTS service
import pygame  # used here only for its audio player (mixer)

# Each preset = a display name -> which neural voice to use, plus speaking speed and pitch tweaks.
# Rate is a percentage (+10% = faster), pitch is in Hz (+4Hz = slightly higher). Tweak freely!
VOICE_PRESETS = {  # dictionary of all voice choices shown in the dropdown
    "Sharp & Sassy (US)": {"voice": "en-US-AriaNeural", "rate": "+12%", "pitch": "+3Hz"},  # quick, confident, bratty
    "Bratty Sweet (US)": {"voice": "en-US-JennyNeural", "rate": "+8%", "pitch": "+5Hz"},  # sweeter voice with a sharp edge
    "Soft Tsundere (US)": {"voice": "en-US-MichelleNeural", "rate": "+4%", "pitch": "+4Hz"},  # gentler, dere-leaning
    "Cool Ojou-sama (UK)": {"voice": "en-GB-SoniaNeural", "rate": "-2%", "pitch": "+2Hz"},  # posh, proud, rich-girl vibe
    "Grumpy Cutie (AU)": {"voice": "en-AU-NatashaNeural", "rate": "+5%", "pitch": "+6Hz"},  # grumpy but adorable
    "Shy & Flustered (CA)": {"voice": "en-CA-ClaraNeural", "rate": "-5%", "pitch": "+4Hz"},  # slower, embarrassed tone
    "Prideful Rival (IE)": {"voice": "en-IE-EmilyNeural", "rate": "+10%", "pitch": "+0Hz"},  # snappy rival-type voice
    "Kababayan Tsundere (PH)": {"voice": "en-PH-RosaNeural", "rate": "+5%", "pitch": "+4Hz"},  # Filipino-accent English
}  # end of presets

SAMPLE_LINE = "Hmph! This is my voice now, baka. D-don't get used to it!"  # line spoken when you pick a new voice


class VoiceEngine:  # handles turning text into audio and playing it
    """Generates speech with edge-tts and plays it with pygame, all in background threads."""  # class description

    def __init__(self):  # runs once when the object is created
        self._lock = threading.Lock()  # makes sure only one line is spoken at a time
        try:  # audio hardware can be missing, so we guard the setup
            pygame.mixer.init()  # starts pygame's audio system
            self.available = True  # remember that audio works
        except pygame.error:  # raised when no audio device is found
            self.available = False  # remember that audio does NOT work (app still runs, just silent)

    @staticmethod  # this helper doesn't need access to "self"
    def _clean(text):  # prepares text for speaking
        """Remove *action text* and leftover symbols so the voice doesn't read them out loud."""  # description
        no_actions = re.sub(r"\*[^*]*\*", "", text)  # deletes anything wrapped in asterisks, e.g. *looks away*
        return no_actions.replace("*", "").strip()  # removes stray asterisks and trims whitespace

    def speak(self, text, preset_name):  # public method: speak this text using the chosen voice preset
        """Start speaking in a background thread so the UI never freezes."""  # description
        if not self.available:  # if there is no audio device
            return  # do nothing
        threading.Thread(target=self._speak_worker, args=(text, preset_name), daemon=True).start()  # run the worker in the background

    def _speak_worker(self, text, preset_name):  # the function the background thread actually runs
        """Download the speech as an mp3, play it, then clean up the file."""  # description
        clean_text = self._clean(text)  # strip out the *actions*
        if not clean_text:  # if nothing is left to say
            return  # skip speaking
        preset = VOICE_PRESETS.get(preset_name, next(iter(VOICE_PRESETS.values())))  # look up the preset (default = first one)
        with self._lock:  # wait for any previous line to finish first
            file_descriptor, path = tempfile.mkstemp(suffix=".mp3")  # create a temporary mp3 file
            os.close(file_descriptor)  # close the low-level handle so edge-tts can write to the path
            try:  # guard the network + playback steps
                communicate = edge_tts.Communicate(  # build the speech request
                    clean_text,  # the text to speak
                    preset["voice"],  # which neural voice to use
                    rate=preset["rate"],  # speaking speed adjustment
                    pitch=preset["pitch"],  # pitch adjustment
                )  # end of Communicate(...)
                asyncio.run(communicate.save(path))  # download the audio into the temp file
                pygame.mixer.music.load(path)  # load the mp3 into the player
                pygame.mixer.music.play()  # start playback
                while pygame.mixer.music.get_busy():  # keep looping while audio is still playing
                    pygame.time.wait(100)  # sleep 100 ms between checks to avoid using CPU
                pygame.mixer.music.unload()  # release the file so Windows lets us delete it
            except Exception as error:  # any failure (no internet, service down, etc.)
                print(f"[voice error] {error}")  # print to the console; the chat keeps working
            finally:  # always runs, even after an error
                try:  # deleting might fail if the file is still locked
                    os.remove(path)  # delete the temporary mp3
                except OSError:  # ignore delete problems
                    pass  # nothing else to do

    def stop(self):  # stops any audio that is currently playing
        """Immediately stop playback (used when the window closes or voice is muted)."""  # description
        if self.available:  # only if audio is set up
            pygame.mixer.music.stop()  # halts the current sound
