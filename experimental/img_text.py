import cv2.cv2 as cv2
import matplotlib.pyplot as plt
from pathlib import Path


class RunLocationError(Exception):
    pass


if not Path.cwd().stem == "fish-mesh":
    raise RunLocationError(
        "This snippet expects you to run from "
        "the project root directory: 'fish-mesh'"
    )

img = cv2.imread('IMG_20210821_130933.jpg')

plt.imshow(cv2.cvtColor(
    img,
    cv2.COLOR_RGB2BGR))
plt.show()


# Font Size
# * Drawn font size is based on pixels of monitor
# * the font in drawn on top of a resized image
# * When drawing on the original image (not resized), the
#   font scale and thickness will need to be scaled to represent
#   the size of the text relative to the image it was drawn upon.
#   To do this I will likely need the
#   * screen size(resolution)
#   * resized_image size
#   * font size (which is likely relative to the monitor size/resolution)

bottomLeftCorner=(200, 3000)
font = cv2.FONT_HERSHEY_DUPLEX
# font = cv2.FONT_HERSHEY_SIMPLEX
fontScale = 20
fontColor = (255,255,255)
thickness = 20
lineType = cv2.LINE_AA  # cv2.LINE_AA ("smeared") | cv2.LINE_4 (pixelated) | cv2.LINE_8 (pixelated taxi)
text_img = cv2.putText(
    img,
    'Hello World!',
    bottomLeftCorner,
    font, 
    fontScale,
    fontColor,
    thickness,
    lineType
)

plt.imshow(cv2.cvtColor(
    text_img,
    cv2.COLOR_RGB2BGR))
plt.show()


# draw ruler code:
"""
drawn_label = self.right_view.canvas.create_text(
    x, y, text=f"{i + 1}: {value:.1f} cm", fill=color, anchor=tk.NW, font=(None, self.settings.font_size)
)
"""
cv2.getTextSize(text="a", fontFace=font, fontScale=1, thickness=1)
cv2.getTextSize(text="A", fontFace=font, fontScale=1, thickness=1)
cv2.getTextSize(text="T", fontFace=font, fontScale=1, thickness=1)
cv2.getTextSize(text=" ", fontFace=font, fontScale=1, thickness=1)
cv2.getTextSize(text="R", fontFace=font, fontScale=1, thickness=1)


