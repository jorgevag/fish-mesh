#!/usr/bin/env python
import logging
import re
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from tkinter import *
from tkinter import filedialog, messagebox
import tkinter as tk
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from functools import partial
from copy import deepcopy

import exif
import cv2.cv2 as cv2
from PIL import ImageTk, Image
from pandas import DataFrame
import dacite

from settings import Settings, SettingsError, DEFAULT_SETTINGS_PATH
from settings_dialog import SettingsDialog


logging.basicConfig(filename='logs.log',
                    filemode='w',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class WriteResultFileError(Exception):
    pass


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


@dataclass
class Point:
    x: float
    y: float
    ruler_id: Optional[int] = None
    color: Optional[str] = None
    drawing_id: Optional[int] = None

@dataclass
class RelativeComponent:
    x: float
    y: float
    w: float  # width
    h: float  # height


class FishMesh:
    def __init__(self, settings: Optional[Settings] = None):
        logger.info("Starting program")
        self.window = tk.Tk()
        self.window.title('fish-mesh')
        self.window.config(background="white")
        self.window.geometry(f"{self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()}")
        # self.window.iconbitmap(default="fish-mesh.ico")  # icon not compatible across OSs (TODO)
        # https://stackoverflow.com/questions/20860325/python-3-tkinter-iconbitmap-error-in-ubuntu

        self.settings: Settings
        if settings is not None:
            self.settings = settings
        elif DEFAULT_SETTINGS_PATH.exists():
            try:
                self.settings = Settings.from_file(DEFAULT_SETTINGS_PATH)
            except (dacite.DaciteError, dacite.DaciteFieldError, dacite.UnexpectedDataError) as e:
                messagebox.showwarning(
                    "Invalid settings file",
                    f"Found fish-mesh-settings.json, but this was not"
                    f" correctly formatted and will be ignored."
                    f"\n\n"
                    f"To remove this warning, either"
                    " overwrite it by going to 'settings' and"
                    " choosing to save for future sessions"
                    f" or delete the settings file located"
                    f" at {DEFAULT_SETTINGS_PATH}"
                )
                logger.exception(e)
                self.settings = Settings()
        else:
            self.settings = Settings()
        # Init tkinter window:

        self.point_radii = max(int(self.settings.point_size / 2), 1)
        self.margin_ratio = self.settings.measure_box_margin_percentage / 100

        self.top_menu = tk.Frame(self.window, background="white")
        self.top_menu.pack(fill="x")#, expand=True)
        self.input_folder = Path.cwd().__str__()
        self.input_file_explorer_button = Button(
            self.top_menu,
            bg="white",
            text="Browse Files",
            command=self.select_and_load_file,
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )
        # self.input_file_explorer_button.pack(side=LEFT, fill="x", expand=True)
        self.input_file_explorer_button.pack(side=tk.LEFT)
        self.selected_input_file = None
        self.settings_button = Button(
            self.top_menu,
            bg="white",
            text="Settings",
            command=self.change_settings,
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )
        self.settings_button.pack(side=tk.RIGHT)

        self.img = None
        self.warped_image = None
        self.output_dir = None

        self.dragged_point: Optional[Point] = None

        self.measure_box_lines = []

        self.new_ruler_start_point = None
        self.drawn_ruler_end = None
        self.drawn_ruler_line = None
        self.num_rulers_created = 0
        self.drawn_ruler_labels = []

        self.image_displays = tk.Frame(self.window)
        self.image_displays.pack(fill="both", expand=True)
        self.left_view = ImageView()
        self.left_view.canvas = Canvas(self.image_displays, width=0, height=0, bg="white")
        # self.left_view.canvas.pack(side=LEFT, fill="both", expand=True)
        self.left_view.canvas.pack(fill="both", expand=True)
        self.right_view = ImageView()
        self.right_view.canvas = Canvas(self.image_displays, width=0, height=0, bg="white")
        # self.right_view.canvas.pack(side=RIGHT, fill="both", expand=True)
        self.in_box_drawing_window = True
        self.mini_window_spec = RelativeComponent(x=0.8, y=0.0, w=0.2, h=0.2)
        self.show_mini_window = self.settings.show_mini_window_on_start
        toggle_win_button_text = "Show"
        if self.show_mini_window:
            toggle_win_button_text = "Hide"
            self.right_view.canvas.place(
                relx=self.mini_window_spec.x,
                rely=self.mini_window_spec.y,
                relwidth=self.mini_window_spec.w,
                relheight=self.mini_window_spec.h,
            )
        self.toggle_mini_window_button = tk.Button(
            self.top_menu,
            text=toggle_win_button_text,
            command=self.toggle_mini_window,
            bg="white",
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )
        self.toggle_mini_window_button.pack(side=tk.RIGHT)


        self.window.bind('<Configure>', self.resize_callback)

        """
        mouse-button  click      hold&move    release
        left          <Button-1>, <B1-Motion>, <ButtonRelease-1>
        middle        <Button-2>, <B2-Motion>, <ButtonRelease-2>
        right         <Button-3>, <B3-Motion>, <ButtonRelease-3>
        """
        self.left_view.canvas.bind("<Button-1>", partial(self.left_click_callback, self.left_view, False, "image"))
        self.left_view.canvas.bind("<B1-Motion>", partial(self.drag_callback, self.left_view, "image"))
        self.left_view.canvas.bind("<ButtonRelease-1>", partial(self.release_callback, self.left_view, "image"))

        self.right_view.canvas.bind("<Button-1>", partial(self.left_click_callback, self.right_view, True, "box"))
        self.right_view.canvas.bind("<B1-Motion>", partial(self.drag_callback, self.right_view, "box"))
        self.right_view.canvas.bind("<ButtonRelease-1>", partial(self.release_callback, self.right_view, "box"))
        self.right_view.canvas.bind("<Motion>", partial(self.move_callback, self.right_view, "box"))
        # button 2 and 3 (middle and right) might vary from OS, so assign both:
        self.right_view.canvas.bind("<Button-2>", partial(self.right_click_callback, self.right_view))
        self.right_view.canvas.bind("<Button-3>", partial(self.right_click_callback, self.right_view))

        self.rotate_anticlockwise_button = Button(
            self.top_menu,
            text="\u21BB",  # unicode char for anticlockwise circular arrow
            command=self.rotate_image_clockwise,
            bg="white",
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )
        self.rotate_anticlockwise_button.pack(side=tk.LEFT)
        self.rotate_clockwise_button = Button(
            self.top_menu,
            text="\u21BA",  # unicode char for anticlockwise circular arrow
            command=self.rotate_image_anticlockwise,
            bg="white",
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )
        self.rotate_clockwise_button.pack(side=tk.LEFT)

        self.to_measurement_window_button = Button(
            self.top_menu,
            bg="white",
            text="To measurement window",
            command=self.go_to_measurement_window,
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )
        self.to_measurement_window_button.pack(side=tk.LEFT)
        self.to_box_drawing_window_button = Button(
            self.top_menu,
            bg="white",
            # text="\u2190",  # Arrow
            text="Back to box drawing window",  # Arrow
            command=self.go_to_box_drawing_window,
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )

        self.save_button = Button(
            self.top_menu,
            text="Save measurements",
            command=self.save_callback,
            bg="white",
            # # remove border:
            # highlightthickness=0,
            # bd=0
        )
        self.saved_points: Optional[List[Point]] = None
        self.output_folder = Path.cwd().__str__()

    def select_and_load_file(self):
        selected_file = self.select_file()
        if selected_file:
            self.input_folder = Path(selected_file).parent

            if self.right_view.points is not None and self.right_view.points != self.saved_points:
                # TODO: make a configuration to not get warning before opening
                answered_yes = messagebox.askyesno(
                    "Load new image?",
                    "Opening a new image will end the current session and reset measurements."
                )
                if not answered_yes:
                    return
            try:
                self.img = self.load_image(selected_file)
            except Exception as e:
                messagebox.showerror(
                    "Image File Error",
                    "Could not load image. Make sure the selected file is an image file."
                )
                logger.error(
                    f"Encountered error while trying to load image from the selected file {repr(selected_file)}:"
                )
                logger.exception(e)
            else:
                logger.info("Successfully loaded image file")
                self.selected_input_file = selected_file
                # Clear any potential drawings from a previous image:
                self.clear_all_drawings()
                # Move to the bounding box drawing view:
                self.go_to_box_drawing_window()
                # After file has loaded, show image, and draw initial bounding box and warped image
                self.init_bounding_box(self.left_view)
                self.warp_image()
                self.draw()

    def select_file(self):
        """opening file explorer window"""
        selected_input_file = filedialog.askopenfilename(
            initialdir=self.input_folder,
            title="Select a File",
            # filetypes=(
            #     ("all files", "*.*"),
            #     ("Text files", "*.txt*"),
            # )
        )
        logger.info(f"Selected file {selected_input_file}")
        return selected_input_file

    def clear_all_drawings(self):
        # Note: order of steps matter
        # 1) Delete stored drawings from canvas:
        clear_drawings(self.left_view)
        clear_drawings(self.right_view)
        self.clear_ruler_label_drawings()
        # 2) Clear containers storing the drawing references:
        self.right_view.points = None
        self.right_view.lines = None
        self.num_rulers_created = 0
        self.drawn_ruler_labels = []

    def change_settings(self):
        dialog = SettingsDialog(title="Settings", parent=self.window, settings=self.settings)
        settings = dialog.get_settings()
        try:
            settings.validate()
        except SettingsError as e:
            messagebox.showerror(f"Incorrect settings", str(e))
        else:
            old_settings = self.settings
            self.settings = settings
            self.update_program_with_new_settings(old_settings)

    def update_program_with_new_settings(self, old_settings: Settings):
        self.point_radii = max(int(self.settings.point_size / 2), 1)
        self.margin_ratio = self.settings.measure_box_margin_percentage / 100
        # settings might change properties related to the bounding box.
        # Since ruler points doesn't know about the margin, we need to
        # rescale all the drawn rulers:
        if self.img is not None:
            self.warp_image()
        if self.right_view.points is not None:
            old_margin_ratio = old_settings.measure_box_margin_percentage / 100
            new_margin_ratio = self.settings.measure_box_margin_percentage / 100
            scaling = (1 - 2 * new_margin_ratio) / ( 1 - 2 * old_margin_ratio)
            for i, p in enumerate(self.right_view.points):
                # get coordinates of points relativee to center of image
                # (in order to scale rulers relative to the center of the image):
                cpx = p.x - 0.5
                cpy = p.y - 0.5
                # scale:
                scpx = cpx * scaling
                scpy = cpy * scaling
                # translate coordinates back to original origin:
                spx = scpx + 0.5
                spy = scpy + 0.5
                self.right_view.points[i].x = spx
                self.right_view.points[i].y = spy
        self.draw()

    def get_default_filename(self, exif_datetime_str: Optional[str] = None) -> str:
        exif_datetime_format = "%Y:%m:%d %H:%M:%S"  # TODO: verify if there is variation in the exif datetime format
        filename_datetime_format = "%Y-%m-%d--%H-%M"
        if exif_datetime_str:  # if not None and not empty string
            try:
                efix_datetime = datetime.strptime(exif_datetime_str, exif_datetime_format).strftime(filename_datetime_format)
            except ValueError as e:
                logger.error(
                    f"Unable to format exif datetime string {repr(exif_datetime_str)}"
                    f" to format {exif_datetime_format}. Conversion failed with error:"
                )
                logger.exception(e)
                logger.info("Returning current time as replacement for failed exif datetime extraction.")
                return datetime.utcnow().strftime(filename_datetime_format)
            else:
                return efix_datetime
        else:
            return datetime.utcnow().strftime(filename_datetime_format)

    def choose_save_file(self) -> Optional[str]:
        exif_info: Dict = get_image_exif_info(self.selected_input_file)
        default_file_name = self.get_default_filename(exif_info["image_datetime"])
        file_handle = filedialog.asksaveasfile(
            initialdir=self.output_folder,
            initialfile=default_file_name,
            title="Select save filename and location"
        )
        if file_handle is not None:
            filename = file_handle.name
            file_handle.__exit__()  # close file so it can be deleted
            Path(filename).unlink()
            return filename

    def load_image(self, image_file):
        img_array_BGR = cv2.imread(image_file)

        # OpenCV uses BGR color, but PIL expects RGB, so we need to convert image's color to RGB order
        img_array_RGB = cv2.cvtColor(img_array_BGR, cv2.COLOR_BGR2RGB)

        return img_array_RGB

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

            # minimal 1 pixel width to avoid error in cv2.resize()
            new_img_width = max(int(img_width * scaling), 1)
            new_img_height = max(int(img_height * scaling), 1)

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
        img_view.canvas_img = img_view.canvas.create_image(x, y, image=img_view.resized_img, anchor=tk.NW)  # TODO: should i delete the previous image on canvas? (not sure I'm using this variable at all)
        # The position is equal to the "padding" (on one side) required to preserve aspect ratio
        img_view.x_padding = x
        img_view.y_padding = y
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
            self.draw_corrected_bounding_box(self.right_view)
            if self.right_view.points:
                ruler_point_map = self.create_ruler_point_mapping(self.right_view)
                self.draw_rulers(self.right_view, ruler_point_map)
                self.draw_ruler_labels(ruler_point_map)

    def resize_callback(self, event):
        self.draw()  # redraw everything to the new canvas display sizes

    def rotate_image_clockwise(self):
        if self.img is not None:
            self.img = cv2.rotate(self.img, cv2.ROTATE_90_CLOCKWISE)
            self.init_bounding_box(self.left_view)  # redraw box since it is hard to rotate points
            self.warp_image()
            self.draw()

    def rotate_image_anticlockwise(self):
        if self.img is not None:
            self.img = cv2.rotate(self.img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            self.init_bounding_box(self.left_view)  # redraw box since it is hard to rotate points
            self.warp_image()
            self.draw()

    def go_to_measurement_window(self):
        already_in_measurement_window = (
            not self.in_box_drawing_window
        )
        if already_in_measurement_window:
            return

        self.in_box_drawing_window = False
        self.left_view.canvas.pack_forget()
        self.right_view.canvas.pack_forget()

        # top menu
        self.rotate_clockwise_button.pack_forget()
        self.rotate_anticlockwise_button.pack_forget()
        self.to_measurement_window_button.pack_forget()
        self.toggle_mini_window_button.pack_forget()
        self.to_box_drawing_window_button.pack(side=tk.LEFT)
        self.save_button.pack(side=tk.LEFT)

        self.right_view.canvas.pack(fill="both", expand=True)

    def go_to_box_drawing_window(self):
        if self.in_box_drawing_window:
            return
        self.in_box_drawing_window = True
        self.left_view.canvas.pack_forget()
        self.right_view.canvas.pack_forget()

        # top menu
        self.to_box_drawing_window_button.pack_forget()
        self.save_button.pack_forget()
        self.rotate_clockwise_button.pack(side=tk.LEFT)
        self.rotate_anticlockwise_button.pack(side=tk.LEFT)
        self.to_measurement_window_button.pack(side=tk.LEFT)
        self.toggle_mini_window_button.pack(side=tk.RIGHT)

        self.left_view.canvas.pack(fill="both", expand=True)
        if self.show_mini_window:
            self.right_view.canvas.place(
                relx=self.mini_window_spec.x,
                rely=self.mini_window_spec.y,
                relwidth=self.mini_window_spec.w,
                relheight=self.mini_window_spec.h,
            )

    def toggle_mini_window(self):
        if self.show_mini_window:
            self.show_mini_window = False
            self.right_view.canvas.place_forget()
            self.toggle_mini_window_button.configure(text="Show")
        else:
            self.show_mini_window = True
            self.right_view.canvas.place(
                relx=self.mini_window_spec.x,
                rely=self.mini_window_spec.y,
                relwidth=self.mini_window_spec.w,
                relheight=self.mini_window_spec.h,
            )
            self.toggle_mini_window_button.configure(text="Hide")

    def run(self):
        self.window.mainloop()

    def draw_point(self, img_view: ImageView, point: Point, color=None):
        w = img_view.resized_width
        h = img_view.resized_height
        if point.color is not None:
            _color = point.color
        if color is not None:
            _color = color
        drawing = img_view.canvas.create_oval(
            img_view.x_padding + int(w * point.x) - self.point_radii,
            img_view.y_padding + int(h * point.y) - self.point_radii,
            img_view.x_padding + int(w * point.x) + self.point_radii,
            img_view.y_padding + int(h * point.y) + self.point_radii,
            # fill=_color,
            fill=self.settings.draw_color
        )
        return drawing

    def init_bounding_box(self, img_view):
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
        col = self.settings.draw_color
        # To get the correct pair of points we need a certain order:
        if img_view.drawn_lines:
            for line in img_view.drawn_lines:
                img_view.canvas.delete(line)
        img_view.drawn_lines = []
        x0 = img_view.x_padding
        y0 = img_view.y_padding
        point_arr = np.stack([np.array([(p.x * img_view.resized_width) + x0, (p.y * img_view.resized_height) + y0]) for p in img_view.points])
        # order to get top_left, top_right, bottom_right, bottom_left:
        ordered_point_arr = _reorder_corner_points(point_arr, "clockwise")
        ps = np.reshape(ordered_point_arr, (4,2))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[0,0], ps[0,1], ps[1,0], ps[1,1], fill=col))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[1,0], ps[1,1], ps[2,0], ps[2,1], fill=col))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[2,0], ps[2,1], ps[3,0], ps[3,1], fill=col))
        img_view.drawn_lines.append(img_view.canvas.create_line(ps[3,0], ps[3,1], ps[0,0], ps[0,1], fill=col))

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
                    fill=col
                )
                img_view.drawn_points.append(canvas_point)

    def draw_corrected_bounding_box(self, img_view):
        # Draw lines
        if self.measure_box_lines:
            for line in self.measure_box_lines:
                img_view.canvas.delete(line)

        col = self.settings.draw_color
        x0 = img_view.x_padding
        y0 = img_view.y_padding
        min_x = self.margin_ratio * img_view.resized_width + x0
        min_y = self.margin_ratio * img_view.resized_height + y0
        max_x = (1 - self.margin_ratio) * img_view.resized_width + x0
        max_y = (1 - self.margin_ratio) * img_view.resized_height + y0
        # draw lines: top_left, top_right, bottom_right, bottom_left:
        self.measure_box_lines = []
        self.measure_box_lines.append(img_view.canvas.create_line(min_x, min_y, min_x, max_y, fill=col))
        self.measure_box_lines.append(img_view.canvas.create_line(min_x, max_y, max_x, max_y, fill=col))
        self.measure_box_lines.append(img_view.canvas.create_line(max_x, max_y, max_x, min_y, fill=col))
        self.measure_box_lines.append(img_view.canvas.create_line(max_x, min_y, min_x, min_y, fill=col))

    # # # # # # # #
    # Draw Rulers #
    # # # # # # # #
    def create_ruler_point_mapping(self, img_view) -> Dict[int, List[Point]]:
        """
        Generate a mapping from ruler_id to points,
        using the point's ruler_id field.
        """
        if img_view.points is None:
            return {}
        rulers: Dict[int, List[Point]] = {}
        for p in img_view.points:
            if p.ruler_id not in rulers:
                rulers[p.ruler_id] = [p]
            else:
                rulers[p.ruler_id].append(p)
        return rulers

    def draw_rulers(self, img_view, ruler_point_map: Dict[int, List[Point]]):
        if img_view.points is None or len(img_view.points) == 0:
            # self.init_ruler(img_view)
            return

        w = img_view.resized_width
        h = img_view.resized_height

        # Before drawing, clear previous drawings:
        clear_drawings(img_view)

        # Draw the ruler's line
        img_view.drawn_lines = []
        img_view.drawn_points = []
        for ruler_points in ruler_point_map.values():
            p1 = ruler_points[0]
            p2 = ruler_points[1]
            # Draw line:
            img_view.drawn_lines.append(img_view.canvas.create_line(
                img_view.x_padding + (w * p1.x),
                img_view.y_padding + (h * p1.y),
                img_view.x_padding + (w * p2.x),
                img_view.y_padding + (h * p2.y),
                width=1,
                # fill=p1.color
                fill=self.settings.draw_color
            ))
            # Draw points:
            drawn_point = img_view.canvas.create_oval(
                img_view.x_padding + int(w * p1.x) - self.point_radii,
                img_view.y_padding + int(h * p1.y) - self.point_radii,
                img_view.x_padding + int(w * p1.x) + self.point_radii,
                img_view.y_padding + int(h * p1.y) + self.point_radii,
                # fill=p1.color
                fill=self.settings.draw_color
            )
            p1.drawing_id = drawn_point
            img_view.drawn_points.append(drawn_point)

            drawn_point = img_view.canvas.create_oval(
                img_view.x_padding + int(w * p2.x) - self.point_radii,
                img_view.y_padding + int(h * p2.y) - self.point_radii,
                img_view.x_padding + int(w * p2.x) + self.point_radii,
                img_view.y_padding + int(h * p2.y) + self.point_radii,
                # fill=p2.color
                fill=self.settings.draw_color
            )
            p2.drawing_id = drawn_point
            img_view.drawn_points.append(drawn_point)

    def find_ruler_label_position(self, ruler_point_map: Dict[int, List[Point]], coordinates_type: str = "canvas"):
        """
        Find where to place ruler labels.
        For simplicity, the label is placed on the side of the ruler closest to the
        image center (this assumes the fish to be laid down along the edge of the box).
        If the line is closest to horizontal, draw label left/right of inner point.
        if the line is closest to vertical, draw label over/under of inner point.

        :coordinates_type: "canvas" | "full_image"
        """
        ruler_label_position = {}
        for i, (ruler_id, ruler_points) in enumerate(ruler_point_map.items()):
            p1 = ruler_points[0]
            p2 = ruler_points[1]
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            vertically_aligned = abs(dy) > abs(dx)  # def: line with slope higher than 45 deg
            label_placement = "unknown"
            if vertically_aligned:
                # The point used for labeling will the the one closest to the image center:
                p1_above_p2 = dy >= 0
                p1_below_p2 = dy < 0
                if abs(p1.y - 0.5) <= abs(p2.y - 0.5):
                    label_point = deepcopy(p1)
                    if p1_above_p2:
                        label_placement = "over"
                    elif p1_below_p2:
                        label_placement = "under"
                else:
                    label_point = deepcopy(p2)
                    if p1_above_p2:
                        label_placement = "under"
                    elif p1_below_p2:
                        label_placement = "over"
            else:  # horizontally aligned
                p1_left_of_p2 = dx >= 0
                p1_right_of_p2 = dx < 0
                if abs(p1.x - 0.5) <= abs(p2.x - 0.5):
                    label_point = deepcopy(p1)
                    if p1_left_of_p2:
                        label_placement = "left"
                    elif p1_right_of_p2:
                        label_placement = "right"
                else:
                    label_point = deepcopy(p2)
                    if p1_left_of_p2:
                        label_placement = "right"
                    elif p1_right_of_p2:
                        label_placement = "left"

            if coordinates_type == "canvas":
                x = label_point.x * self.right_view.resized_width + self.right_view.x_padding
                y = label_point.y * self.right_view.resized_height + self.right_view.y_padding
            elif coordinates_type == "full_image":
                # For drawing rulers and labels when saving the image.
                img_width = self.warped_image.shape[1]
                img_height = self.warped_image.shape[0]
                x = label_point.x * img_width
                y = label_point.y * img_height
            else:
                raise ValueError(f"Received unknown coordinate_type: '{coordinates_type}'")
            if label_placement == "over":
                # TODO: maybe used max(font_size, point_radii) * 3 as distance measure to place text relative to point
                y -= self.point_radii * 3
            elif label_placement == "under":
                y += self.point_radii * 3
            elif label_placement == "left":
                x -= self.point_radii * 3
            elif label_placement == "right":
                x += self.point_radii * 3
            else:
                raise RuntimeError(
                    f"Unable to find 'label_placement' for ruler {ruler_id} (color: {p1.color})"
                )
            ruler_label_position[ruler_id] = (x, y)
        return ruler_label_position

    def read_rulers(self, ruler_point_map: Dict[int, List[Point]]):
        img_to_box_scale_ratio = 1 / (1 - 2 * self.margin_ratio)
        ruler_values = {}
        for ruler_id, ruler_points in ruler_point_map.items():
            p1 = ruler_points[0]
            p2 = ruler_points[1]
            ruler_values[ruler_id] = np.sqrt(
                (img_to_box_scale_ratio * self.settings.measure_box_width * (p1.x - p2.x)) ** 2
                + (img_to_box_scale_ratio * self.settings.measure_box_height * (p1.y - p2.y)) ** 2
            )
        return ruler_values

    def draw_ruler_labels(self, ruler_point_map: Dict[int, List[Point]]):
        """
        draw ruler labels with the measurement
        """

        # Clear existing ruler labels before drawing new ones:
        self.clear_ruler_label_drawings()

        label_positions = self.find_ruler_label_position(ruler_point_map)
        ruler_values = self.read_rulers(ruler_point_map)
        for i, ruler_id in enumerate(ruler_point_map.keys()):
            x, y = label_positions[ruler_id]
            value = ruler_values[ruler_id]
            # color = ruler_point_map[ruler_id][0].color
            color = self.settings.draw_color
            # self.right_view.canvas.create_text(10, 10, text=text, fill="red", anchor=tk.NW, font=(None, 16))
            drawn_label = self.right_view.canvas.create_text(
                x, y, text=f"{i + 1}: {value:.1f} cm", fill=color, anchor=tk.NW, font=(None, self.settings.font_size)
            )
            self.drawn_ruler_labels.append(drawn_label)

    def clear_ruler_label_drawings(self):
        if self.drawn_ruler_labels:
            for label in self.drawn_ruler_labels:
                self.right_view.canvas.delete(label)

    def create_save_image(self):
        """
        when saving the image, draw rulers and ruler labels
        on the original image to keep original resolution.
        """
        ruler_point_map = self.create_ruler_point_mapping(self.right_view)
        label_positions = self.find_ruler_label_position(ruler_point_map, coordinates_type="full_image")
        ruler_values = self.read_rulers(ruler_point_map)
        save_image = deepcopy(self.warped_image)
        img_width = self.warped_image.shape[1]
        img_height = self.warped_image.shape[0]

        scaled_font_size = self.get_original_image_font_size(
            self.settings.font_size
        )
        color = self.settings.draw_color
        rgb = self.hex_color_to_rgb(color)
        for i, (ruler_id, points) in enumerate(ruler_point_map.items()):
            # draw lines
            # color = self.tk_color_to_rgb(points[0].color)
            p0 = (
                int(points[0].x * img_width),
                int(points[0].y * img_height)
            )
            p1 = (
                 int(points[1].x * img_width),
                 int(points[1].y * img_height)
            )
            # rgb = self.hex_color_to_rgb(color)
            cv2.line(save_image, p0, p1, color=rgb, thickness=1, lineType=cv2.LINE_4)

            lbl_x, lbl_y = label_positions[ruler_id]
            value = ruler_values[ruler_id]

            output_ruler_id = i + 1
            cv2.putText(
                img=save_image,
                text=f"{output_ruler_id}: {value:.1f} cm",
                org=(int(lbl_x), int(lbl_y)),
                fontFace=cv2.FONT_HERSHEY_DUPLEX,  # cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=int(np.ceil(scaled_font_size)),
                thickness=int(np.ceil(scaled_font_size)),
                color=rgb,
            )

        # Draw bounding box
        min_x = int(self.margin_ratio * img_width)
        min_y = int(self.margin_ratio * img_height)
        max_x = int((1 - self.margin_ratio) * img_width)
        max_y = int((1 - self.margin_ratio) * img_height)
        # draw lines: top_left, top_right, bottom_right, bottom_left:
        cv2.line(save_image, (min_x, min_y), (min_x, max_y), color=rgb, thickness=1, lineType=cv2.LINE_4)
        cv2.line(save_image, (min_x, max_y), (max_x, max_y), color=rgb, thickness=1, lineType=cv2.LINE_4)
        cv2.line(save_image, (max_x, max_y), (max_x, min_y), color=rgb, thickness=1, lineType=cv2.LINE_4)
        cv2.line(save_image, (max_x, min_y), (min_x, min_y), color=rgb, thickness=1, lineType=cv2.LINE_4)

        save_image = cv2.cvtColor(save_image, cv2.COLOR_RGB2BGR)
        return save_image

    def get_original_image_font_size(self, font_size: int):
        """
            Get the size of the font to be drawn on the original image
            from the font size drawn on the screen (on resized image)
        """
        # get font size relative to resized image
        resized_height = self.right_view.resized_height
        img_relative_font_size = font_size / resized_height  # both are in pixels

        # Get the number of pixels this represents on the original image
        # scaled_font_size = img_relative_font_size * len(self.img)
        scaled_font_size = img_relative_font_size * len(self.warped_image)

        # Correct any differences in font size between tkinter and cv2
        corrected_font_size = (
                scaled_font_size
                * self.get_font_scale_correction_by_font_size_diff(font_size)
        )
        return corrected_font_size

    @staticmethod
    def get_font_scale_correction_by_font_size_diff(font_size: int, cv2_font=cv2.FONT_HERSHEY_DUPLEX):
        """
        Get correction for the size of a font relative to the
        size of the cv2 font with fontScale=1, thickness=1
        """
        cv2_text_height = cv2.getTextSize(text="A", fontFace=cv2_font, fontScale=font_size, thickness=font_size)[0][1]
        return font_size / cv2_text_height

    @staticmethod
    def hex_color_to_rgb(hex: str) -> Tuple[int, int, int]:
        _hex = hex.lstrip("#")
        r = int(_hex[0:2], 16)
        g = int(_hex[2:4], 16)
        b = int(_hex[4:6], 16)
        return r, g, b

    def left_click_callback(self, img_view: ImageView, create_rulers_on_click: bool, bound_to: str, event):
        if img_view.canvas_img is not None:
            x = event.x
            y = event.y
            x, y = self.restrict_position(x, y, img_view, bound_to)

            # Hack: tkinter doesn't allow to separate drawn canvas types.
            #       solution: delete drawn text when clicking points:
            for label in self.drawn_ruler_labels:
                img_view.canvas.delete(label)

            drawn_points = img_view.drawn_points if img_view.drawn_points is not None else []
            closest = img_view.canvas.find_closest(x, y, halo=10, start=drawn_points)
            selected_point_id = closest[0]
            if selected_point_id in drawn_points:
                # create reference to point in img_view.points to easily adjust its position:
                # Find the clicked point
                selected_point_idx = img_view.drawn_points.index(selected_point_id)
                self.dragged_point = img_view.points[selected_point_idx]
                # Update dragged_point with click position (might be slightly off original position):
                self.dragged_point.x = (x - img_view.x_padding) / img_view.resized_width
                self.dragged_point.y = (y - img_view.y_padding) / img_view.resized_height
                # First part of animation: removing it from original position to a position centered on mouse:
                img_view.drawn_points.remove(selected_point_id)
                self.draw()
            elif create_rulers_on_click:
                if self.new_ruler_start_point is None:
                    # Add the released point:
                    rel_x = (x - img_view.x_padding) / img_view.resized_width
                    rel_y = (y - img_view.y_padding) / img_view.resized_height
                    self.new_ruler_start_point = Point(
                        # rel_x, rel_y, self.num_rulers_created + 1, self.settings.colors[(self.num_rulers_created + 1) % len(self.settings.colors)]
                        rel_x, rel_y, self.num_rulers_created + 1, self.settings.draw_color
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
                            # rel_x, rel_y, self.num_rulers_created, self.settings.colors[self.num_rulers_created % len(self.settings.colors)]
                            rel_x, rel_y, self.num_rulers_created, self.settings.draw_color
                        )
                    ])
                    img_view.canvas.delete(self.new_ruler_start_point.drawing_id)
                    img_view.canvas.delete(self.drawn_ruler_end)
                    img_view.canvas.delete(self.drawn_ruler_line)
                    self.drawn_ruler_end = None
                    self.drawn_ruler_line = None
                    self.new_ruler_start_point = None
                    self.draw()

    def drag_callback(self, img_view: ImageView, bound_to: str, event):
        if self.img is None:
            return

        x = event.x
        y = event.y
        # make sure point isn't dragged outside canvas
        x, y = self.restrict_position(x, y, img_view, bound_to)

        if self.dragged_point is not None:
            img_view.canvas.configure(cursor="none")
            img_view.canvas.delete(self.dragged_point.drawing_id)
            # Update dragged_point with click position to moving mouse:
            self.dragged_point.x = (x - img_view.x_padding) / img_view.resized_width
            self.dragged_point.y = (y - img_view.y_padding) / img_view.resized_height
            self.draw()

    def release_callback(self, img_view: ImageView, bound_to: str, event):
        """
        bound_to="image": bound rulers to be inside image
        bound_to="box": bound rules to be inside the defined drawing box
        """

        if self.dragged_point is not None:
            img_view.canvas.configure(cursor="arrow")

            x = event.x
            y = event.y
            # make sure point isn't dragged outside canvas
            x, y = self.restrict_position(x, y, img_view, bound_to)

            img_view.canvas.delete(self.dragged_point.drawing_id)
            # Update point with the release position:
            self.dragged_point.x = (x - img_view.x_padding) / img_view.resized_width
            self.dragged_point.y = (y - img_view.y_padding) / img_view.resized_height
            self.dragged_point = None
            self.warp_image()
            self.draw()

    def move_callback(self, img_view: ImageView, bound_to: str, event):
        if self.new_ruler_start_point is not None:
            x = event.x
            y = event.y
            # make sure point isn't dragged outside canvas or the drawn box
            x, y = self.restrict_position(x, y, img_view, bound_to)

            img_view.canvas.delete(self.new_ruler_start_point.drawing_id)
            start_x = self.new_ruler_start_point.x * img_view.resized_width + img_view.x_padding
            start_y = self.new_ruler_start_point.y * img_view.resized_height + img_view.y_padding
            self.new_ruler_start_point.drawing_id = img_view.canvas.create_oval(
                start_x - self.point_radii,
                start_y - self.point_radii,
                start_x + self.point_radii,
                start_y + self.point_radii,
                # fill=self.new_ruler_start_point.color
                fill=self.settings.draw_color
            )
            if self.drawn_ruler_end is not None:
                img_view.canvas.delete(self.drawn_ruler_end)
            self.drawn_ruler_end = img_view.canvas.create_oval(
                x - self.point_radii,
                y - self.point_radii,
                x + self.point_radii,
                y + self.point_radii,
                # fill=self.new_ruler_start_point.color
                fill=self.settings.draw_color
            )
            if self.drawn_ruler_line is not None:
                img_view.canvas.delete(self.drawn_ruler_line)
            self.drawn_ruler_line = img_view.canvas.create_line(
                start_x,
                start_y,
                x,
                y,
                # fill=self.new_ruler_start_point.color
                fill=self.settings.draw_color
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
            # Hack: tkinter doesn't allow to separate drawn canvas types.
            #       solution: delete drawn text when clicking points:
            for label in self.drawn_ruler_labels:
                img_view.canvas.delete(label)

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

    def restrict_position(self, x, y, img_view: ImageView, bound_to: str = "image"):
        if bound_to == "image":
            x = max(img_view.x_padding, x)
            y = max(img_view.y_padding, y)
            x = min(img_view.canvas.winfo_width() - img_view.x_padding, x)
            y = min(img_view.canvas.winfo_height() - img_view.y_padding, y)
        elif bound_to == "box":
            min_x = self.margin_ratio * img_view.resized_width + img_view.x_padding
            min_y = self.margin_ratio * img_view.resized_height + img_view.y_padding
            max_x = (1 - self.margin_ratio) * img_view.resized_width + img_view.x_padding
            max_y = (1 - self.margin_ratio) * img_view.resized_height + img_view.y_padding
            x = max(min_x, x)
            y = max(min_y, y)
            x = min(max_x, x)
            y = min(max_y, y)
        else:
            raise ValueError("param bound_to must be set to 'image' or 'box'.")
        return x, y

    def warp_image(self):
        corners_ndarray = self.points_to_ndarray(self.left_view.points)
        self.warped_image = warp_image(self.img, corners_ndarray, self.margin_ratio)
        # self.warp_activated = True

    def points_to_ndarray(self, points: List[Point]):
        img_width = self.img.shape[1]
        img_height = self.img.shape[0]
        return np.stack([np.array([p.x * img_width, p.y * img_height]) for p in points])

    @staticmethod
    def valid_filename(filename_stem: str):
        alphanum_underscore_dash = "^[a-zA-Z0-9_-]+$"
        matched = re.match(alphanum_underscore_dash, filename_stem)
        return bool(matched)

    def save_callback(self):
        if self.warped_image is None:
            return
        try:
            selected_save_path = self.choose_save_file()
            if selected_save_path is not None:
                save_path = Path(selected_save_path)
                if not self.valid_filename(save_path.stem):
                    messagebox.showerror(
                        "Invalid filename",
                        "Only alphanumeric characters, dashes and underscores are allowed in the filenames"
                        " (allowed: a-z, A-Z, 0-9, -, _)")
                    return
                self.output_folder = save_path.parent
                img_path = save_path.parent / f"P-{save_path.stem}.jpg"
                data_path = save_path.parent / f"D-{save_path.stem}.xlsx"
                existing_file_warnings = []
                if img_path.exists():
                    existing_file_warnings.append(
                        f"image file {img_path.name}"
                    )
                if data_path.exists():
                    existing_file_warnings.append(
                        f"excel file {data_path.name}"
                    )
                if existing_file_warnings:
                    existing_files = " and ".join(existing_file_warnings)
                    answered_yes = messagebox.askyesno(
                        f"Overwrite existing file(s)?",
                        f"The {existing_files} already exists."
                        f" Do you want to overwrite {'it' if len(existing_file_warnings) == 1 else 'them'}?"
                    )
                    if not answered_yes:
                        return
                self.save_image(path=img_path)
                self.save_data(data_path=data_path, img_path=img_path)
        except Exception as e:
            logger.error("Exception encountered while trying to save image and data files.")
            logger.exception(e)
        else:
            self.saved_points = deepcopy(self.right_view.points)

    def save_data(self, data_path: Path, img_path: Path):
        img_info = get_image_exif_info(self.selected_input_file)

        # Read ruler info (the lengths extracted from the drawn rulers):
        ruler_info = []
        ruler_point_map = self.create_ruler_point_mapping(self.right_view)
        ruler_values = self.read_rulers(ruler_point_map)
        for i, ruler_id in enumerate(ruler_point_map.keys()):
            ruler_info.append(dict(
                measurement_id=i+1,
                length_cm=ruler_values[ruler_id],
            ))

        # create table with drawn measurements:
        df = DataFrame(ruler_info)

        # add box dimensions
        df.insert(0, "box_width_cm", self.settings.measure_box_width)
        df.insert(1, "box_height_cm", self.settings.measure_box_height)

        # insert image information and image name (so data can be mapped back to file)
        # (using insert to insert image information at the front)
        for i, (field, value) in enumerate(img_info.items()):
            df.insert(i, field, value)

        df.insert(0, "image_file", img_path.name)

        # Save excel file with the same name as image filename:
        df.to_excel(str(data_path), index=False, float_format="%.1f")
        if not data_path.exists():
            raise WriteResultFileError(
                f"No output excel file produced for {data_path}."
            )

    def save_image(self, path: Path):
        save_image = self.create_save_image()
        cv2.imwrite(filename=str(path), img=save_image)
        if not path.exists():
            raise WriteResultFileError(
                f"No output image produced for {path}."
            )


def clear_drawings(img_view: ImageView):
    # delete existing lines:
    if img_view.drawn_lines:
        for line in img_view.drawn_lines:
            img_view.canvas.delete(line)
    # Delete drawn points:
    if img_view.drawn_points:
        for drawn_corner in img_view.drawn_points:
            img_view.canvas.delete(drawn_corner)


def warp_image(img, corner_points, rel_margin: float):
    corner_points = _reorder_corner_points(corner_points, "anti-clockwise")  # getPerspective expects anti-clockwise
    img_width = img.shape[1]
    img_height = img.shape[0]
    old_corner_points = np.float32(corner_points)
    # new_corner_points = np.float32([[0, 0],
    #                                 [img_height, 0],
    #                                 [img_width, img_height],
    #                                 [0, img_width]])
    new_corner_points = np.float32([
        [rel_margin * img_width, rel_margin * img_height],
        [rel_margin * img_width, (1 - rel_margin) * img_height],
        [(1 - rel_margin) * img_width, (1 - rel_margin) * img_height],
        [(1 - rel_margin) * img_width, rel_margin * img_height]])
    matrix = cv2.getPerspectiveTransform(old_corner_points, new_corner_points)
    img_warped = cv2.warpPerspective(img, matrix, (img_width, img_height))
    # cv2 warpPerspective seems to output the same dimensions as the input image,
    # potentially skewing the image if the drawn corners are of a different aspect
    # ratio than the original image.
    # --> Add an additional transformation according to the drawn bounding box
    #     aspect ratio in order to prevent skew in the original image
    # TODO: see if there is a better way to do this (input params of warpPerspective?)
    p1 = corner_points[0, 0, :]  # (points ordered anti-clockwise, starting from upper left)
    p2 = corner_points[1, 0, :]
    p3 = corner_points[2, 0, :]
    p4 = corner_points[3, 0, :]
    left_height = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    right_height = np.sqrt((p3[0] - p4[0])**2 + (p3[1] - p4[1])**2)
    top_width = np.sqrt((p1[0] - p4[0])**2 + (p1[1] - p4[1])**2)
    bottom_width = np.sqrt((p2[0] - p3[0])**2 + (p2[1] - p3[1])**2)

    box_height = int(np.mean([left_height, right_height]))
    box_width = int(np.mean([top_width, bottom_width]))
    box_aspect_ratio = box_width / box_height
    if box_aspect_ratio >= 1:
        new_img_width = img_width
        new_img_height = max(int(img_width / box_aspect_ratio), 1)  # avoid height=0
    else:
        new_img_width = max(int(box_aspect_ratio * img_height), 1)
        new_img_height = img_height
    img_warped_unskewed = cv2.resize(img_warped, (new_img_width, new_img_height), interpolation=cv2.INTER_AREA)
    return img_warped_unskewed


# reorder (for correct input to warping function
def _reorder_corner_points(corner_points, order="anti-clockwise"):
    """
    Identify point position and order them accorading to the specified
    order starting from the upper left corner
    order: "anti-clockwise" | "clockwise"
    """
    # TODO: try to find a more robust way of categorising the corners
    #       motivation: the box isn't drawn for oddly positioned points
    #                   breaking with the non-robust method below
    corner_points = corner_points.reshape((4, 2))
    reordered_points = np.zeros((4, 1, 2), np.int32)

    pair_sum = corner_points.sum(1)
    pair_diff = -np.diff(corner_points, axis=1)

    # sort points based on angle:
    # (starting from upper_left to get correct orientation when warping image)
    upper_left = corner_points[np.argmin(pair_sum)]
    upper_left_angle = 0 if order == "clockwise" else 2 * np.pi
    angles = [
        np.arctan2((p[1] - upper_left[1]), (p[0] - upper_left[0])) + np.pi
        if np.any(p != upper_left) else upper_left_angle
        for p in corner_points
    ]
    if order == "anti-clockwise":
        reverse = True
    elif order == "clockwise":
        reverse = False
    else:
        raise ValueError(f"Unknown order={repr(order)}. Allowed values: 'clockwise' or 'anti-clockwise' (default)")
    reordered_points = np.stack([[p] for (_, p) in sorted(zip(angles, corner_points), key=lambda x: x[0], reverse=reverse)])
    return reordered_points


def get_image_exif_info(path: str) -> Dict:
    def get_degrees(angles: Tuple[float, float, float]) -> float:
        return angles[0] + (angles[1] / 60) + (angles[2] / 3600)
    def format_degrees(angles: Tuple[float, float, float]) -> str:
        return f"{int(angles[0])}\u00B0{int(angles[1])}'{angles[2]}\""
    # def get_angles(degrees: float) -> Tuple[float, float, float]:
    #     a0 = degrees // 1
    #     r0 = (degrees % 1)
    #     a1 = r0 * 60 // 1
    #     r1 = r0 * 60 % 1
    #     a2 = r1 * 60
    #     return a0, a1, a2
    extracted_info = {
        "image_datetime": "",
        "image_gps_latitude": "",
        "image_gps_longitude": "",
        # "image_gps_latitude_text": "",
        # "image_gps_longitude_text": ""
    }
    with open(path, "rb") as f:
        exif_img = exif.Image(f)
        if exif_img.has_exif:
            if hasattr(exif_img, "datetime"):
                extracted_info["image_datetime"] = exif_img.datetime
            if hasattr(exif_img, "gps_latitude"):
                extracted_info["image_gps_latitude"] = f"{get_degrees(exif_img.gps_latitude):.5f}"
                # extracted_info["image_gps_latitude_text"] = format_degrees(exif_img.gps_latitude)
            if hasattr(exif_img, "gps_longitude"):
                extracted_info["image_gps_longitude"] = f"{get_degrees(exif_img.gps_longitude):.5f}"
                # extracted_info["image_gps_longitude_text"] = format_degrees(exif_img.gps_longitude)
    # lo = exif_img.gps_latitude
    # lo_s = format_degrees(lo)
    # lo_f = get_degrees(lo)
    # lo_2 = get_angles(lo_f)
    #
    # la = exif_img.gps_longitude
    # la_s = format_degrees(la)
    # la_f = get_degrees(la)
    # la_2 = get_angles(la_f)
    return extracted_info


if __name__ == "__main__":
    fm = FishMesh()
    fm.run()
