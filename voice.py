"""Text-to-speech: expressive anime voices via the local VOICEVOX engine, with edge-tts as a backup."""  # explains what this file is for

import asyncio  # edge-tts (the backup voice) is asynchronous, so we need asyncio
import os  # file paths, environment variables, and deleting temp files
import re  # regular expressions, used to strip *actions* out of the spoken text
import tempfile  # creates temporary audio files for each spoken line
import threading  # lets speech run in the background without freezing the window

import edge_tts  # backup text-to-speech used when VOICEVOX isn't running
import pygame  # used here only for its audio player (mixer)
import requests  # sends HTTP requests to the local VOICEVOX engine

VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021")  # where the VOICEVOX engine listens (default port 50021)
SFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx")  # optional folder for real sound-effect recordings
SFX_MAP = {"ふん": "hmph.wav", "むぅ": "mu.wav", "はぁ": "sigh.wav", "ちっ": "tsk.wav"}  # line starts with this -> play this file first
FALLBACK_VOICE = "ja-JP-NanamiNeural"  # the backup edge-tts voice if VOICEVOX is unavailable

# Each preset picks a different VOICEVOX character + style, plus tuning:
#   speed = talking speed (1.0 normal), pitch = -0.15..+0.15 shift, intonation = how expressive/exaggerated (1.0 normal),
#   volume = loudness (1.0 normal).
VOICE_PRESETS = {  # dictionary of all voice choices shown in the dropdown
    "Classic Tsundere": {"character": "九州そら", "style": "ツンツン", "speed": 1.05, "pitch": 0.0, "intonation": 1.4, "volume": 1.1},  # snappy, sharp girl
    "Sassy & Grumpy (loud)": {"character": "四国めたん", "style": "ツンツン", "speed": 1.2, "pitch": 0.02, "intonation": 1.7, "volume": 1.6},  # fast, loud, annoyed
    "Soft & Shy": {"character": "雨晴はう", "style": "ノーマル", "speed": 0.88, "pitch": 0.06, "intonation": 1.25, "volume": 0.9},  # higher, slower, quiet
    "Cool Ojou-sama": {"character": "波音リツ", "style": "クイーン", "speed": 0.95, "pitch": -0.03, "intonation": 1.3, "volume": 1.1},  # proud, calm, lower
    "Bratty Sweet": {"character": "四国めたん", "style": "あまあま", "speed": 1.1, "pitch": 0.05, "intonation": 1.5, "volume": 1.2},  # sugary but bratty
    "Genki Rival": {"character": "春日部つむぎ", "style": "ノーマル", "speed": 1.2, "pitch": 0.03, "intonation": 1.6, "volume": 1.4},  # energetic, competitive
    "Gentle Big-Sis Dere": {"character": "もち子さん", "style": "ノーマル", "speed": 0.95, "pitch": 0.0, "intonation": 1.2, "volume": 1.0},  # warm, mature, soft
}  # end of presets

SAMPLE_LINE = "ふんっ！これが私の声よ、バカ！な、慣れないでよね！"  # Japanese line spoken when you pick a new voice


