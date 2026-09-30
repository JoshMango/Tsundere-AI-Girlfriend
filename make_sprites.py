"""Draws original placeholder expression sprites (one PNG per emotion) into sprites/<character>/ - replace them with your own art anytime."""  # explains what this file is for

import os  # builds file paths and creates folders

from PIL import Image, ImageDraw  # Pillow: create images and draw shapes on them

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # the folder this file lives in
OUT_DIR = os.path.join(BASE_DIR, "sprites")  # where the sprite folders are saved
W, H = 512, 800  # drawing canvas size (drawn big, then shrunk for smooth edges)
FINAL = (400, 625)  # final sprite size in pixels
SKIN = "#ffe3d3"  # skin colour
UNIFORM = "#2b3a67"  # school-uniform colour
SLEEVE_SHADE = "#24325a"  # slightly darker uniform colour for arms
BLUSH = "#ff9fb3"  # cheek blush colour
INK = "#3a2a3a"  # dark colour for lashes, pupils and mouth
MOUTH_RED = "#c2435b"  # inside colour for open mouths

EMOTIONS = ["neutral", "angry", "blush", "happy", "sad", "pout", "surprised", "smug"]  # one PNG is made per emotion

CHARACTERS = {  # folder name -> look of that character
    "hikari_pink": {"hair": "#ff8fb8", "dark": "#e0679a", "eyes": "#3fbf8f", "style": "twintails"},  # pink twintails
    "aya_red": {"hair": "#e8593f", "dark": "#c23f2b", "eyes": "#f2a623", "style": "ponytail"},  # red ponytail
    "yuki_silver": {"hair": "#e4e6f2", "dark": "#b7bdd6", "eyes": "#5aa8ff", "style": "long"},  # silver long hair
}  # end of characters

# Eye shapes: (top y, bottom y, half width, pupil x shift, pupil size multiplier, eyelid y or None)
EYES = {  # how the eyes look for each emotion
    "neutral": (262, 332, 30, 0, 1.0, None),  # normal round eyes
    "angry": (280, 332, 30, 0, 1.0, None),  # narrowed, glaring
    "blush": (262, 332, 30, 12, 0.9, None),  # looking away shyly
    "happy": None,  # closed happy arcs are drawn separately
    "sad": (262, 334, 31, 0, 1.1, None),  # big watery eyes
    "pout": (270, 332, 30, 12, 1.0, None),  # sulky side glance
    "surprised": (246, 344, 35, 0, 0.6, None),  # wide eyes with tiny pupils
    "smug": (262, 332, 30, 0, 1.0, 298),  # half-lidded eyes
}  # end of EYES

# Eyebrows: (left x0, y0, x1, y1), (right x0, y0, x1, y1)
BROWS = {  # eyebrow lines for each emotion
    "neutral": ((172, 238, 232, 242), (340, 238, 280, 242)),  # flat
    "angry": ((166, 220, 232, 256), (346, 220, 280, 256)),  # steep angry slant
    "blush": ((172, 242, 232, 232), (340, 242, 280, 232)),  # slightly worried
    "happy": ((172, 234, 232, 230), (340, 234, 280, 230)),  # relaxed high
    "sad": ((170, 248, 232, 228), (342, 248, 280, 228)),  # inner ends raised
    "pout": ((168, 228, 232, 250), (344, 228, 280, 250)),  # irritated
    "surprised": ((174, 212, 232, 208), (338, 212, 280, 208)),  # high arched
    "smug": ((170, 242, 232, 234), (342, 228, 280, 246)),  # one brow raised
}  # end of BROWS

CROSSED_ARMS = {"neutral", "angry", "pout", "smug"}  # emotions that use the arms-crossed pose


def draw_back_hair(d, cfg):  # draws the hair behind the head
    dark, style = cfg["dark"], cfg["style"]  # shortcuts for hair colour and style
    if style == "twintails":  # two pigtails
        d.ellipse((20, 190, 150, 500), fill=dark)  # left pigtail
        d.ellipse((362, 190, 492, 500), fill=dark)  # right pigtail
        d.ellipse((115, 85, 397, 410), fill=dark)  # back of the head
    elif style == "ponytail":  # ponytail on the right
        d.ellipse((350, 130, 490, 470), fill=dark)  # the ponytail
        d.ellipse((115, 85, 397, 410), fill=dark)  # back of the head
    else:  # long straight hair
        d.ellipse((95, 80, 417, 560), fill=dark)  # big oval behind the head and shoulders


