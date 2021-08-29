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

        self.file_explorer_button = Button(
            self.window,
            text="Browse Files",
            command=self.select_file,
        )

        self.selected_file = tk.StringVar()

        # Create a File Explorer label
        self.label_file_explorer = Label(
            self.window,
            text="No file selected",
            # width=100,
            # height=4,
            # fg="blue"
        )

        self.load_image_button = Button(
            self.window,
            text="Load Image",
            command=self.load_image,
        )

        self.exit_button = Button(
            self.window,
            text="Exit",
            command=exit
        )

        self.exit_button = ttk.Button(self.window, text="Quit")
        #self.exit_button.grid(row=2, column=0)
        self.exit_button['command'] = self.window.destroy


        # Place components:
        #self.selected_file.grid(row=0, column=0)
        self.file_explorer_button.grid(column=1, row=1)
        self.label_file_explorer.grid(column=1, row=2)
        self.load_image_button.grid(column=1, row=3)
        self.canvas = Canvas(self.window, width=600, height=600)
        #self.canvas.pack()
        self.canvas.grid(column=1, row=4)
        self.exit_button.grid(column=1, row=5)


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

        # # Canvas to draw image on
        # # pil_img = Image.open(filename)
        # pil_img = cv2.imread(filename)
        #
        # # Trying to rescale image to fit into display
        # # (the displayed image only showed a subppart of the total photo.. but maybe this can be
        # #  avoided altogether by using some other method...)
        # output_size = 4000
        # # w = pil_img.size[0]
        # # h = pil_img.size[1]
        # w = len(pil_img[0])
        # h = len(pil_img)
        # if w > h:
        #     scaling =  float(output_size)
        # else:
        #     scaling =  float(output_size) / h
        # new_w = int(w * scaling)
        # new_h = int(h * scaling)
        # # resized = pil_img.copy().resize((new_w, new_h), Image.ANTIALIAS)
        # resized = cv2.resize(pil_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        # #cv2.imshow("resized image", resized)
        #
        # # pil_img.resize((new_w, new_h))
        # img_resized = Image.fromarray(resized)
        # img = ImageTk.PhotoImage(img_resized)
        # #img = ImageTk.PhotoImage(cv2.imread(self.selected_file.get()))
        # self.canvas.create_image(output_size, output_size, image=img)

    def load_image(self):
        img_array_BGR = cv2.imread(self.selected_file.get())

        # OpenCV uses BGR color, but PIL expects RGB, so we need to convert image's color to RGB order
        img_array_RGB = cv2.cvtColor(img_array_BGR, cv2.COLOR_BGR2RGB)

        # https://stackoverflow.com/questions/19838972/how-to-update-an-image-on-a-canvas/19842646
        img = Image.fromarray(img_array_RGB)
        photo_img = ImageTk.PhotoImage(img)
        self.image_on_canvas = self.canvas.create_image(0, 0, image=photo_img)
        #self.canvas.configure(photo_img, height=photo_img.height(), width=photo_img.width())
        self.canvas.itemconfig(self.image_on_canvas, image=photo_img)
        self.canvas.image = photo_img

    def resize_image(self):
        # Maybe we also need to resize image to the window size:
        # https://stackoverflow.com/questions/24061099/tkinter-resize-background-image-to-window-size
        pass

class Dog:
    def __init__(self):
        self.age = 10

    def growing_older(self, year_passed):
        self.age += year_passed

a_dog = Dog()
a_dog.growing_older(2)
a_dog.age

if __name__ == "__main__":

    # Create the entire GUI program
    program = FileExplorerProgram()

    # Start the GUI event loop
    program.window.mainloop()
