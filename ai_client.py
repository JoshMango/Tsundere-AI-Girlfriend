"""Wraps the Gemini API so the rest of the app only has to call brain.reply(text)."""  # explains what this file is for

import time  # used to pause between retries

from google import genai  # the official Google Gen AI SDK (pip package: google-genai)
from google.genai import types  # typed config objects used to pass parameters to the model

import config  # our settings: API key, model name, temperature, etc.
from personality import SYSTEM_PROMPT  # the tsundere personality instructions

BUSY_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "OVERLOADED")  # error text that means "temporary, try again"
MAX_RETRIES = 3  # how many times to retry the same model before giving up on it
RETRY_DELAYS = (2, 4, 8)  # seconds to wait before each retry (gets longer each time)


def _is_busy(error):  # checks whether an error is a temporary overload / rate limit
    return any(marker in str(error).upper() for marker in BUSY_MARKERS)  # True if the error text contains a "busy" marker


def _is_not_found(error):  # checks whether an error means "this model name doesn't exist"
    return getattr(error, "code", None) == 404 or "NOT_FOUND" in str(error).upper()  # HTTP 404 or the NOT_FOUND status text


def explain_error(error, model, role="main"):  # turns a scary API error into a short, friendly explanation
    """Return a casual, plain-English message saying what went wrong and what to do. role is 'main' or 'backup'."""  # description
    text = str(error).upper()  # upper-case copy of the error for easy matching
    code = getattr(error, "code", None)  # the HTTP status number, if the SDK provided one
    env_name = "GEMINI_FALLBACK_MODEL" if role == "backup" else "GEMINI_MODEL"  # which .env setting controls this model
    label = "backup" if role == "backup" else "main"  # word used in the message

    if _is_not_found(error):  # the model name doesn't exist (or isn't available to your key)
        message = (  # build the message
            f"[!] Oops, I can't find the {label} AI model '{model}'. It's probably been renamed or retired.\n"  # what happened
            f"Open your .env file and change {env_name} to a model that exists, "  # what to do
            "like gemini-3.8-flash or gemini-3.5-flash-lite."  # example names
        )  # end of message
    elif code in (401, 403) or "API KEY" in text or "API_KEY" in text or "PERMISSION_DENIED" in text or "UNAUTHENTICATED" in text:  # key problems
        message = (  # build the message
            "[!] Hmm, Google didn't like your API key.\n"  # what happened
            "Double-check GEMINI_API_KEY in your .env file (no spaces or quotes around it). "  # what to do
            "You can grab a fresh one at https://aistudio.google.com/apikey"  # where to get one
        )  # end of message
    elif code == 429 or "429" in text or "RESOURCE_EXHAUSTED" in text or "QUOTA" in text:  # usage limits
        message = (  # build the message
            "[!] Whoa, slow down a bit! You've used up Google's free limit for now.\n"  # what happened
            "Give it a minute and try again. If it keeps happening, you might be out of free messages for today."  # what to do
        )  # end of message
    elif _is_busy(error):  # servers overloaded
        message = (  # build the message
            "[!] Google's AI is super busy right now. It's not you, I promise.\n"  # what happened
            "Just wait a few seconds and send that again!"  # what to do
        )  # end of message
    elif code == 400 or "INVALID_ARGUMENT" in text:  # Google rejected the request settings
        message = (  # build the message
            "[!] Google didn't understand that request, so one of your settings might be off.\n"  # what happened
            "Take a look at GEMINI_MODEL, TEMPERATURE, TOP_P and MAX_OUTPUT_TOKENS in your .env file."  # what to do
        )  # end of message
    elif any(word in text for word in ("CONNECT", "GETADDRINFO", "TIMED OUT", "TIMEOUT", "NAME RESOLUTION", "NETWORK")):  # internet problems
        message = (  # build the message
            "[!] I can't reach Google right now. Looks like your internet might be acting up.\n"  # what happened
            "Check your connection and try again."  # what to do
        )  # end of message
    else:  # anything we don't recognise
        short = str(error).replace("\n", " ")[:160]  # first part of the raw error for debugging
        message = f"[!] Hmm, something weird happened and I'm not sure what.\nHere's a peek in case it helps: {short}"  # show a short technical hint

    if role == "backup":  # the backup model failed after the main one already failed
        message = "The main model didn't work, so I tried the backup, and that one failed too.\n" + message  # explain the sequence, then the reason
    return message  # the friendly text shown in the chat


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

    def _try_send(self, chat, user_text):  # sends the message, retrying only while the server is busy
        for attempt in range(MAX_RETRIES + 1):  # first try + the retries
            try:  # wrap the network call
                response = chat.send_message(user_text)  # sends your text (plus history) to Gemini
                return (response.text or "").strip()  # return the reply text (empty string if none)
            except Exception as error:  # any error from the API
                if not _is_busy(error) or attempt == MAX_RETRIES:  # not a busy error, or out of retries
                    raise  # pass the error up to the caller
                time.sleep(RETRY_DELAYS[attempt])  # wait a bit, then loop and try again

    def reply(self, user_text):  # sends your message and returns her answer as a string
        """Send one user message to the model and return the text reply (or a friendly error message)."""  # method description
        try:  # try the current model first
            text = self._try_send(self.chat, user_text)  # send the message (with retries if busy)
        except Exception as error:  # the current model failed
            print(f"[ai error] {error}")  # print the full technical error in the console for debugging
            fallback = config.GEMINI_FALLBACK_MODEL  # the backup model name (may be empty)
            can_switch = (_is_busy(error) or _is_not_found(error)) and fallback and fallback != self.model  # only switch for "busy" or "not found"
            if not can_switch:  # no usable backup, or a different kind of error
                return explain_error(error, self.model, "main")  # show a simple explanation
            try:  # try the backup model
                backup_chat = self._make_chat(fallback, self.chat.get_history())  # new chat that keeps the old history
                text = self._try_send(backup_chat, user_text)  # send the message again
            except Exception as fallback_error:  # the backup failed too
                print(f"[ai backup error] {fallback_error}")  # print the technical error for debugging
                return explain_error(fallback_error, fallback, "backup")  # show a simple explanation (we stay on the main model)
            self.chat = backup_chat  # the backup worked, so keep using it from now on
            self.model = fallback  # remember which model is active
        return text or "H-huh?! I lost my words for a second... say that again, baka!"  # fallback line if the reply was empty