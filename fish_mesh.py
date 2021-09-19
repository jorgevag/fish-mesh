from typing import List, Optional
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import cv2.cv2 as cv2
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from functools import partial

import tkinter as tk
from tkinter import ttk

"""
* load image upon file selection, show red error message if image file
  not supported
* modularize components to have less mental overhead
* when warping image, show warped image as a new canvas on the side
  * will also need to have resize functionality
  * point drawing logic (maybe just draw a ruler/line between points)
* if bounding box is changed, update warped image on the release_callback
"""
import components as comp

@dataclass
class FileExplorer:
    button = None
    selected_file: Optional[tk.StringVar] = None
    selected_file_label: Optional[tk.Label] = None

@dataclass
class Data:
    loaded_img = None
    warped_img = None

@dataclass
class ImageView:
    img = None
    canvas = None  # canvas to draw on
    canvas_img = None

    # Padding to preserve aspect ratio (centered image)
    x_padding = None
    y_padding = None

    resized_img = None
    resized_width = None
    resized_height = None

@dataclass
class Point:
    x: float
    y: float

@dataclass
class BoundingBoxDrawer:
    img_viewer = None # contains canvas that points should be drawn on
    # and the canvas to add the drawing callbacks to
    corners = []
    drawn_corner_ids = []

# Where do I put cv2_image and loading??


