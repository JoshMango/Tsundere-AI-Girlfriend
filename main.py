"""Entry point: opens a direct-message style popup window to chat with your tsundere girlfriend."""  # explains what this file is for
import re  # regular expressions, used to split her reply into English and Japanese
import os # builds file paths and lists the avatars folder
import threading  # runs the slow API call in the background so the window doesn't freeze
import tkinter as tk  # Python's built-in GUI toolkit (this is the popup window)
from tkinter import ttk, filedialog, messagebox  # themed widgets, file-picker dialog, and message popups

from PIL import Image, ImageDraw, ImageTk  # Pillow: open images, draw the circle mask, convert for Tk

import config  # our settings (API key, names, etc.)
from ai_client import TsundereBrain  # the class that talks to Gemini
from voice import VoiceEngine, VOICE_PRESETS, SAMPLE_LINE  # text-to-speech engine, voice choices, and a sample line

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # the folder this file lives in
AVATAR_DIR = os.path.join(BASE_DIR, "avatars")  # the folder holding the profile picture choices
AVATAR_SIZE = 56  # pixel size of the round profile picture in the header
IMAGE_TYPES = (".png", ".jpg", ".jpeg")  # file extensions treated as profile pictures

HEADER_BG = "#2f2a48"  # dark purple header colour
CHAT_BG = "#f4f1fa"  # very light lavender chat background
BOT_BUBBLE = "#ffd6e7"  # pink bubble colour for her messages
USER_BUBBLE = "#bfe0ff"  # blue bubble colour for your messages
INPUT_BG = "#ffffff"  # white background for the message box


def list_avatars():  # finds every image in the avatars folder
    """Return a dict of {pretty name: file path} for all png/jpg files in the avatars folder."""  # description
    found = {}  # will hold the results
    if not os.path.isdir(AVATAR_DIR):  # if the folder doesn't exist
        return found  # return an empty dict
    for filename in sorted(os.listdir(AVATAR_DIR)):  # loop through files in alphabetical order
        if filename.lower().endswith(IMAGE_TYPES):  # keep only png/jpg/jpeg files
            pretty = os.path.splitext(filename)[0].replace("_", " ").title()  # "hikari_pink.png" -> "Hikari Pink"
            found[pretty] = os.path.join(AVATAR_DIR, filename)  # store name -> full path
    return found  # hand back the dictionary


def make_round_photo(path, size):  # turns any image file into a circular Tk-compatible picture
    """Center-crop the image to a square, shrink it, and cut it into a circle."""  # description
    image = Image.open(path).convert("RGBA")  # open the file and make sure it has an alpha (transparency) channel
    side = min(image.size)  # the shorter edge decides the square size
    left = (image.width - side) // 2  # x offset to center the crop
    top = (image.height - side) // 2  # y offset to center the crop
    image = image.crop((left, top, left + side, top + side))  # crop to a centered square
    image = image.resize((size, size), Image.LANCZOS)  # shrink to the wanted size with smooth quality
    mask = Image.new("L", (size, size), 0)  # a black (fully transparent) grayscale mask
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)  # draw a white circle = visible area
    image.putalpha(mask)  # apply the mask so only the circle shows
    return ImageTk.PhotoImage(image)  # convert to a format Tkinter labels can display

def split_reply(raw):  # splits "EN: ... JP: ..." into two strings
    """Return (english, japanese). If the format is missing, japanese is empty."""  # description
    jp_match = re.search(r"JP:\s*(.*)", raw, re.S)  # everything after "JP:"
    en_match = re.search(r"EN:\s*(.*?)\s*(?=JP:|\Z)", raw, re.S)  # everything after "EN:" up to "JP:" or the end
    english = en_match.group(1).strip() if en_match else raw.strip()  # English part (or the whole text if no tag)
    japanese = jp_match.group(1).strip() if jp_match else ""  # Japanese part (empty if missing)
    return english, japanese  # hand both back

