from typing import List, Optional
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import cv2.cv2 as cv2
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from functools import partial
from copy import deepcopy

import tkinter as tk
from tkinter import ttk

# from colors import colors

"""
TODO 
  * consider adding zoom functionality (this might leave the resize logic unnecessary; which is good)
    https://stackoverflow.com/questions/41656176/tkinter-canvas-zoom-move-pan
  * draw multiple lines:
    * left-click:
      * if not close to another point: (probably need to extend existing callback for right_view)
      * 
    * right-click:
      * if drawing_ruler: cancel
      * if not drawling_ruler and sufficiently close to point: delete ruler related to point (delete both points and line)
"""

colors = [
    "red",
    "green",
    "blue",
    "orange",
    "magenta",
    "brown",
    "gray",
    "yellow green",
    "blue violet",
    "cornflower blue",
    "dark orange",
    "cyan",
    "coral",
    "gold",
    "hot pink",
    "green yellow",
    "maroon",
    "purple"
]

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

    points = None
    drawn_points = None
    lines = None
    drawn_lines = None
    # dragging_point = False       # TODO: consider if these should be tied to FishMesh (since you can only click on one view at a time, so they should maybe be "global" to the program
    # drawn_dragging_point = None  # TODO: consider if these should be tied to FishMesh (since you can only click on one view at a time, so they should maybe be "global" to the program