class FishMesh:
    def __init__(self):
        # Init tkinter window:
        self.window = tk.Tk()
        self.window.title('File Explorer')
        #self.window.geometry("500x500")  # Set window size
        self.window.config(background="white")
        self.window.geometry(f"{self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()}")

        file_explorer = FileExplorer()
        file_explorer.button = Button(
            self.window,
            bg="white",
            text="Browse Files",
            command=self.load_selected_file,
        )
        file_explorer.button.pack()
        file_explorer.selected_file = tk.StringVar()
        file_explorer.selected_file_label = Label(
            self.window,
            text="No file selected",
            bg="white",
        )
        file_explorer.selected_file_label.pack()
        self.file_explorer: FileExplorer = file_explorer

        self.img = None

        self.image_displays = tk.Frame(self.window)
        self.image_displays.pack(fill="both", expand=True)
        self.left_view = ImageView()
        self.left_view.canvas = Canvas(self.image_displays, width=0, height=0, bg="white")
        self.left_view.canvas.pack(side=LEFT, fill="both", expand=True)
        self.right_view = ImageView()
        self.right_view.canvas = Canvas(self.image_displays, width=0, height=0, bg="white")
        self.right_view.canvas.pack(side=RIGHT, fill="both", expand=True)
        self.window.bind('<Configure>', self.resize_callback)
        # # # # # #
        # # This one works (but doesn't include additional canvas):
        # self.left_view = ImageView()
        # self.left_view.canvas = Canvas(self.window, width=0, height=0, bg="white")
        # self.left_view.canvas.pack(fill="both", expand=True)
        # self.right_view = ImageView()
        # self.window.bind('<Configure>', self.resize_callback)
        # # # # # #
        # self.left_view = ImageView()
        # self.left_view.canvas = Canvas(self.window, width=0, height=0, bg="white")
        # self.left_view.canvas.pack(expand=True)
        # self.right_view = ImageView()
        # self.right_view.canvas = Canvas(self.window, width=0, height=0, bg="white")
        # self.right_view.canvas.pack(expand=True)
        # self.window.bind('<Configure>', self.resize_callback)

        # drag corner callbacks
        self.bounding_box = []
        self.drawn_bounding_box = None
        self.drawn_bounding_box_lines = None
        """
        mouse-button  click      hold&move    release
        left          <Button-1>, <B1-Motion>, <ButtonRelease-1>
        middle        <Button-2>, <B2-Motion>, <ButtonRelease-2>
        right         <Button-3>, <B3-Motion>, <ButtonRelease-3>
        """
        self.corner_selected = False
        self._drawn_dragged_point = None
        self.left_view.canvas.bind("<Button-1>", partial(self.click_callback, self.left_view))
        self.left_view.canvas.bind("<B1-Motion>", partial(self.drag_callback, self.left_view))
        self.left_view.canvas.bind("<ButtonRelease-1>", partial(self.release_callback, self.left_view))

        self.rotate_buttons_frame = tk.Frame(self.window)
        self.rotate_buttons_frame.pack(fill="x")
        self.rotate_anticlockwise_button = Button(
            self.rotate_buttons_frame,
            text="\u21BB",  # unicode char for anticlockwise circular arrow
            command=self.rotate_image_clockwise,
            bg="white",
        )
        self.rotate_anticlockwise_button.pack(side=LEFT, fill="x", expand=True)
        self.rotate_clockwise_button = Button(
            self.rotate_buttons_frame,
            text="\u21BA",  # unicode char for anticlockwise circular arrow
            command=self.rotate_image_anticlockwise,
            bg="white",
        )
        self.rotate_clockwise_button.pack(side=RIGHT, fill="x", expand=True)

        self.warped_image = None
        self.exit_button = Button(
            self.window,
            text="Quit",
            command=exit,
            bg="white",
        )
        #self.exit_button = ttk.Button(self.window, text="Quit")
        #self.exit_button['command'] = self.window.destroy
        self.exit_button.pack(fill="x")


    def load_selected_file(self):
        self.select_file()
        self.load_image()
        #
        self.init_bounding_box()
        self.warp_image()
        self.draw()


    def select_file(self):
        """opening file explorer window"""
        filename = filedialog.askopenfilename(
            #initialdir="/",
            initialdir=Path.cwd().__str__(),
            title="Select a File",
            filetypes=(
                ("all files", "*.*"),
                ("Text files", "*.txt*"),
            )
        )
        self.file_explorer.selected_file.set(filename)
        # Show selected file
        self.file_explorer.selected_file_label.configure(text="Selected File: " + filename)

    def load_image(self):
        img_array_BGR = cv2.imread(self.file_explorer.selected_file.get())

        # OpenCV uses BGR color, but PIL expects RGB, so we need to convert image's color to RGB order
        img_array_RGB = cv2.cvtColor(img_array_BGR, cv2.COLOR_BGR2RGB)

        # https://stackoverflow.com/questions/19838972/how-to-update-an-image-on-a-canvas/19842646
        self.img = img_array_RGB

    def resize_views(self):
        if self.left_view.img is not None:
            img, w, h = self.resize_image(self.left_view.img, self.left_view.canvas)
            self.left_view.resized_img = img
            self.left_view.resized_width = w
            self.left_view.resized_height = h

        if self.right_view.img is not None:
            img, w, h = self.resize_image(self.right_view.img, self.right_view.canvas)
            self.right_view.resized_img = img
            self.right_view.resized_width = w
            self.right_view.resized_height = h

    def resize_image(self, img, canvas: tk.Canvas, preserve_aspect_ratio=True):
        img_width = len(img[0])
        img_height = len(img)
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        if preserve_aspect_ratio:
            # Check how much to scale image width to be within canvas width:
            required_width_scaling = canvas_width / img_width
            # and also for the height:
            required_height_scaling = canvas_height / img_height

            # The one with the minimum required scaling is used:
            # * when smaller than canvas, image is resized based on which dimension is closest
            # * when larger than canvas, scale will be most negative for dimension that "overshoots" the most
            scaling = min(required_width_scaling, required_height_scaling)

            new_img_width = int(img_width * scaling)
            new_img_height = int(img_height * scaling)

            resized = cv2.resize(img, (new_img_width, new_img_height), interpolation=cv2.INTER_AREA)
            resized_width = new_img_width
            resized_height = new_img_height
        else:
            resized = cv2.resize(img, (canvas_width, canvas_height), interpolation=cv2.INTER_AREA)
            resized_width = canvas_width
            resized_height = canvas_height
        resized_img = ImageTk.PhotoImage(Image.fromarray(resized))
        return resized_img, resized_width, resized_height

    def draw_image(self, img_view):
        if img_view.img is None:
            return
        # Get x,y position to center image drawn on canvas using anchor to NW
        x = (img_view.canvas.winfo_width() - img_view.resized_width) // 2
        y = (img_view.canvas.winfo_height() - img_view.resized_height) // 2
        img_view.canvas_img = img_view.canvas.create_image(x, y, image=img_view.resized_img, anchor=tk.NW)  # TODO: should i delete the previous image on canbas? (not sure I'm using this variable at all)
        # The position is equal to the "padding" (on one side) required to preserve aspect ratio
        img_view.x_padding = x
        img_view.y_padding = y
        # self.canvas.configure(photo_img, height=photo_img.height(), width=photo_img.width())
        img_view.canvas.itemconfig(img_view.canvas_img, image=img_view.resized_img)
        img_view.canvas.image = img_view.resized_img
        img_view.canvas.configure(bg="black")

    def draw(self):
        if self.img is None:
            return
        self.left_view.img = self.img
        self.right_view.img = self.warped_image

        self.resize_views()

        self.draw_image(self.left_view)
        self.draw_bounding_box(self.left_view)

        if self.right_view.img is not None:
            self.draw_image(self.right_view)


    def resize_callback(self, event):
        self.draw()  # redraw everything to the new canvas display sizes

    def rotate_image_clockwise(self):
        self.img = cv2.rotate(self.img, cv2.ROTATE_90_CLOCKWISE)
        self.warp_image()
        self.draw()

    def rotate_image_anticlockwise(self):
        self.img = cv2.rotate(self.img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.warp_image()
        self.draw()

    def run(self):
        self.window.mainloop()

    def init_bounding_box(self):
        # w = self.canvas.winfo_width()
        # h = self.canvas.winfo_height()
        top_left = Point(0.20, 0.20)
        bottom_left = Point(0.20, 0.80)
        bottom_right = Point(0.80, 0.80)
        top_right = Point(0.80, 0.20)
        self.bounding_box: List[Point] = [top_left, bottom_left, bottom_right, top_right]

    def draw_bounding_box(self, img_view):
        if len(self.bounding_box) == 0:
            self.init_bounding_box()

        # TODO: simplify drawing lines and points (naming and structuring should also be improved)
        # Draw lines
        # To get the correct pair of points we need a certain order:
        if self.drawn_bounding_box_lines:
            for line in self.drawn_bounding_box_lines:
                img_view.canvas.delete(line)
        self.drawn_bounding_box_lines = []
        x0 = img_view.x_padding
        y0 = img_view.y_padding
        point_arr = np.stack([np.array([(p.x * img_view.resized_width) + x0, (p.y * img_view.resized_height) + y0 ]) for p in self.bounding_box])
        ps = np.reshape(point_arr, (4,2))
        #ps = [p[0] for p in _reorder_corner_points(point_arr, "drawing_bounding_box")]
        self.drawn_bounding_box_lines.append(img_view.canvas.create_line(ps[0,0], ps[0,1], ps[1,0], ps[1,1], fill="red"))
        self.drawn_bounding_box_lines.append(img_view.canvas.create_line(ps[1,0], ps[1,1], ps[2,0], ps[2,1], fill="red"))
        self.drawn_bounding_box_lines.append(img_view.canvas.create_line(ps[2,0], ps[2,1], ps[3,0], ps[3,1], fill="red"))
        self.drawn_bounding_box_lines.append(img_view.canvas.create_line(ps[3,0], ps[3,1], ps[0,0], ps[0,1], fill="red"))

        w = img_view.resized_width
        h = img_view.resized_height
        screen_width = self.window.winfo_screenwidth()
        point_size = int(0.005 * screen_width)
        # Delete the previously drawn points:
        if self.drawn_bounding_box:
            for drawn_corner in self.drawn_bounding_box:
                img_view.canvas.delete(drawn_corner)
        # Draw bounding box (and keep track of points):
        self.drawn_bounding_box = []
        for corner in self.bounding_box:
            if corner is not None:
                canvas_obj = img_view.canvas.create_oval(
                    # set point diagonal as 2% of monitor screen width
                    img_view.x_padding + int(w * corner.x) - point_size,
                    img_view.y_padding + int(h * corner.y) - point_size,
                    img_view.x_padding + int(w * corner.x) + point_size,
                    img_view.y_padding + int(h * corner.y) + point_size,
                    fill='red'
                )
                self.drawn_bounding_box.append(canvas_obj)


    def click_callback(self, img_view: ImageView, event):
        x = event.x
        y = event.y
        if self.drawn_bounding_box is not None:  # coreners must be drawn
            closest = img_view.canvas.find_closest(x, y, halo=10, start=self.drawn_bounding_box)
            selected_corner_tag = closest[0]
            if selected_corner_tag in self.drawn_bounding_box:
                self.corner_selected = True
                # Delete selected point (it will be redrawn on the release position)
                self.selected_corner_idx = self.drawn_bounding_box.index(selected_corner_tag)
                img_view.canvas.delete(selected_corner_tag)
                self.drawn_bounding_box.remove(selected_corner_tag)
                self.bounding_box[self.selected_corner_idx] = None
                # Remove lines (this is easier than to draw lines for all points in the drag_callback)
                if self.drawn_bounding_box_lines:
                    for line in self.drawn_bounding_box_lines:
                        img_view.canvas.delete(line)

    def drag_callback(self, img_view: ImageView, event):
        x = event.x
        y = event.y
        # make sure point isn't dragged outside canvas
        x = max(0, x)
        y = max(0, y)
        x = min(img_view.canvas.winfo_width(), x)
        y = min(img_view.canvas.winfo_height(), y)
        if self.corner_selected:
            screen_width = self.window.winfo_screenwidth()
            point_size = int(0.005 * screen_width)  # TODO: make a member variable of this
            if self._drawn_dragged_point:
                img_view.canvas.delete(self._drawn_dragged_point)
            self._drawn_dragged_point = img_view.canvas.create_oval(
                # set point diagonal as 2% of monitor screen width
                x - point_size,
                y - point_size,
                x + point_size,
                y + point_size,
                fill='IndianRed1'
            )

    def release_callback(self, img_view: ImageView, event):
        x = event.x
        y = event.y
        # make sure point isn't dragged outside canvas
        x = max(0, x)
        y = max(0, y)
        x = min(img_view.canvas.winfo_width(), x)
        y = min(img_view.canvas.winfo_height(), y)
        if self.corner_selected:
            self.corner_selected = False
            if self._drawn_dragged_point:
                img_view.canvas.delete(self._drawn_dragged_point)
            self._drawn_dragged_point = None
            rel_x = (x - img_view.x_padding) / img_view.resized_width
            rel_y = (y - img_view.y_padding) / img_view.resized_height
            self.bounding_box[self.bounding_box.index(None)] = Point(rel_x, rel_y)
            #self.draw_bounding_box(img_view)
            self.warp_image()
            self.draw()

    def warp_image(self):
        corners_ndarray = self.points_to_ndarray(self.bounding_box)
        self.warped_image = warp_image(self.img, corners_ndarray)
        self.warp_activated = True

    def points_to_ndarray(self, points: List[Point]):
        img_width = self.img.shape[1]
        img_height = self.img.shape[0]
        return np.stack([np.array([p.x * img_width, p.y * img_height]) for p in points])



"""
how to create draggable point:
  1. on click find closest drawn point, use self.canvas.find_closest()
  2. if close enough find index of point, delete drawn point, set self.bounding_box[index] = None, and
     if a corner is None, then don't draw it (add if-statement in the drawing function), set
     a flag, self.moving_corner=True
  3. Draw point on cursor if self.moving_corner=True
  3. set self.moving_corner=False, get cursor position, create Point and replace with
     None value in self.bounding_box, redraw bounding_box
"""

def warp_image(img, corner_points):
    corner_points = _reorder_corner_points(corner_points, "warp")
    img_width = img.shape[1]
    img_height = img.shape[0]
    old_corner_points = np.float32(corner_points)
    new_corner_points = np.float32([[0, 0], [img_width, 0],
                                    [0, img_height], [img_width, img_height]])
    matrix = cv2.getPerspectiveTransform(old_corner_points, new_corner_points)
    img_warped = cv2.warpPerspective(img, matrix, (img_width, img_height))
    return img_warped

# reorder (for correct input to warping function
def _reorder_corner_points(corner_points, reorder_for="warp"):
    """
    reorder_for: "warp" | "drawing_bounding_box"
    """
    corner_points = corner_points.reshape((4, 2))
    reordered_points = np.zeros((4, 1, 2), np.int32)

    pair_sum = corner_points.sum(1)
    reordered_points[0] = corner_points[np.argmin(pair_sum)]
    reordered_points[3] = corner_points[np.argmax(pair_sum)]

    pair_diff = np.diff(corner_points, axis=1)
    if reorder_for == "warp":
        reordered_points[1] = corner_points[np.argmin(pair_diff)]
        reordered_points[2] = corner_points[np.argmax(pair_diff)]
    elif reorder_for == "drawing_bounding_box":
        reordered_points[2] = corner_points[np.argmin(pair_diff)]
        reordered_points[1] = corner_points[np.argmax(pair_diff)]
    else:
        raise ValueError("Unknown reorder_for. Allowed values: 'warp' or 'drawing_bounding_box'")
    return reordered_points



if __name__ == "__main__":
    fm = FishMesh()
    fm.run()