def draw_body(d, emotion):  # draws neck, torso, collar and arms
    d.rectangle((226, 360, 286, 450), fill=SKIN)  # neck
    d.ellipse((90, 430, 422, 720), fill=UNIFORM)  # shoulders
    d.rectangle((120, 560, 392, H), fill=UNIFORM)  # torso down to the bottom edge
    d.polygon([(200, 435), (256, 505), (312, 435), (290, 425), (256, 462), (222, 425)], fill="white")  # white sailor collar
    d.polygon([(256, 480), (232, 520), (280, 520)], fill="#d9435b")  # red ribbon
    if emotion in CROSSED_ARMS:  # arms crossed pose
        d.rounded_rectangle((96, 540, 416, 615), radius=36, fill=SLEEVE_SHADE)  # folded arms band
        d.ellipse((372, 548, 428, 608), fill=SKIN)  # right hand
        d.ellipse((84, 548, 140, 608), fill=SKIN)  # left hand
    else:  # hands together in front of the chest
        d.rounded_rectangle((84, 470, 184, 650), radius=44, fill=UNIFORM, outline=SLEEVE_SHADE, width=4)  # left arm
        d.rounded_rectangle((328, 470, 428, 650), radius=44, fill=UNIFORM, outline=SLEEVE_SHADE, width=4)  # right arm
        d.ellipse((196, 600, 252, 660), fill=SKIN)  # left hand
        d.ellipse((260, 600, 316, 660), fill=SKIN)  # right hand


def draw_head(d, cfg):  # draws the face, side locks and bangs (no expression yet)
    hair = cfg["hair"]  # front hair colour
    d.ellipse((140, 130, 372, 395), fill=SKIN)  # face
    d.polygon([(138, 210), (178, 210), (170, 415), (140, 445)], fill=hair)  # left side lock
    d.polygon([(374, 210), (334, 210), (342, 415), (372, 445)], fill=hair)  # right side lock
    d.ellipse((128, 82, 384, 220), fill=hair)  # top of the head
    d.polygon([(128, 200), (135, 150), (256, 90), (377, 150), (384, 200), (372, 245), (330, 205), (300, 238), (256, 198), (212, 238), (182, 205), (140, 245)], fill=hair)  # bangs
    d.line((256, 92, 280, 40), fill=hair, width=10)  # ahoge (hair antenna)


def draw_eye(d, ex, shape, iris):  # draws one open eye centred at x = ex
    top, bottom, half, shift, pupil_scale, lid = shape  # unpack the shape values
    d.ellipse((ex - half, top, ex + half, bottom), fill="white")  # white of the eye
    d.ellipse((ex - 23 + shift, top + 4, ex + 23 + shift, bottom), fill=iris)  # coloured iris
    mid = (top + bottom) // 2 + 6  # vertical centre of the pupil
    pw, ph = int(11 * pupil_scale), int(17 * pupil_scale)  # pupil half-width and half-height
    d.ellipse((ex + shift - pw, mid - ph, ex + shift + pw, mid + ph), fill=INK)  # pupil
    d.ellipse((ex + shift - 15, top + 10, ex + shift - 3, top + 24), fill="white")  # big sparkle
    d.ellipse((ex + shift + 5, bottom - 26, ex + shift + 13, bottom - 18), fill="white")  # small sparkle
    if lid:  # half-lidded (smug) eyes
        d.rectangle((ex - half - 3, top - 6, ex + half + 3, lid), fill=SKIN)  # skin-coloured eyelid
        d.line((ex - half - 2, lid, ex + half + 2, lid), fill=INK, width=8)  # lid line
    else:  # normal eyes
        d.line((ex - half - 3, top, ex + half + 3, top), fill=INK, width=7)  # upper lash line


