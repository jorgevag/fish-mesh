# Sources:
# https://www.geeksforgeeks.org/file-explorer-in-python-using-tkinter/
# Python program to create a file explorer in Tkinter

# TODO: try to follow this guide to show the image: https://www.pyimagesearch.com/2016/05/23/opencv-with-tkinter/

from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import cv2.cv2 as cv2
from pathlib import Path

import tkinter as tk
from tkinter import ttk


class FileExplorerProgram:
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
            command=self.select_file,
        )
        self.file_explorer_button.pack()

        self.selected_file = tk.StringVar()

        self.label_file_explorer = Label(
            self.window,
            text="No file selected",
            bg="white",
        )
        self.label_file_explorer.pack()

        self.load_image_button = Button(
            self.window,
            text="Load Image",
            command=self.load_image,
            bg="white",
        )
        self.load_image_button.pack()
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
        # self.canvas.configure(photo_img, height=photo_img.height(), width=photo_img.width())
        self.canvas.itemconfig(self.image_on_canvas, image=self.resized_img)
        self.canvas.image = self.resized_img
        self.canvas.configure(bg="black")

    def resize_callback(self, event):
        self.draw_image()

    def rotate_image_clockwise(self):
        self.img_cv2 = cv2.rotate(self.img_cv2, cv2.ROTATE_90_CLOCKWISE)
        self.draw_image()

    def rotate_image_anticlockwise(self):
        self.img_cv2 = cv2.rotate(self.img_cv2, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.draw_image()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    program = FileExplorerProgram()
    program.run()
