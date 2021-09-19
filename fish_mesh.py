from typing import List
from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import cv2.cv2 as cv2
from pathlib import Path
from dataclasses import dataclass

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


class FishMesh:
    def __init__(self):
        # Init tkinter window:
        self.window = tk.Tk()
        self.window.title('File Explorer')
        #self.window.geometry("500x500")  # Set window size
        self.window.config(background="white")
        self.window.geometry(f"{self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()}")

        self.file_explorer_button = Button(
            self.window,
            bg="white",
            text="Browse Files",
            command=self.load_selected_file,
        )
        self.file_explorer_button.pack()

        self.selected_file = tk.StringVar()

        self.label_file_explorer = Label(
            self.window,
            text="No file selected",
            bg="white",
        )
        self.label_file_explorer.pack()

        self.img_cv2 = None

        self.canvas = Canvas(self.window, width=0, height=0, bg="white")
        self.canvas.pack(fill="both", expand=True)
        self.window.bind('<Configure>', self.resize_callback)

        self.rotate_buttons_frame = Frame(self.window)
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

        # drag corner callbacks
        self.bounding_box = []
        self.drawn_bounding_box = None
        """
        mouse-button  click      hold&move    release
        left          <Button-1>, <B1-Motion>, <ButtonRelease-1>
        middle        <Button-2>, <B2-Motion>, <ButtonRelease-2>
        right         <Button-3>, <B3-Motion>, <ButtonRelease-3>
        """
        self.corner_selected = False
        self._drawn_dragged_point = None
        self.canvas.bind("<Button-1>", self.click_callback)
        self.canvas.bind("<B1-Motion>", self.drag_callback)
        self.canvas.bind("<ButtonRelease-1>", self.release_callback)




    def load_selected_file(self):
        self.select_file()
        self.load_image()

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
        self.selected_file.set(filename)
        # Show selected file
        self.label_file_explorer.configure(text="Selected File: " + filename)

    def load_image(self):
        img_array_BGR = cv2.imread(self.selected_file.get())

        # OpenCV uses BGR color, but PIL expects RGB, so we need to convert image's color to RGB order
        img_array_RGB = cv2.cvtColor(img_array_BGR, cv2.COLOR_BGR2RGB)

        # https://stackoverflow.com/questions/19838972/how-to-update-an-image-on-a-canvas/19842646
        self.img_cv2 = img_array_RGB
        img = Image.fromarray(img_array_RGB)
        self.img_tk = ImageTk.PhotoImage(img)
        self.draw_image()
        self.init_bounding_box()
        self.draw_bounding_box()

    def _resize_image(self, event):
        # Maybe we also need to resize image to the window size:
        # https://stackoverflow.com/questions/24061099/tkinter-resize-background-image-to-window-size
        new_width = event.width
        new_height = event.height

        resized = cv2.resize(self.img_cv2, (new_width, new_height), interpolation=cv2.INTER_AREA)

        self.resized_img = ImageTk.PhotoImage(Image.fromarray(resized))
        #self.canvas.configure(image =  self.resized_img)

    def resize_image(self, preserve_aspect_ratio=True):
        img_width = len(self.img_cv2[0])
        img_height = len(self.img_cv2)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
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

            resized = cv2.resize(self.img_cv2, (new_img_width, new_img_height), interpolation=cv2.INTER_AREA)
            self.resized_img_width = new_img_width
            self.resized_img_height = new_img_height
        else:
            resized = cv2.resize(self.img_cv2, (canvas_width, canvas_height), interpolation=cv2.INTER_AREA)
            self.resized_img_width = canvas_width
            self.resized_img_height = canvas_height
        self.resized_img = ImageTk.PhotoImage(Image.fromarray(resized))

    def draw_image(self):
        if self.img_cv2 is None:
            return

        self.resize_image()

        # Get x,y position to center image drawn on canvas using anchor to NW
        x = (self.canvas.winfo_width() - self.resized_img_width) // 2
        y = (self.canvas.winfo_height() - self.resized_img_height) // 2
        self.image_on_canvas = self.canvas.create_image(x, y, image=self.resized_img, anchor=tk.NW)
        # The position is equal to the "padding" (on one side) required to preserve aspect ratio
        self.x_padding = x
        self.y_padding = y
        # self.canvas.configure(photo_img, height=photo_img.height(), width=photo_img.width())
        self.canvas.itemconfig(self.image_on_canvas, image=self.resized_img)
        self.canvas.image = self.resized_img
        self.canvas.configure(bg="black")

    def resize_callback(self, event):
        if self.img_cv2 is not None:
            self.draw_image()
            self.draw_bounding_box()

    def rotate_image_clockwise(self):
        self.img_cv2 = cv2.rotate(self.img_cv2, cv2.ROTATE_90_CLOCKWISE)
        self.draw_image()
        self.draw_bounding_box()

    def rotate_image_anticlockwise(self):
        self.img_cv2 = cv2.rotate(self.img_cv2, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.draw_image()
        self.draw_bounding_box()

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

    def draw_bounding_box(self):
        w = self.resized_img_width
        h = self.resized_img_height
        screen_width = self.window.winfo_screenwidth()
        point_size = int(0.005 * screen_width)
        # Delete the previously drawn points:
        if self.drawn_bounding_box:
            for drawn_corner in self.drawn_bounding_box:
                self.canvas.delete(drawn_corner)
        # Draw bounding box (and keep track of points):
        self.drawn_bounding_box = []
        for corner in self.bounding_box:
            if corner is not None:
                canvas_obj = self.canvas.create_oval(
                    # set point diagonal as 2% of monitor screen width
                    self.x_padding + int(w * corner.x) - point_size,
                    self.y_padding + int(h * corner.y) - point_size,
                    self.x_padding + int(w * corner.x) + point_size,
                    self.y_padding + int(h * corner.y) + point_size,
                    fill='red'
                )
                self.drawn_bounding_box.append(canvas_obj)


    def click_callback(self, event):
        x = event.x
        y = event.y
        if self.drawn_bounding_box is not None:  # coreners must be drawn
            closest = self.canvas.find_closest(x, y, halo=10, start=self.drawn_bounding_box)
            selected_corner_tag = closest[0]
            if selected_corner_tag in self.drawn_bounding_box:
                self.selected_corner_idx = self.drawn_bounding_box.index(selected_corner_tag)
                self.canvas.delete(selected_corner_tag)
                self.drawn_bounding_box.remove(selected_corner_tag)
                self.bounding_box[self.selected_corner_idx] = None
                self.corner_selected = True

    def drag_callback(self, event):
        x = event.x
        y = event.y
        # make sure point isn't dragged outside canvas
        x = max(0, x)
        y = max(0, y)
        x = min(self.canvas.winfo_width(), x)
        y = min(self.canvas.winfo_height(), y)
        if self.corner_selected:
            screen_width = self.window.winfo_screenwidth()
            point_size = int(0.005 * screen_width)  # TODO: make a member variable of this
            if self._drawn_dragged_point:
                self.canvas.delete(self._drawn_dragged_point)
            self._drawn_dragged_point = self.canvas.create_oval(
                # set point diagonal as 2% of monitor screen width
                x - point_size,
                y - point_size,
                x + point_size,
                y + point_size,
                fill='IndianRed1'
            )

    def release_callback(self, event):
        x = event.x
        y = event.y
        # make sure point isn't dragged outside canvas
        x = max(0, x)
        y = max(0, y)
        x = min(self.canvas.winfo_width(), x)
        y = min(self.canvas.winfo_height(), y)
        if self.corner_selected:
            self.corner_selected = False
            if self._drawn_dragged_point:
                self.canvas.delete(self._drawn_dragged_point)
            self._drawn_dragged_point = None
            rel_x = (x - self.x_padding) / self.resized_img_width
            rel_y = (y - self.y_padding) / self.resized_img_height
            self.bounding_box[self.bounding_box.index(None)] = Point(rel_x, rel_y)
            self.draw_bounding_box()


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

@dataclass
class Point:
    x: float
    y: float


if __name__ == "__main__":
    fm = FishMesh()
    fm.run()