def draw_face(d, cfg, emotion):  # draws eyes, brows, blush, mouth and extras for one emotion
    for ex in (206, 306):  # left and right eye
        if emotion == "happy":  # happy closed eyes ^ ^
            d.arc((ex - 30, 268, ex + 30, 326), start=200, end=340, fill=INK, width=9)  # upward arc
        else:  # every other emotion uses open eyes
            draw_eye(d, ex, EYES[emotion], cfg["eyes"])  # open eye with the emotion's shape
    (lx0, ly0, lx1, ly1), (rx0, ry0, rx1, ry1) = BROWS[emotion]  # eyebrow coordinates
    d.line((lx0, ly0, lx1, ly1), fill=cfg["dark"], width=8)  # left eyebrow
    d.line((rx0, ry0, rx1, ry1), fill=cfg["dark"], width=8)  # right eyebrow

    blush_size = 1.5 if emotion in ("blush", "pout") else 1.0  # bigger blush when flustered or sulking
    for cx in (181, 331):  # left and right cheek
        w, h = int(21 * blush_size), int(12 * blush_size)  # blush half-size
        d.ellipse((cx - w, 350 - h, cx + w, 350 + h), fill=BLUSH)  # cheek blush
    if emotion == "blush":  # extra blush hatch lines
        for cx in (181, 331):  # each cheek
            for k in range(3):  # three short lines
                d.line((cx - 14 + k * 12, 338, cx - 6 + k * 12, 358), fill="#ff6f91", width=3)  # hatch line

    if emotion == "neutral":  # small flat mouth
        d.line((240, 372, 272, 372), fill=INK, width=4)  # straight line
    elif emotion == "angry":  # deep frown
        d.arc((232, 366, 280, 400), start=200, end=340, fill=INK, width=6)  # frown arc
    elif emotion == "blush":  # wobbly embarrassed mouth
        d.arc((234, 364, 256, 380), start=0, end=180, fill=INK, width=4)  # left wave
        d.arc((256, 364, 278, 380), start=0, end=180, fill=INK, width=4)  # right wave
    elif emotion == "happy":  # open smile
        d.pieslice((226, 352, 286, 402), start=0, end=180, fill=MOUTH_RED, outline=INK, width=4)  # open mouth
    elif emotion == "sad":  # small frown
        d.arc((238, 374, 274, 396), start=200, end=340, fill=INK, width=4)  # frown arc
    elif emotion == "pout":  # tiny puffed mouth
        d.ellipse((246, 366, 270, 380), outline=INK, width=4)  # small "o" pout
    elif emotion == "surprised":  # open "o" mouth
        d.ellipse((240, 356, 272, 394), fill=MOUTH_RED, outline=INK, width=4)  # round open mouth
    elif emotion == "smug":  # smirk
        d.arc((236, 352, 292, 386), start=20, end=160, fill=INK, width=4)  # smirk curve
        d.line((288, 368, 296, 360), fill=INK, width=4)  # smirk corner

    if emotion == "angry":  # anger vein mark
        for (x0, y0, x1, y1) in ((334, 104, 346, 116), (350, 104, 338, 116), (330, 92, 346, 96), (352, 92, 340, 98)):  # four short strokes
            d.line((x0, y0, x1, y1), fill="#e53935", width=5)  # red stroke
    if emotion == "sad":  # tear
        d.ellipse((160, 340, 176, 372), fill="#9fd8ff")  # tear drop
    if emotion == "surprised":  # sweat drop
        d.polygon([(392, 200), (380, 228), (404, 228)], fill="#9fd8ff")  # drop tip
        d.ellipse((380, 220, 404, 244), fill="#9fd8ff")  # drop body
    if emotion in ("smug", "happy"):  # sparkle
        d.polygon([(120, 130), (127, 148), (145, 155), (127, 162), (120, 180), (113, 162), (95, 155), (113, 148)], fill="#fff2a8")  # four-point star

    d.polygon([(150, 120), (190, 100), (200, 140)], fill="#ff5c8a")  # left half of the hair bow
    d.polygon([(250, 108), (210, 92), (200, 140)], fill="#ff5c8a")  # right half of the hair bow
    d.ellipse((190, 108, 212, 132), fill="#d9436f")  # bow knot


def draw_sprite(cfg, emotion):  # draws one full sprite and returns the image
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))  # fully transparent canvas
    d = ImageDraw.Draw(image)  # drawing tool
    draw_back_hair(d, cfg)  # hair behind the head
    draw_body(d, emotion)  # neck, torso, arms
    draw_head(d, cfg)  # face, side locks, bangs
    draw_face(d, cfg, emotion)  # expression
    return image.resize(FINAL, Image.LANCZOS)  # shrink for smooth anti-aliased edges


def main():  # generates every sprite
    for folder, cfg in CHARACTERS.items():  # each character
        os.makedirs(os.path.join(OUT_DIR, folder), exist_ok=True)  # make sprites/<character>/
        for emotion in EMOTIONS:  # each expression
            path = os.path.join(OUT_DIR, folder, f"{emotion}.png")  # sprites/<character>/<emotion>.png
            draw_sprite(cfg, emotion).save(path)  # draw and save
        print("saved", folder)  # tell the user


if __name__ == "__main__":  # only true when run directly
    main()  # generate the sprites