@dataclass
class Point:
    x: float
    y: float
    ruler_id: Optional[int] = None
    color: Optional[str] = None
    drawing_id: Optional[int] = None

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

        screen_width = self.window.winfo_screenwidth()
        self.point_radii = int(0.005 * screen_width)  # Make point sizes 1 % of monitor width

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
        self.displayed_text = None
        self.warped_image = None

        self.dragged_point: Optional[Point] = None

        self.new_ruler_start_point = None
        self.drawn_ruler_end = None
        self.drawn_ruler_line = None
        self.num_rulers_created = 0
        self.rulers = []

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

        """
        mouse-button  click      hold&move    release
        left          <Button-1>, <B1-Motion>, <ButtonRelease-1>
        middle        <Button-2>, <B2-Motion>, <ButtonRelease-2>
        right         <Button-3>, <B3-Motion>, <ButtonRelease-3>
        """
        self.left_view.canvas.bind("<Button-1>", partial(self.left_click_callback, self.left_view, False))
        self.left_view.canvas.bind("<B1-Motion>", partial(self.drag_callback, self.left_view))
        self.left_view.canvas.bind("<ButtonRelease-1>", partial(self.release_callback, self.left_view))

        self.right_view.canvas.bind("<Button-1>", partial(self.left_click_callback, self.right_view, True))
        self.right_view.canvas.bind("<B1-Motion>", partial(self.drag_callback, self.right_view))
        self.right_view.canvas.bind("<ButtonRelease-1>", partial(self.release_callback, self.right_view))
        self.right_view.canvas.bind("<Motion>", partial(self.move_callback, self.right_view))
        #self.right_view.canvas.bind("<Button-2>", partial(self.right_click_callback, self.right_view))
        self.right_view.canvas.bind("<Button-3>", partial(self.right_click_callback, self.right_view))

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
        self.init_bounding_box(self.left_view)
        self.warp_image()
        # self.init_ruler(self.right_view)
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
            self.draw_ruler(self.right_view)
            # self.draw_ruler_measure()  # TODO: make it work with multiple rulers


    def resize_callback(self, event):
        self.draw()  # redraw everything to the new canvas display sizes

    def rotate_image_clockwise(self):
        # self.rotate_points("clockwise")
        self.img = cv2.rotate(self.img, cv2.ROTATE_90_CLOCKWISE)
        self.init_bounding_box(self.left_view)  # redraw box since it is hard to rotate points
        self.warp_image()
        self.draw()

    def rotate_image_anticlockwise(self):
        # self.rotate_points("anticlockwise")
        self.img = cv2.rotate(self.img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.init_bounding_box(self.left_view)  # redraw box since it is hard to rotate points
        self.warp_image()
        self.draw()

    # def rotate_points(self, direction: str):
    #     """
    #     This doesn't work.
    #     Things that I need to consider:
    #     * when rotating paddings change, since the view is rectangular, it can lead to a smaller or greater padding
    #       in the new direction. (maybe I need both paddings before and after to do this right)
    #     * I feel like there should be a way to just swap coordinates as long as I get the new padding
    #     * I have the canbas width and height and resized image width and height, so I got everything I need
    #
    #     ooo PROBLEM!, image might be resized during rotation,... then all points must be scaled differently when scaling back
    #     """
    #     # xs = [p.x * self.left_view.resized_width + self.left_view.x_padding for p in self.left_view.points]
    #     # ys = [p.y * self.left_view.resized_height + self.left_view.y_padding for p in self.left_view.points]
    #     # center_x = np.sum(xs) / len(ys)
    #     # center_y = np.sum(ys) / len(ys)
    #     # for x, y, p in zip(xs, ys, self.left_view.points):
    #     #     # translate point to origin:
    #     #     tx, ty = x - center_x, y - center_y
    #     #     # rotate:
    #     #     if direction == "clockwise":
    #     #         rtx, rty = -ty, tx
    #     #     elif direction == "anticlockwise":
    #     #         rtx, rty = ty, -tx
    #     #     else:
    #     #         raise ValueError("Unknown 'direction', expected 'clockwise' or 'anticlockwise'")
    #     #     # translate back
    #     #     rx, ry = rtx + center_x, rty + center_y
    #     #     # Calculate relative points:
    #     #     p.x = (rx - self.left_view.x_padding) / self.left_view.resized_width
    #     #     p.y = (ry - self.left_view.y_padding) / self.left_view.resized_height
    #
    #     new_padding_x = self.left_view.resized_height - self.left_view.canvas.winfo_width()  # ooo, image might be resized during rotation,... then all points must be scaled differently when scaling back
    #     for p in self.left_view.points:
    #         old_x_px = p.x * self.left_view.resized_width + self.left_view.x_padding
    #         old_y_px = p.y * self.left_view.resized_height  + self.left_view.y_padding
    #         old_view_height = 2 * self.left_view.y_padding + self.left_view.resized_height
    #         new_x_px = old_view_height - old_y_px
    #         new_y_px = old_x_px
    #         p.x = (new_x_px - self.left_view.x_padding) / self.left_view.resized_width
    #         p.y = (new_y_px - self.left_view.y_padding) / self.left_view.resized_height
    #
    # def rotate_points_anticlockwise(self):
    #     for p in self.left_view.points:
    #         old_x_px = p.x * self.left_view.resized_width + self.left_view.x_padding
    #         old_y_px = p.y * self.left_view.resized_height  + self.left_view.y_padding
    #         old_view_width = 2 * self.left_view.x_padding + self.left_view.resized_width
    #         new_x_px = old_y_px
    #         new_y_px = old_view_width - old_x_px
    #         p.x = (new_x_px - self.left_view.x_padding) / self.left_view.resized_width
    #         p.y = (new_y_px - self.left_view.y_padding) / self.left_view.resized_height
    #
    def run(self):
        self.window.mainloop()

    def init_bounding_box(self, img_view):
        # w = self.canvas.winfo_width()
        # h = self.canvas.winfo_height()
        top_left = Point(0.20, 0.20)
        bottom_left = Point(0.20, 0.80)
        bottom_right = Point(0.80, 0.80)
        top_right = Point(0.80, 0.20)
        img_view.points = [top_left, bottom_left, bottom_right, top_right]

    def draw_bounding_box(self, img_view):
        if img_view.points is None or len(img_view.points) == 0:
            self.init_bounding_box(img_view)

        # TODO: simplify drawing lines and points (naming and structuring should also be improved)
        # Draw lines
        # To get the correct pair of points we need a certain order:
        if img_view.drawn_lines:
            for line in img_view.drawn_lines:
                img_view.canvas.delete(line)
        img_view.drawn_lines = []
        x0 = img_view.x_padding
        y0 = img_view.y_padding
        point_arr = np.stack([np.array([(p.x * img_view.resized_width) + x0, (p.y * img_view.resized_height) + y0 ]) for p in img_view.points])
        # order to get top_left, top_right, bottom_right, bottom_left:
        ordered_point_arr = _reorder_corner_points(point_arr, "drawing_bounding_box")
        ps = np.reshape(ordered_point_arr, (4,2))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[0,0], ps[0,1], ps[1,0], ps[1,1], fill="red"))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[1,0], ps[1,1], ps[2,0], ps[2,1], fill="red"))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[2,0], ps[2,1], ps[3,0], ps[3,1], fill="red"))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[3,0], ps[3,1], ps[0,0], ps[0,1], fill="red"))

        w = img_view.resized_width
        h = img_view.resized_height
        # Delete the previously drawn points:
        if img_view.drawn_points:
            for drawn_corner in img_view.drawn_points:
                img_view.canvas.delete(drawn_corner)
        # Draw bounding box (and keep track of points):
        img_view.drawn_points = []
        for point in img_view.points:
            if point is not None:
                canvas_point = img_view.canvas.create_oval(
                    # set point diagonal as 2% of monitor screen width
                    img_view.x_padding + int(w * point.x) - self.point_radii,
                    img_view.y_padding + int(h * point.y) - self.point_radii,
                    img_view.x_padding + int(w * point.x) + self.point_radii,
                    img_view.y_padding + int(h * point.y) + self.point_radii,
                    fill='red'
                )
                img_view.drawn_points.append(canvas_point)

    # def init_ruler(self, img_view):
    #     # w = self.canvas.winfo_width()
    #     # h = self.canvas.winfo_height()
    #     left = Point(0, 0.50)
    #     right = Point(0.50, 0.50)
    #     img_view.points = [left, right]
    def draw_point(self, img_view: ImageView, point: Point, color=None):
        w = img_view.resized_width
        h = img_view.resized_height
        _color = 'IndianRed1'
        if point.color is not None:
            _color = point.color
        if color is not None:
            _color = color
        drawing = img_view.canvas.create_oval(
            img_view.x_padding + int(w * point.x) - self.point_radii,
            img_view.y_padding + int(h * point.y) - self.point_radii,
            img_view.x_padding + int(w * point.x) + self.point_radii,
            img_view.y_padding + int(h * point.y) + self.point_radii,
            fill=_color
        )
        return drawing

    def draw_ruler(self, img_view):
        if img_view.points is None or len(img_view.points) == 0:
            # self.init_ruler(img_view)
            return

        w = img_view.resized_width
        h = img_view.resized_height

        # find rulers:
        rulers = {}
        for p in img_view.points:
            if p.ruler_id not in rulers:
                rulers[p.ruler_id] = [p]
            else:
                rulers[p.ruler_id].append(p)

        # Before drawing, delete existing liness:
        if img_view.drawn_lines:
            for line in img_view.drawn_lines:
                img_view.canvas.delete(line)
        # Delete the previously drawn points:
        if img_view.drawn_points:
            for drawn_corner in img_view.drawn_points:
                img_view.canvas.delete(drawn_corner)
        # Draw the ruler's line
        img_view.drawn_lines = []
        img_view.drawn_points = []
        for ruler in rulers.values():
            p1 = ruler[0]
            p2 = ruler[1]
            # Draw line:
            img_view.drawn_lines.append(img_view.canvas.create_line(
                img_view.x_padding + (w * p1.x),
                img_view.y_padding + (h * p1.y),
                img_view.x_padding + (w * p2.x),
                img_view.y_padding + (h * p2.y),
                width=1,
                fill=p1.color
            ))
            # Draw points:
            drawn_point = img_view.canvas.create_oval(
                img_view.x_padding + int(w * p1.x) - self.point_radii,
                img_view.y_padding + int(h * p1.y) - self.point_radii,
                img_view.x_padding + int(w * p1.x) + self.point_radii,
                img_view.y_padding + int(h * p1.y) + self.point_radii,
                fill=p1.color
            )
            p1.drawing_id = drawn_point
            img_view.drawn_points.append(drawn_point)

            drawn_point = img_view.canvas.create_oval(
                img_view.x_padding + int(w * p2.x) - self.point_radii,
                img_view.y_padding + int(h * p2.y) - self.point_radii,
                img_view.x_padding + int(w * p2.x) + self.point_radii,
                img_view.y_padding + int(h * p2.y) + self.point_radii,
                fill=p2.color
            )
            p2.drawing_id = drawn_point
            img_view.drawn_points.append(drawn_point)

    def read_ruler(self):
        points = self.right_view.points
        p1 = points[0]
        p2 = points[1]
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def draw_ruler_measure(self):
        ruler_length = self.read_ruler()
        ruler_percentage_length = ruler_length * 100
        text = f"relative length: {ruler_percentage_length:.2f} %"
        if self.displayed_text is not None:
            self.right_view.canvas.delete(self.displayed_text)
        self.displayed_text = self.right_view.canvas.create_text(10, 10, text=text, fill="red", anchor=tk.NW, font=(None, 16))


    def left_click_callback(self, img_view: ImageView, create_rulers_on_click: bool, event):
        x = event.x
        y = event.y
        x = max(img_view.x_padding, x)
        y = max(img_view.y_padding, y)
        x = min(img_view.canvas.winfo_width() - img_view.x_padding, x)
        y = min(img_view.canvas.winfo_height() - img_view.y_padding, y)
        drawn_points = img_view.drawn_points if img_view.drawn_points is not None else []
        closest = img_view.canvas.find_closest(x, y, halo=10, start=drawn_points)
        selected_point_id = closest[0]
        if selected_point_id in drawn_points:
            # img_view.dragging_point = True
            # # Delete selected point (it will be redrawn on the release position)
            # selected_point_idx = img_view.drawn_points.index(selected_point_id)
            # del img_view.points[selected_point_idx]
            # img_view.canvas.delete(selected_point_id)
            # img_view.drawn_points.remove(selected_point_id)
            # # Remove lines (this is easier than to draw lines for all points in the drag_callback)
            # if img_view.drawn_lines:
            #     for line in img_view.drawn_lines:
            #         img_view.canvas.delete(line)

            # create reference to point in img_view.points to easily adjust its position:
            # Find the clicked point
            selected_point_idx = img_view.drawn_points.index(selected_point_id)
            self.dragged_point = img_view.points[selected_point_idx]
            # Update dragged_point with click position (might be slightly off original position):
            self.dragged_point.x = (x - img_view.x_padding) / img_view.resized_width
            self.dragged_point.y = (y - img_view.y_padding) / img_view.resized_height
            # First part of animation: removing it from original position to a position centered on mouse:
            img_view.drawn_points.remove(selected_point_id)
            #self.dragged_point.drawing_id = self.draw_point(img_view, self.dragged_point)
            self.draw()
        elif create_rulers_on_click:
            if self.new_ruler_start_point is None:
                # Add the released point:
                rel_x = (x - img_view.x_padding) / img_view.resized_width
                rel_y = (y - img_view.y_padding) / img_view.resized_height
                self.new_ruler_start_point = Point(
                    rel_x, rel_y, self.num_rulers_created + 1, colors[(self.num_rulers_created + 1) % len(colors)]
                )
                self.new_ruler_start_point.drawing_id = self.draw_point(img_view, self.new_ruler_start_point)
            else:
                rel_x = (x - img_view.x_padding) / img_view.resized_width
                rel_y = (y - img_view.y_padding) / img_view.resized_height
                self.num_rulers_created += 1
                if img_view.points is None:
                    img_view.points = []
                img_view.points.extend([
                    deepcopy(self.new_ruler_start_point),
                    Point(
                        rel_x, rel_y, self.num_rulers_created, colors[self.num_rulers_created % len(colors)]
                    )
                ])
                img_view.canvas.delete(self.new_ruler_start_point.drawing_id)
                img_view.canvas.delete(self.drawn_ruler_end)
                img_view.canvas.delete(self.drawn_ruler_line)
                self.drawn_ruler_end = None
                self.drawn_ruler_line = None
                self.new_ruler_start_point = None
                self.draw()


    def drag_callback(self, img_view: ImageView, event):
        x = event.x
        y = event.y

        # make sure point isn't dragged outside canvas
        x = max(img_view.x_padding, x)
        y = max(img_view.y_padding, y)
        x = min(img_view.canvas.winfo_width() - img_view.x_padding, x)
        y = min(img_view.canvas.winfo_height() - img_view.y_padding, y)

        # if img_view.dragging_point:
        #     if img_view.drawn_dragging_point:
        #         img_view.canvas.delete(img_view.drawn_dragging_point)
        #     img_view.drawn_dragging_point = img_view.canvas.create_oval(
        #         # set point diagonal as 2% of monitor screen width
        #         x - self.point_radii,
        #         y - self.point_radii,
        #         x + self.point_radii,
        #         y + self.point_radii,
        #         fill='IndianRed1'
        #     )
        if self.dragged_point is not None:
            img_view.canvas.delete(self.dragged_point.drawing_id)
            # Update dragged_point with click position to moving mouse:
            self.dragged_point.x = (x - img_view.x_padding) / img_view.resized_width
            self.dragged_point.y = (y - img_view.y_padding) / img_view.resized_height
            #self.dragged_point.drawing_id = self.draw_point(img_view, self.dragged_point)
            self.draw()

    def release_callback(self, img_view: ImageView, event):
        # if img_view.dragging_point:
        #     x = event.x
        #     y = event.y
        #
        #     # make sure point isn't dragged outside canvas
        #     x = max(img_view.x_padding, x)
        #     y = max(img_view.y_padding, y)
        #     x = min(img_view.canvas.winfo_width() - img_view.x_padding, x)
        #     y = min(img_view.canvas.winfo_height() - img_view.y_padding, y)
        #
        #     img_view.dragging_point = False  # On release we're no longer dragging the point
        #     if img_view.drawn_dragging_point:
        #         img_view.canvas.delete(img_view.drawn_dragging_point)
        #     img_view.drawn_dragging_point = None
        #     # Add the released point:
        #     rel_x = (x - img_view.x_padding) / img_view.resized_width
        #     rel_y = (y - img_view.y_padding) / img_view.resized_height
        #     img_view.points.append(Point(rel_x, rel_y))  #img_view.points[img_view.points.index(None)] = Point(rel_x, rel_y)
        #     self.warp_image()
        #     self.draw()
        if self.dragged_point is not None:
            x = event.x
            y = event.y
            # make sure point isn't dragged outside canvas
            x = max(img_view.x_padding, x)
            y = max(img_view.y_padding, y)
            x = min(img_view.canvas.winfo_width() - img_view.x_padding, x)
            y = min(img_view.canvas.winfo_height() - img_view.y_padding, y)

            img_view.canvas.delete(self.dragged_point.drawing_id)
            # Update point with the release position:
            self.dragged_point.x = (x - img_view.x_padding) / img_view.resized_width
            self.dragged_point.y = (y - img_view.y_padding) / img_view.resized_height
            self.dragged_point = None
            self.warp_image()
            self.draw()

    def move_callback(self, img_view: ImageView, event):
        if self.new_ruler_start_point is not None:
            x = event.x
            y = event.y

            # make sure point isn't dragged outside canvas
            x = max(img_view.x_padding, x)
            y = max(img_view.y_padding, y)
            x = min(img_view.canvas.winfo_width() - img_view.x_padding, x)
            y = min(img_view.canvas.winfo_height() - img_view.y_padding, y)

            img_view.canvas.delete(self.new_ruler_start_point.drawing_id)
            start_x = self.new_ruler_start_point.x * img_view.resized_width + img_view.x_padding
            start_y = self.new_ruler_start_point.y * img_view.resized_height + img_view.y_padding
            self.new_ruler_start_point.drawing_id = img_view.canvas.create_oval(
                start_x - self.point_radii,
                start_y - self.point_radii,
                start_x + self.point_radii,
                start_y + self.point_radii,
                fill=self.new_ruler_start_point.color
            )
            if self.drawn_ruler_end is not None:
                img_view.canvas.delete(self.drawn_ruler_end)
            self.drawn_ruler_end = img_view.canvas.create_oval(
                x - self.point_radii,
                y - self.point_radii,
                x + self.point_radii,
                y + self.point_radii,
                fill=self.new_ruler_start_point.color
            )
            if self.drawn_ruler_line is not None:
                img_view.canvas.delete(self.drawn_ruler_line)
            self.drawn_ruler_line = img_view.canvas.create_line(
                start_x,
                start_y,
                x,
                y,
                fill=self.new_ruler_start_point.color
            )

    def right_click_callback(self, img_view: ImageView, event):
        x = event.x
        y = event.y
        if self.new_ruler_start_point is not None:
            # if drawing a new ruler, cancel drawing the ruler
            img_view.canvas.delete(self.new_ruler_start_point.drawing_id)
            if self.drawn_ruler_end is not None:
                img_view.canvas.delete(self.drawn_ruler_end)
                self.drawn_ruler_end = None
            if self.drawn_ruler_line is not None:
                img_view.canvas.delete(self.drawn_ruler_line)
                self.drawn_ruler_line = None
            self.new_ruler_start_point = None
        elif img_view.drawn_points is not None:
            closest = img_view.canvas.find_closest(x, y, halo=10, start=img_view.drawn_points)
            selected_point_id = closest[0]
            if selected_point_id in img_view.drawn_points:
                # Delete selected point (it will be redrawn on the release position)
                selected_point_idx = img_view.drawn_points.index(selected_point_id)
                selected_ruler_id = img_view.points[selected_point_idx].ruler_id
                img_view.drawn_points.remove(selected_point_id)
                img_view.canvas.delete(selected_point_id)
                del img_view.points[selected_point_idx]
                connected_point_idx = 0
                for p in img_view.points:
                    if p.ruler_id == selected_ruler_id:
                        break
                    connected_point_idx += 1
                connected_point_drawing_id = img_view.points[connected_point_idx].drawing_id
                img_view.drawn_points.remove(connected_point_drawing_id)
                img_view.canvas.delete(connected_point_drawing_id)
                del img_view.points[connected_point_idx]
                # self.rulers.remove[selected_ruler_id]
                self.draw()

    def warp_image(self):
        corners_ndarray = self.points_to_ndarray(self.left_view.points)
        self.warped_image = warp_image(self.img, corners_ndarray)
        self.warp_activated = True

    def points_to_ndarray(self, points: List[Point]):
        img_width = self.img.shape[1]
        img_height = self.img.shape[0]
        return np.stack([np.array([p.x * img_width, p.y * img_height]) for p in points])


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
    pair_diff = np.diff(corner_points, axis=1)
    if reorder_for == "warp":
        reordered_points[0] = corner_points[np.argmin(pair_sum)]
        reordered_points[3] = corner_points[np.argmax(pair_sum)]

        reordered_points[1] = corner_points[np.argmin(pair_diff)]
        reordered_points[2] = corner_points[np.argmax(pair_diff)]
    elif reorder_for == "drawing_bounding_box":
        reordered_points[0] = corner_points[np.argmin(pair_sum)]  # x+y smallest (upper left)
        reordered_points[2] = corner_points[np.argmax(pair_sum)]  # x+y largest (lower right)

        reordered_points[3] = corner_points[np.argmin(pair_diff)]  # x-y smallest (lower left)
        reordered_points[1] = corner_points[np.argmax(pair_diff)]  # x-y larger (upper right)
    else:
        raise ValueError("Unknown reorder_for. Allowed values: 'warp' or 'drawing_bounding_box'")
    return reordered_points


"""
Create draggable point:
  1. on click find closest drawn point, use self.canvas.find_closest()
  2. if close enough find index of point, delete drawn point, set self.bounding_box[index] = None, and
     if a corner is None, then don't draw it (add if-statement in the drawing function), set
     a flag, self.moving_corner=True
  3. Draw point on cursor if self.moving_corner=True
  3. set self.moving_corner=False, get cursor position, create Point and replace with
     None value in self.bounding_box, redraw bounding_box
"""

if __name__ == "__main__":
    fm = FishMesh()
    fm.run()
