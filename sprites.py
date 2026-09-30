"""A visual-novel style side panel that shows the girlfriend's sprite and swaps expressions with a quick crossfade."""  # explains what this file is for

import os  # builds file paths and lists folders
import tkinter as tk  # Python's built-in GUI toolkit
from tkinter import ttk  # themed widgets (the dropdown)

from PIL import Image, ImageOps, ImageTk  # Pillow: load, scale, blend and convert images for Tk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # the folder this file lives in
SPRITE_DIR = os.path.join(BASE_DIR, "sprites")  # folder that holds one sub-folder per sprite set
EMOTIONS = ("neutral", "angry", "blush", "happy", "sad", "pout", "surprised", "smug")  # the emotion names the AI can pick
IMAGE_TYPES = (".png", ".webp", ".jpg", ".jpeg")  # file types we accept (png/webp keep transparency)
STAGE_WIDTH = 340  # width of the side panel in pixels
PANEL_BG = "#2f2a48"  # colour of the small top bar (matches the chat header)
SKY_TOP = (255, 214, 231)  # backdrop gradient colour at the top (pink)
SKY_BOTTOM = (191, 224, 255)  # backdrop gradient colour at the bottom (light blue)
FADE_STEPS = 5  # how many frames the crossfade uses
FADE_DELAY_MS = 35  # milliseconds between crossfade frames


def list_sprite_sets():  # finds every sprite folder that contains at least one image
    """Return {pretty name: folder path} for each sub-folder of sprites/."""  # description
    found = {}  # will hold the results
    if not os.path.isdir(SPRITE_DIR):  # if the sprites folder doesn't exist
        return found  # return an empty dict
    for folder in sorted(os.listdir(SPRITE_DIR)):  # loop through sub-folders alphabetically
        path = os.path.join(SPRITE_DIR, folder)  # full path of this sub-folder
        if os.path.isdir(path) and any(name.lower().endswith(IMAGE_TYPES) for name in os.listdir(path)):  # has at least one image
            found[folder.replace("_", " ").title()] = path  # "hikari_pink" -> "Hikari Pink"
    return found  # hand back the dictionary


def find_sprite(folder, emotion):  # finds the image file for an emotion inside a sprite folder
    """Return the path of <emotion>.png/.webp/.jpg in the folder, or None."""  # description
    for extension in IMAGE_TYPES:  # try each accepted file type
        path = os.path.join(folder, emotion + extension)  # e.g. sprites/hikari_pink/angry.png
        if os.path.isfile(path):  # if that file exists
            return path  # use it
    return None  # no file for this emotion


