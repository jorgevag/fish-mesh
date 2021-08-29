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