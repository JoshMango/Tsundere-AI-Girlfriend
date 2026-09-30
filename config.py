"""Central settings for the tsundere girlfriend app (all values can be overridden in the .env file)."""  # explains what this file is for

import os  # standard library module used to read environment variables
from dotenv import load_dotenv  # reads KEY=value lines from a .env file

load_dotenv()  # loads the .env file (if present) into the process environment

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # your secret Google AI Studio key; empty string if missing
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # which Gemini model answers; change it in .env if needed
CHARACTER_NAME = os.getenv("CHARACTER_NAME", "Mika")  # the girlfriend's name shown in the window and used in her prompt
USER_NAME = os.getenv("USER_NAME", "Darling")  # the name she (reluctantly) calls you
TEMPERATURE = float(os.getenv("TEMPERATURE", "1.0"))  # creativity: higher = more random/spicy replies, lower = more predictable
TOP_P = float(os.getenv("TOP_P", "0.95"))  # nucleus sampling: only consider the most likely words adding up to this probability
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))  # hard cap on reply length (she is told to keep it short anyway)
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")  # backup model used if the main one stays overloaded (empty = none)