class SpriteStage(tk.Frame):  # the side panel widget
    """Shows the current sprite over a soft gradient backdrop with a name plate, and crossfades between expressions."""  # class description

    def __init__(self, master, character_name):  # runs once when the panel is created
        super().__init__(master, width=STAGE_WIDTH, bg=PANEL_BG)  # create the frame with a fixed width
        self.pack_propagate(False)  # stop children from resizing the frame
        self.character_name = character_name  # the name shown on the name plate
        self.sets = list_sprite_sets()  # all sprite folders found
        self.folder = None  # the currently selected sprite folder
        self.emotion = "neutral"  # the currently shown emotion
        self.originals = {}  # cache of loaded PIL images (path -> image)
        self.backdrops = {}  # cache of gradient backgrounds (size -> image)
        self.photo = None  # the Tk image currently on the canvas (must be kept alive)
        self.last_frame = None  # the last fully composed frame (start of the next crossfade)
        self.fade_job = None  # id of the scheduled crossfade step, so it can be cancelled

        bar = tk.Frame(self, bg=PANEL_BG)  # small top bar holding the sprite-set dropdown
        bar.pack(side="top", fill="x")  # stretch across the top
        tk.Label(bar, text="Sprite:", bg=PANEL_BG, fg="white", font=("Segoe UI", 9)).pack(side="left", padx=(10, 4), pady=6)  # label
        self.set_box = ttk.Combobox(bar, values=list(self.sets), state="readonly", width=20)  # dropdown of sprite sets
        self.set_box.pack(side="left", pady=6)  # place it next to the label
        self.set_box.bind("<<ComboboxSelected>>", self.on_set_selected)  # react when a set is chosen

        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#d8e6ff")  # the drawing area for the sprite
        self.canvas.pack(side="top", fill="both", expand=True)  # fill the rest of the panel
        self.canvas.bind("<Configure>", lambda event: self.redraw())  # redraw whenever the panel is resized

        if self.sets:  # if at least one sprite set exists
            first = next(iter(self.sets))  # take the first one
            self.set_box.set(first)  # show it in the dropdown
            self.folder = self.sets[first]  # remember its folder

    def on_set_selected(self, event):  # runs when you pick a different sprite set
        self.folder = self.sets[self.set_box.get()]  # switch to the chosen folder
        self.redraw()  # show it immediately

    def _load(self, path):  # loads an image once and keeps it in memory
        if path not in self.originals:  # not loaded yet
            self.originals[path] = Image.open(path).convert("RGBA")  # open it and ensure it has transparency
        return self.originals[path]  # the cached image

    def _backdrop(self, width, height):  # builds (or reuses) the gradient background for a given size
        key = (width, height)  # cache key
        if key not in self.backdrops:  # not built yet
            gradient = Image.linear_gradient("L").resize((width, height))  # black-to-white vertical gradient
            self.backdrops[key] = ImageOps.colorize(gradient, black=SKY_TOP, white=SKY_BOTTOM).convert("RGBA")  # tint it with our two colours
        return self.backdrops[key].copy()  # a fresh copy we can paint on

    def _compose(self):  # builds one full frame: backdrop + sprite
        width = max(self.canvas.winfo_width(), 50)  # current canvas width (minimum 50)
        height = max(self.canvas.winfo_height(), 50)  # current canvas height (minimum 50)
        frame = self._backdrop(width, height)  # start with the gradient
        path = find_sprite(self.folder, self.emotion) or find_sprite(self.folder, "neutral") if self.folder else None  # emotion file, else neutral
        if path:  # if we found an image
            sprite = self._load(path)  # load it
            scale = min(width * 0.96 / sprite.width, height * 0.94 / sprite.height)  # scale that fits the panel
            new_size = (max(int(sprite.width * scale), 1), max(int(sprite.height * scale), 1))  # scaled size
            sprite = sprite.resize(new_size, Image.LANCZOS)  # shrink/grow smoothly
            x = (width - new_size[0]) // 2  # centre horizontally
            y = height - new_size[1]  # stand on the bottom edge
            frame.alpha_composite(sprite, (x, y))  # paste using the sprite's transparency
        return frame  # the finished frame

    def _show(self, frame):  # draws a composed frame on the canvas plus the name plate
        self.photo = ImageTk.PhotoImage(frame)  # convert to a Tk image (kept on self so it isn't garbage-collected)
        self.canvas.delete("all")  # clear the canvas
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")  # draw the frame
        if not (self.folder and find_sprite(self.folder, "neutral")):  # no sprites available
            self.canvas.create_text(frame.width // 2, frame.height // 2, text="Add images to\nsprites/<name>/neutral.png", fill="#4d4d6d", font=("Segoe UI", 11), justify="center")  # help text
        text_id = self.canvas.create_text(24, frame.height - 28, text=self.character_name, anchor="w", fill="white", font=("Segoe UI", 12, "bold"))  # name text
        x1, y1, x2, y2 = self.canvas.bbox(text_id)  # size of the name text
        plate = self.canvas.create_rectangle(x1 - 14, y1 - 6, x2 + 14, y2 + 6, fill="#ff7aa8", outline="white", width=2)  # pink name plate
        self.canvas.tag_lower(plate, text_id)  # put the plate behind the text

    def redraw(self):  # shows the current emotion without any fade (used on resize / set change)
        if self.fade_job:  # a crossfade is running
            self.after_cancel(self.fade_job)  # stop it
            self.fade_job = None  # forget it
        self.last_frame = self._compose()  # build the frame
        self._show(self.last_frame)  # display it

    def set_emotion(self, emotion):  # public method: switch to a new expression with a quick crossfade
        """emotion should be one of EMOTIONS; anything else becomes 'neutral'."""  # description
        emotion = (emotion or "neutral").strip().lower()  # clean the value
        self.emotion = emotion if emotion in EMOTIONS else "neutral"  # unknown names fall back to neutral
        new_frame = self._compose()  # the frame we're fading to
        old_frame = self.last_frame  # the frame we're fading from
        if self.fade_job:  # a previous crossfade is still running
            self.after_cancel(self.fade_job)  # stop it
            self.fade_job = None  # forget it
        self.last_frame = new_frame  # remember the new frame for next time
        if old_frame is None or old_frame.size != new_frame.size:  # nothing to fade from
            self._show(new_frame)  # just show it
            return  # done
        self._fade(old_frame, new_frame, 1)  # start the crossfade

    def _fade(self, old_frame, new_frame, step):  # one step of the crossfade
        self._show(Image.blend(old_frame, new_frame, step / FADE_STEPS))  # mix the two frames
        if step < FADE_STEPS:  # more steps to go
            self.fade_job = self.after(FADE_DELAY_MS, self._fade, old_frame, new_frame, step + 1)  # schedule the next step
        else:  # finished
            self.fade_job = None  # nothing scheduled any more
