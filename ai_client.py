"""Wraps the Gemini API so the rest of the app only has to call brain.reply(text)."""  # explains what this file is for

import time  # used to pause between retries

from google import genai  # the official Google Gen AI SDK (pip package: google-genai)
from google.genai import types  # typed config objects used to pass parameters to the model

import config  # our settings: API key, model name, temperature, etc.
from personality import SYSTEM_PROMPT  # the tsundere personality instructions

BUSY_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")  # error text that means "temporary, try again"
MAX_RETRIES = 3  # how many times to retry the same model before giving up on it
RETRY_DELAYS = (2, 4, 8)  # seconds to wait before each retry (gets longer each time)


class TsundereBrain:  # one instance = one ongoing conversation with her
    """Keeps a running chat session so she remembers what you said earlier."""  # class description

    def __init__(self):  # runs once when the object is created
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)  # creates the API client using your key
        self.model = config.GEMINI_MODEL  # the model currently in use
        self.chat = self._make_chat(self.model)  # start a chat session with the main model

    def _make_chat(self, model, history=None):  # builds a chat session for a given model
        return self.client.chats.create(  # starts a multi-turn chat session
            model=model,  # which Gemini model to use
            history=history,  # earlier messages to carry over (None = fresh chat)
            config=types.GenerateContentConfig(  # the parameters we pass along with every message
                system_instruction=SYSTEM_PROMPT,  # permanent instructions that define her personality
                temperature=config.TEMPERATURE,  # how random/creative the replies are
                top_p=config.TOP_P,  # nucleus sampling cutoff
                max_output_tokens=config.MAX_OUTPUT_TOKENS,  # maximum reply length
            ),  # end of the config object
        )  # end of chats.create(...)

    @staticmethod  # this helper doesn't need access to "self"
    def _is_busy(error):  # checks whether an error is a temporary overload
        return any(marker in str(error) for marker in BUSY_MARKERS)  # True if the error text contains a "busy" marker

    def _try_send(self, user_text):  # sends the message, retrying while the server is busy
        last_error = None  # remembers the most recent error
        for attempt in range(MAX_RETRIES + 1):  # first try + the retries
            try:  # wrap the network call
                response = self.chat.send_message(user_text)  # sends your text (plus history) to Gemini
                return (response.text or "").strip()  # return the reply text (empty string if none)
            except Exception as error:  # any error from the API
                last_error = error  # remember it
                if not self._is_busy(error) or attempt == MAX_RETRIES:  # not a busy error, or out of retries
                    raise  # pass the error up to the caller
                time.sleep(RETRY_DELAYS[attempt])  # wait a bit, then loop and try again
        raise last_error  # safety net (normally never reached)

    def reply(self, user_text):  # sends your message and returns her answer as a string
        """Send one user message to the model and return the text reply."""  # method description
        try:  # wrap everything so a failure doesn't crash the window
            text = self._try_send(user_text)  # try the current model (with retries)
        except Exception as error:  # the current model failed even after retries
            fallback = config.GEMINI_FALLBACK_MODEL  # the backup model name (may be empty)
            if self._is_busy(error) and fallback and fallback != self.model:  # busy error and a different backup exists
                try:  # try the backup model
                    history = self.chat.get_history()  # copy the conversation so far
                    self.model = fallback  # switch to the backup model from now on
                    self.chat = self._make_chat(self.model, history)  # new chat that keeps the old history
                    text = self._try_send(user_text)  # send the message again
                except Exception as fallback_error:  # backup failed too
                    return f"*the servers are too busy right now, try again in a minute* ({fallback_error})"  # friendly failure message
            elif self._is_busy(error):  # busy and no backup available
                return "*the servers are too busy right now, try again in a minute*"  # friendly failure message
            else:  # a different kind of error (bad key, 404, etc.)
                return f"*something went wrong* ({error})"  # show the real error so you can debug
        return text or "H-huh?! I lost my words for a second... say that again, baka!"  # fallback line if the reply was empty