class VoiceEngine:  # handles turning text into audio and playing it
    """Generates speech with VOICEVOX (or edge-tts as backup) and plays it with pygame in background threads."""  # class description

    def __init__(self):  # runs once when the object is created
        self._lock = threading.Lock()  # makes sure only one line is spoken at a time
        self._speakers = None  # cache of the character list fetched from VOICEVOX
        self._style_ids = {}  # cache of preset name -> VOICEVOX style id
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

    @staticmethod  # this helper doesn't need access to "self"
    def _temp_path(suffix):  # makes an empty temporary file and returns its path
        file_descriptor, path = tempfile.mkstemp(suffix=suffix)  # create the temp file
        os.close(file_descriptor)  # close the low-level handle so other code can write to the path
        return path  # hand back the path

    def _load_speakers(self):  # asks VOICEVOX which characters/styles it has
        if self._speakers is None:  # only fetch once (retry later if it failed)
            try:  # the engine might not be running
                reply = requests.get(f"{VOICEVOX_URL}/speakers", timeout=3)  # request the character list
                reply.raise_for_status()  # raise an error for bad HTTP status codes
                self._speakers = reply.json()  # store the parsed list
            except requests.RequestException:  # connection refused, timeout, etc.
                return None  # signal "VOICEVOX not available"
        return self._speakers  # the cached list

    def _find_style_id(self, preset_name):  # converts a preset (character + style names) into VOICEVOX's numeric id
        if preset_name in self._style_ids:  # already looked up before
            return self._style_ids[preset_name]  # return the cached id
        speakers = self._load_speakers()  # get the character list
        if not speakers:  # VOICEVOX isn't reachable
            return None  # signal failure
        preset = VOICE_PRESETS[preset_name]  # the settings for this preset
        speaker = next((s for s in speakers if s["name"] == preset["character"]), None)  # find the character by name
        if speaker is None:  # character not found in this VOICEVOX version
            print(f"[voice] character '{preset['character']}' not found, using '{speakers[0]['name']}' instead")  # warn in the console
            speaker = speakers[0]  # fall back to the first character
        style = next((st for st in speaker["styles"] if st["name"] == preset["style"]), None)  # find the style by name
        if style is None:  # style not found for this character
            print(f"[voice] style '{preset['style']}' not found for {speaker['name']}, using '{speaker['styles'][0]['name']}'")  # warn
            style = speaker["styles"][0]  # fall back to that character's first style
        self._style_ids[preset_name] = style["id"]  # remember the id for next time
        return style["id"]  # hand back the id

    def _synth_voicevox(self, text, preset_name, path):  # creates a wav file with VOICEVOX; returns True on success
        style_id = self._find_style_id(preset_name)  # which voice to use
        if style_id is None:  # VOICEVOX isn't running
            return False  # tell the caller to use the backup voice
        preset = VOICE_PRESETS[preset_name]  # the tuning values for this preset
        try:  # network calls can fail
            query = requests.post(  # step 1: ask VOICEVOX to analyse the text
                f"{VOICEVOX_URL}/audio_query", params={"text": text, "speaker": style_id}, timeout=15  # text + voice id
            ).json()  # the analysis comes back as JSON we can edit
            query["speedScale"] = preset["speed"]  # set talking speed
            query["pitchScale"] = preset["pitch"]  # set pitch shift
            query["intonationScale"] = preset["intonation"]  # set how expressive the voice is
            query["volumeScale"] = preset["volume"]  # set loudness
            query["prePhonemeLength"] = 0.05  # tiny silence before speaking (keeps "ふんっ" from being clipped)
            if "！" in text or "!" in text:  # excited/angry line
                query["intonationScale"] *= 1.15  # make it even more expressive
                query["volumeScale"] *= 1.1  # and a little louder
            audio = requests.post(  # step 2: turn the analysis into audio
                f"{VOICEVOX_URL}/synthesis", params={"speaker": style_id}, json=query, timeout=60  # voice id + edited query
            )  # end of the request
            audio.raise_for_status()  # raise an error for bad HTTP status codes
            with open(path, "wb") as audio_file:  # open the temp wav file for writing bytes
                audio_file.write(audio.content)  # save the audio
            return True  # success
        except requests.RequestException as error:  # any network/engine problem
            print(f"[voice] VOICEVOX error: {error}")  # print to the console
            return False  # tell the caller to use the backup voice

    def _play_sfx(self, text):  # plays a real sound-effect file if the line starts with a reaction like ふん
        for keyword, filename in SFX_MAP.items():  # check each known reaction
            if text.startswith(keyword):  # the line starts with this reaction
                sfx_path = os.path.join(SFX_DIR, filename)  # where the recording would be
                if os.path.isfile(sfx_path):  # only if you actually added the file
                    sound = pygame.mixer.Sound(sfx_path)  # load the sound effect
                    sound.play()  # play it
                    pygame.time.wait(int(sound.get_length() * 1000))  # wait until it finishes
                    return text[len(keyword):].lstrip("っッ！!、,…~ー ")  # remove the reaction from the spoken text so it isn't said twice
                break  # no file found, so let the voice say it normally
        return text  # unchanged text

    @staticmethod  # this helper doesn't need access to "self"
    def _play(path):  # plays one audio file and waits until it ends
        pygame.mixer.music.load(path)  # load the audio into the player
        pygame.mixer.music.play()  # start playback
        while pygame.mixer.music.get_busy():  # keep looping while audio is still playing
            pygame.time.wait(100)  # sleep 100 ms between checks to avoid using CPU
        pygame.mixer.music.unload()  # release the file so Windows lets us delete it

    def speak(self, text, preset_name):  # public method: speak this text using the chosen voice preset
        """Start speaking in a background thread so the UI never freezes."""  # description
        if not self.available:  # if there is no audio device
            return  # do nothing
        threading.Thread(target=self._speak_worker, args=(text, preset_name), daemon=True).start()  # run the worker in the background

    def _speak_worker(self, text, preset_name):  # the function the background thread actually runs
        """Synthesize the line (VOICEVOX, else backup voice), play it, then clean up."""  # description
        clean_text = self._clean(text)  # strip out the *actions*
        if not clean_text:  # if nothing is left to say
            return  # skip speaking
        if preset_name not in VOICE_PRESETS:  # unknown preset name
            preset_name = next(iter(VOICE_PRESETS))  # use the first preset
        with self._lock:  # wait for any previous line to finish first
            clean_text = self._play_sfx(clean_text)  # play a real "hmph" recording first, if you added one
            if not clean_text:  # nothing left after removing the reaction
                return  # done
            wav_path = self._temp_path(".wav")  # temp file for VOICEVOX audio
            mp3_path = None  # temp file for backup audio (created only if needed)
            try:  # guard synthesis + playback
                if self._synth_voicevox(clean_text, preset_name, wav_path):  # try the expressive VOICEVOX voice
                    self._play(wav_path)  # play it
                else:  # VOICEVOX unavailable
                    print("[voice] VOICEVOX not running - using the backup voice")  # tell the user in the console
                    mp3_path = self._temp_path(".mp3")  # temp file for the backup audio
                    asyncio.run(edge_tts.Communicate(clean_text, FALLBACK_VOICE, rate="+8%", pitch="+4Hz").save(mp3_path))  # download backup speech
                    self._play(mp3_path)  # play it
            except Exception as error:  # any other failure
                print(f"[voice error] {error}")  # print to the console; the chat keeps working
            finally:  # always runs, even after an error
                for temp_file in (wav_path, mp3_path):  # both temp files
                    if temp_file:  # skip the one that was never created
                        try:  # deleting might fail if the file is still locked
                            os.remove(temp_file)  # delete the temp audio file
                        except OSError:  # ignore delete problems
                            pass  # nothing else to do

    def stop(self):  # stops any audio that is currently playing
        """Immediately stop playback (used when the window closes or voice is muted)."""  # description
        if self.available:  # only if audio is set up
            pygame.mixer.music.stop()  # halts the current voice line
            pygame.mixer.stop()  # halts any sound effect too