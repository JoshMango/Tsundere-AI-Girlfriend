"""Draws a set of original anime-style girl profile pictures into the avatars/ folder (run once, or add your own images)."""  # explains what this file is for

import os  # builds file paths and creates folders

from PIL import Image, ImageDraw  # Pillow: create images and draw shapes on them

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # the folder this file lives in
OUT_DIR = os.path.join(BASE_DIR, "avatars")  # where the finished pictures are saved
SIZE = 512  # we draw big, then shrink for smooth edges
FINAL = 256  # final picture size in pixels
SKIN = "#ffe3d3"  # skin colour shared by all girls
UNIFORM = "#2b3a67"  # school-uniform jacket colour
BLUSH = "#ff9fb3"  # cheek blush colour
INK = "#3a2a3a"  # dark colour for lashes, pupils and mouth

AVATARS = [  # one dictionary per profile picture
    {"file": "hikari_pink.png", "hair": "#ff8fb8", "dark": "#e0679a", "eyes": "#3fbf8f", "style": "twintails", "bg": "#ffd9e8"},  # pink twintails
    {"file": "yuki_silver.png", "hair": "#e4e6f2", "dark": "#b7bdd6", "eyes": "#5aa8ff", "style": "long", "bg": "#dfe9ff"},  # silver long hair
    {"file": "aya_red.png", "hair": "#e8593f", "dark": "#c23f2b", "eyes": "#f2a623", "style": "ponytail", "bg": "#ffe1d1"},  # red ponytail
    {"file": "mio_blue.png", "hair": "#5b8def", "dark": "#4370cc", "eyes": "#9a6bff", "style": "bob", "bg": "#d8ecff"},  # blue bob cut
    {"file": "nao_blonde.png", "hair": "#f7d56b", "dark": "#dfb247", "eyes": "#e0405a", "style": "twintails", "bg": "#fff3c9"},  # blonde twintails
    {"file": "rei_midnight.png", "hair": "#3a3358", "dark": "#28233f", "eyes": "#c86bff", "style": "long", "bg": "#e6dcf7"},  # dark purple long hair
]  # end of the avatar list


def draw_avatar(cfg):  # draws one avatar from its settings and returns the image
    image = Image.new("RGB", (SIZE, SIZE), cfg["bg"])  # blank square with the background colour
    d = ImageDraw.Draw(image)  # drawing tool for that image
    hair, dark, style = cfg["hair"], cfg["dark"], cfg["style"]  # shortcuts for the hair colours and style

    if style == "twintails":  # two pigtails hanging on both sides
        d.ellipse((20, 190, 150, 490), fill=dark)  # left pigtail
        d.ellipse((362, 190, 492, 490), fill=dark)  # right pigtail
        d.ellipse((115, 85, 397, 410), fill=dark)  # back of the head
    elif style == "long":  # long straight hair
        d.ellipse((95, 80, 417, 530), fill=dark)  # big oval behind the head and shoulders
    elif style == "ponytail":  # ponytail on the right side
        d.ellipse((350, 130, 490, 440), fill=dark)  # the ponytail
        d.ellipse((115, 85, 397, 410), fill=dark)  # back of the head
    else:  # "bob" = short chin-length hair
        d.ellipse((98, 85, 414, 430), fill=dark)  # rounded bob shape

    d.rectangle((226, 360, 286, 450), fill=SKIN)  # neck
    d.ellipse((90, 430, 422, 720), fill=UNIFORM)  # shoulders / uniform
    d.polygon([(200, 435), (256, 505), (312, 435), (290, 425), (256, 462), (222, 425)], fill="white")  # white sailor collar
    d.polygon([(256, 480), (232, 520), (280, 520)], fill="#d9435b")  # red ribbon
    d.ellipse((140, 130, 372, 395), fill=SKIN)  # face

    d.polygon([(138, 210), (178, 210), (170, 415), (140, 445)], fill=hair)  # left side lock of hair
    d.polygon([(374, 210), (334, 210), (342, 415), (372, 445)], fill=hair)  # right side lock of hair
    d.ellipse((128, 82, 384, 220), fill=hair)  # top of the head
    d.polygon([(128, 200), (135, 150), (256, 90), (377, 150), (384, 200), (372, 245), (330, 205), (300, 238), (256, 198), (212, 238), (182, 205), (140, 245)], fill=hair)  # bangs
    d.line((256, 92, 280, 40), fill=hair, width=10)  # ahoge (the little hair antenna)

    for eye_x in (206, 306):  # draw the left eye then the right eye
        d.ellipse((eye_x - 30, 262, eye_x + 30, 332), fill="white")  # white of the eye
        d.ellipse((eye_x - 23, 266, eye_x + 23, 332), fill=cfg["eyes"])  # coloured iris
        d.ellipse((eye_x - 11, 282, eye_x + 11, 316), fill=INK)  # pupil
        d.ellipse((eye_x - 15, 272, eye_x - 3, 286), fill="white")  # big sparkle highlight
        d.ellipse((eye_x + 5, 306, eye_x + 13, 314), fill="white")  # small sparkle highlight
        d.line((eye_x - 33, 262, eye_x + 33, 262), fill=INK, width=7)  # upper lash line

    d.line((170, 232, 232, 252), fill=dark, width=8)  # left brow, angled down = tsundere glare
    d.line((342, 232, 280, 252), fill=dark, width=8)  # right brow, angled down = tsundere glare

    d.ellipse((160, 338, 202, 362), fill=BLUSH)  # left cheek blush
    d.ellipse((310, 338, 352, 362), fill=BLUSH)  # right cheek blush
    d.arc((236, 358, 276, 384), start=200, end=340, fill=INK, width=4)  # small pouting mouth
    d.polygon([(150, 120), (190, 100), (200, 140)], fill="#ff5c8a")  # left half of a hair bow
    d.polygon([(250, 108), (210, 92), (200, 140)], fill="#ff5c8a")  # right half of the bow (meets at the knot)
    d.ellipse((190, 108, 212, 132), fill="#d9436f")  # bow knot

    return image.resize((FINAL, FINAL), Image.LANCZOS)  # shrink for smooth anti-aliased edges


def main():  # generates every avatar
    os.makedirs(OUT_DIR, exist_ok=True)  # create the avatars folder if needed
    for cfg in AVATARS:  # loop over each avatar definition
        path = os.path.join(OUT_DIR, cfg["file"])  # where to save this one
        draw_avatar(cfg).save(path)  # draw and save it
        print("saved", path)  # tell the user


if __name__ == "__main__":  # only true when run directly
    main()  # generate the pictures