class ChatApp:  # the whole window and its behaviour
    """Builds the DM-style window and handles sending/receiving messages."""  # class description

    def __init__(self, root):  # runs once when the app starts
        self.root = root  # keep a reference to the main window
        self.root.title(f"{config.CHARACTER_NAME} - Direct Message")  # window title bar text
        self.root.geometry("440x700")  # starting window size (width x height)
        self.root.minsize(380, 540)  # smallest size the user can shrink it to
        self.root.configure(bg=CHAT_BG)  # window background colour

        self.brain = TsundereBrain()  # connect to Gemini and start a chat session
        self.voice = VoiceEngine()  # set up text-to-speech
        self.avatars = list_avatars()  # scan the avatars folder
        self.avatar_photo = None  # will hold the current profile picture (must be kept alive or Tk drops it)
        self.voice_on = tk.BooleanVar(value=True)  # True/False variable bound to the "Voice" checkbox

        self._build_header()  # create the top bar (picture, name, dropdowns)
        self._build_input()  # create the bottom message box (packed before chat so it stays at the bottom)
        self._build_chat()  # create the scrolling message area in the middle

        if self.avatars:  # if at least one avatar image exists
            first_name = next(iter(self.avatars))  # pick the first one
            self.avatar_box.set(first_name)  # show its name in the dropdown
            self.set_avatar(self.avatars[first_name])  # display it in the header

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # run on_close when the window's X is clicked
        greeting_en = "Hmph! Y-you're finally here, baka! ...Not that I was waiting or anything!"  # her English opening line
        greeting_jp = "ふん！やっと来たの、バカ！べ、別に待ってたわけじゃないんだからね！"  # her Japanese opening line
        self.add_message("bot", f"{greeting_en}\n{greeting_jp}")  # show both lines in the chat
        self.speak(greeting_jp)  # say the Japanese line out loud

    def _build_header(self):  # creates the top part of the window
        header = tk.Frame(self.root, bg=HEADER_BG)  # container frame for the header
        header.pack(side="top", fill="x")  # stick it to the top and stretch across the width

        top_row = tk.Frame(header, bg=HEADER_BG)  # row holding the picture and the name
        top_row.pack(fill="x", padx=12, pady=(10, 4))  # add some padding around it

        self.avatar_label = tk.Label(top_row, bg=HEADER_BG)  # label that will display the round profile picture
        self.avatar_label.pack(side="left")  # put it on the left

        info = tk.Frame(top_row, bg=HEADER_BG)  # container for the name and status text
        info.pack(side="left", padx=10)  # place it to the right of the picture

        tk.Label(info, text=config.CHARACTER_NAME, bg=HEADER_BG, fg="white", font=("Segoe UI", 14, "bold")).pack(anchor="w")  # her name
        self.status_label = tk.Label(info, text="● online", bg=HEADER_BG, fg="#7CFC98", font=("Segoe UI", 9))  # status line
        self.status_label.pack(anchor="w")  # left-align the status under the name

        settings = tk.Frame(header, bg=HEADER_BG)  # row holding the dropdowns and buttons
        settings.pack(fill="x", padx=12, pady=(0, 10))  # add padding around it

        tk.Label(settings, text="Voice:", bg=HEADER_BG, fg="white", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")  # voice label
        self.voice_box = ttk.Combobox(settings, values=list(VOICE_PRESETS), state="readonly", width=24)  # dropdown of voice presets
        self.voice_box.current(0)  # select the first voice by default
        self.voice_box.grid(row=0, column=1, padx=6, pady=2, sticky="w")  # place it next to its label
        self.voice_box.bind("<<ComboboxSelected>>", self.on_voice_selected)  # call our handler when a voice is picked
        tk.Checkbutton(  # checkbox to turn speech on/off
            settings, text="Speak", variable=self.voice_on, command=self.on_voice_toggle,  # bound to voice_on, calls handler on click
            bg=HEADER_BG, fg="white", selectcolor=HEADER_BG, activebackground=HEADER_BG, activeforeground="white",  # dark-theme colours
        ).grid(row=0, column=2, padx=4)  # place it at the end of the row

        tk.Label(settings, text="Picture:", bg=HEADER_BG, fg="white", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")  # picture label
        self.avatar_box = ttk.Combobox(settings, values=list(self.avatars), state="readonly", width=24)  # dropdown of avatar names
        self.avatar_box.grid(row=1, column=1, padx=6, pady=2, sticky="w")  # place it under the voice dropdown
        self.avatar_box.bind("<<ComboboxSelected>>", self.on_avatar_selected)  # call our handler when a picture is picked
        ttk.Button(settings, text="Upload…", width=8, command=self.on_upload_avatar).grid(row=1, column=2, padx=4)  # custom image button

    def _build_chat(self):  # creates the scrolling message area
        area = tk.Frame(self.root, bg=CHAT_BG)  # container for the text box and its scrollbar
        area.pack(side="top", fill="both", expand=True)  # fill all the leftover space in the middle

        scrollbar = ttk.Scrollbar(area)  # vertical scrollbar
        scrollbar.pack(side="right", fill="y")  # attach it to the right edge

        self.chat = tk.Text(  # the text widget that displays every message
            area, wrap="word", state="disabled", bg=CHAT_BG, relief="flat",  # word-wrap, read-only, no border
            font=("Segoe UI", 11), yscrollcommand=scrollbar.set, padx=8, pady=8, cursor="arrow",  # font, scrollbar link, padding
        )  # end of Text(...)
        self.chat.pack(side="left", fill="both", expand=True)  # fill the area
        scrollbar.config(command=self.chat.yview)  # let the scrollbar control the text widget

        self.chat.tag_configure("bot", background=BOT_BUBBLE, lmargin1=10, lmargin2=10, rmargin=90, spacing1=4, spacing3=4)  # her bubble style (left)
        self.chat.tag_configure("user", background=USER_BUBBLE, justify="right", lmargin1=90, lmargin2=90, rmargin=10, spacing1=4, spacing3=4)  # your bubble style (right)
        self.chat.tag_configure("bot_name", foreground="#8a5a78", font=("Segoe UI", 8, "bold"), lmargin1=12, rmargin=90)  # small name above her bubble
        self.chat.tag_configure("user_name", foreground="#4d6f8f", font=("Segoe UI", 8, "bold"), justify="right", rmargin=12, lmargin1=90)  # small name above yours

    def _build_input(self):  # creates the bottom message bar
        bar = tk.Frame(self.root, bg=HEADER_BG)  # container for the entry box and send button
        bar.pack(side="bottom", fill="x")  # stick it to the bottom

        self.entry = tk.Entry(bar, font=("Segoe UI", 12), bg=INPUT_BG, relief="flat")  # the box where you type
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=10, ipady=6)  # stretch it and pad it
        self.entry.bind("<Return>", lambda event: self.on_send())  # pressing Enter sends the message
        self.entry.focus_set()  # put the cursor in the box immediately

        self.send_button = tk.Button(  # the send button
            bar, text="Send", command=self.on_send, bg="#ff7aa8", fg="white",  # click = send, pink colour
            activebackground="#ff5c94", relief="flat", font=("Segoe UI", 10, "bold"), padx=14,  # hover colour, flat style, font
        )  # end of Button(...)
        self.send_button.pack(side="right", padx=(0, 10), pady=10, ipady=4)  # attach it to the right

    def add_message(self, sender, text):  # appends one chat bubble to the message area
        """sender is 'bot' or 'user'."""  # description
        name = config.CHARACTER_NAME if sender == "bot" else "You"  # label shown above the bubble
        self.chat.config(state="normal")  # unlock the text box so we can insert
        self.chat.insert("end", f"{name}\n", f"{sender}_name")  # insert the small name label
        self.chat.insert("end", f" {text} \n", sender)  # insert the message with the bubble style
        self.chat.insert("end", "\n")  # blank line for spacing between messages
        self.chat.config(state="disabled")  # lock it again so you can't type in the history
        self.chat.see("end")  # scroll to the newest message

    def set_avatar(self, path):  # changes the profile picture in the header
        try:  # image files can be broken, so guard it
            self.avatar_photo = make_round_photo(path, AVATAR_SIZE)  # build the round picture (kept on self so it isn't garbage-collected)
            self.avatar_label.config(image=self.avatar_photo)  # show it in the header label
        except Exception as error:  # bad or unreadable image
            messagebox.showerror("Picture error", f"Couldn't load that image:\n{error}")  # tell the user

    def on_avatar_selected(self, event):  # runs when you pick a picture from the dropdown
        name = self.avatar_box.get()  # the chosen display name
        self.set_avatar(self.avatars[name])  # load and show the matching file

    def on_upload_avatar(self):  # runs when you click the "Upload…" button
        path = filedialog.askopenfilename(  # open the operating system's file picker
            title="Choose a profile picture",  # dialog title
            filetypes=[("Images", "*.png *.jpg *.jpeg")],  # only show png/jpg files
        )  # returns "" if cancelled
        if path:  # if a file was chosen
            self.set_avatar(path)  # display it

    def speak(self, text):  # speaks text using the currently selected voice (if Speak is ticked)
        if self.voice_on.get():  # only if the checkbox is on
            self.voice.speak(text, self.voice_box.get())  # send text + chosen preset to the voice engine

    def on_voice_selected(self, event):  # runs when you pick a different voice
        self.voice.stop()  # cut off whatever is currently playing
        self.speak(SAMPLE_LINE)  # play a sample line so you can hear the new voice

    def on_voice_toggle(self):  # runs when you click the "Speak" checkbox
        if not self.voice_on.get():  # if it was just switched off
            self.voice.stop()  # silence any audio right away

    def on_send(self):  # runs when you press Enter or click Send
        text = self.entry.get().strip()  # read what you typed and trim spaces
        if not text:  # ignore empty messages
            return  # do nothing
        self.entry.delete(0, "end")  # clear the message box
        self.add_message("user", text)  # show your message in the chat
        self.send_button.config(state="disabled")  # disable Send while waiting for her answer
        self.status_label.config(text="typing…", fg="#ffd166")  # header shows she's typing
        threading.Thread(target=self._get_reply, args=(text,), daemon=True).start()  # ask the AI in the background

    def _get_reply(self, text):  # runs in a background thread
        reply = self.brain.reply(text)  # blocks until Gemini answers (safe here, not on the UI thread)
        self.root.after(0, self._show_reply, reply)  # hand the result back to the UI thread

    def _show_reply(self, reply):  # runs on the UI thread once the answer arrives
        self.status_label.config(text="● online", fg="#7CFC98")  # she's no longer typing
        english, japanese = split_reply(reply)  # separate the English and Japanese lines
        shown = f"{english}\n{japanese}" if japanese else english  # show both if Japanese exists
        self.add_message("bot", shown)  # show her answer in the chat
        if japanese:  # only speak when there is Japanese text (error messages stay silent)
            self.speak(japanese)  # say the Japanese line out loud
        self.send_button.config(state="normal")  # re-enable the Send button
        self.entry.focus_set()  # put the cursor back in the message box

    def on_close(self):  # runs when you close the window
        self.voice.stop()  # stop any audio
        self.root.destroy()  # close the window and end the program


def main():  # program start
    if not config.GEMINI_API_KEY:  # if no API key was found in .env
        temp_root = tk.Tk()  # need a hidden root window to show a popup
        temp_root.withdraw()  # hide that window
        messagebox.showerror(  # show an error popup
            "Missing API key",  # popup title
            "No GEMINI_API_KEY found.\nCopy .env.example to .env and paste your key inside.",  # popup message
        )  # end of showerror
        return  # quit
    root = tk.Tk()  # create the main window
    ChatApp(root)  # build the chat UI inside it
    root.mainloop()  # start the GUI event loop (keeps the window open)


if __name__ == "__main__":  # only true when you run "python main.py" directly
    main()  # start the app
