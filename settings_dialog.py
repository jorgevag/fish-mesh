import tkinter as tk
from typing import Dict, Optional, Any, Union
from tkinter import simpledialog, colorchooser, messagebox
import json
from functools import partial

from dataclasses import dataclass, fields, asdict
from settings import (
    Settings, SettingsError, DEFAULT_SETTINGS_PATH, SETTING_DESCRIPTIONS
)


@dataclass
class SettingsDialogField:
    label: Optional[tk.Label] = None
    entry: Optional[Union[tk.Entry, tk.Button]] = None
    type: Optional[type] = None
    value: Optional[Any] = None


class SettingsDialog(tk.simpledialog.Dialog):
    def __init__(self, parent, title, field_width=25, settings: Optional[Settings] = None):
        self.fields: Dict[str, SettingsDialogField] = {}
        max_width_required = 0
        if settings is not None:
            self.selected_draw_color = settings.draw_color
            self.show_mini_window = settings.show_mini_window_on_start
            for field in fields(settings):
                self.fields[field.name] = SettingsDialogField(
                    value=getattr(settings, field.name),
                    type=field.type
                )
                max_width_required = max(
                    max_width_required,
                    len(var_to_text(field.name))
                )
        else:  # default settings values from class
            self.selected_draw_color = Settings.draw_color
            self.show_mini_window = Settings.show_mini_window_on_start
            for field in fields(Settings):
                self.fields[field.name] = SettingsDialogField(
                    value=getattr(Settings, field.name),
                    type=field.type
                )
                max_width_required = max(
                    max_width_required,
                    len(var_to_text(field.name))
                )
        self.field_width = max_width_required
        super().__init__(parent, title)

    def body(self, frame):
        for row, field in enumerate(self.fields):
            # print(field.name, field.type, getattr(FishMeshSettings, field.name))
            self.fields[field].label = tk.Label(
                frame,
                width=self.field_width,
                text=var_to_text(field) + ": ",
                anchor="e",
                justify=tk.RIGHT,
            )
            self.fields[field].label.grid(row=row, column=0)
            self.fields[field].label.bind("<Enter>", partial(self.tooltip_enter, field))
            self.fields[field].label.bind("<Leave>", self.tooltip_leave)
            if field == "draw_color":
                self.fields[field].entry = tk.Button(
                    frame,
                    background=self.fields[field].value,
                    text="",
                    command=self.choose_color,
                )
                self.fields[field].entry.grid(row=row, column=1)
            elif field == "show_mini_window_on_start":
                self.fields[field].entry = tk.Button(
                    frame,
                    text="Yes" if self.fields[field].value else "No",
                    command=self.toggle_show_mini_window,
                )
                self.fields[field].entry.grid(row=row, column=1)
            else:
                self.fields[field].entry = tk.Entry(frame)#, width=self.field_width)
                self.fields[field].entry.insert(tk.END, self.fields[field].value)  # show existing value
                self.fields[field].entry.grid(row=row, column=1)

        # self.tooltip_title = tk.Label(
        #     frame,
        #     text="",
        #     font=('Helvetica', 12, 'bold'),
        #     anchor="nw",
        #     justify=tk.LEFT
        # )
        # self.tooltip_title.grid(row=1, column=3)
        self.tooltip = tk.Label(
            frame,
            text="",
            anchor="nw",
            justify=tk.LEFT
        )
        self.tooltip.grid(row=0, column=3, rowspan=len(self.fields) - 1)

        return frame

    def buttonbox(self):
        self.apply_button = tk.Button(self, text='Apply', width=5, command=self.apply_pressed)
        self.apply_button.pack(side="left")

        self.save_settings_button = tk.Button(
            self,
            text="Apply and save for future sessions",
            command=self.save_settings,
        )
        self.save_settings_button.pack(side="left")

        cancel_button = tk.Button(self, text='Cancel', width=5, command=self.destroy)
        cancel_button.pack(side="right")
        self.bind("<Return>", lambda event: self.apply_pressed)
        self.bind("<Escape>", lambda event: self.destroy)

    def tooltip_enter(self, field: str, event):
        if field in SETTING_DESCRIPTIONS:
            # self.tooltip_title.configure(text=var_to_text(field))
            self.tooltip.configure(text=SETTING_DESCRIPTIONS[field])

    def tooltip_leave(self, event):
        # self.tooltip_title.configure(text="")
        self.tooltip.configure(text="")

    def apply_pressed(self):
        field_errors = self.validate_fields()
        if field_errors:
            messagebox.showerror("Incorrect field input", "\n".join(field_errors))
        else:
            self.read_entries()
            self.destroy()

    def choose_color(self):
        rgb, hex = colorchooser.askcolor(title="Choose color")
        if hex is not None:
            self.selected_draw_color = hex
        self.fields["draw_color"].entry.configure(text="", background=hex)

    def toggle_show_mini_window(self):
        self.show_mini_window = not(self.fields["show_mini_window_on_start"].value)
        self.fields["show_mini_window_on_start"].entry.configure(
            text=("Yes" if self.show_mini_window else "No")
        )

    def read_entries(self):
        for field in self.fields:
            if isinstance(self.fields[field].entry, tk.Entry):
                self.fields[field].value = self.fields[field].entry.get()
            elif field == "draw_color":
                self.fields["draw_color"].value = self.selected_draw_color
            elif field == "show_mini_window_on_start":
                self.fields["show_mini_window_on_start"].value = self.show_mini_window
            else:
                TypeError(
                    "Unknown type for 'entry' property to receive"
                    " user input value in SettingsDialog."
                    " These should be tk.Entry except for draw_color, which"
                    " is handled differently due to colorchooser.askcolor()."
                    " Make sure, new special cases of entries are handled"
                    " appropriately."
                )

    def validate_fields(self):
        field_errors = []
        for field_name, field in self.fields.items():
            if isinstance(field.entry, tk.Entry):
                value = field.entry.get()
                if field.type is None:
                    pass
                try:
                    field.type(value)
                except ValueError:
                    field_errors.append(
                        f"field '{var_to_text(field_name)}': '{value}' "
                        f"is not of type '{field.type.__name__}'"
                    )
        return field_errors

    def save_settings(self):
        self.read_entries()
        settings = self.get_settings()
        try:
            settings.validate()
        except SettingsError as e:
            messagebox.showerror(f"Cannot save invalid settings", str(e))
        else:
            self.destroy()
            if DEFAULT_SETTINGS_PATH.exists():
                answered_yes = messagebox.askyesno(
                    "Settings file already exists",
                    f"Settings file {DEFAULT_SETTINGS_PATH} already exists. Would you like to overwrite it?"
                )
                if not answered_yes:
                    return
            with open(DEFAULT_SETTINGS_PATH, "w") as f:
                f.write(json.dumps(asdict(settings), indent=4))

    def get_settings(self) -> Settings:
        return Settings(**{
            name: field.type(field.value) for name, field in self.fields.items()
        })


def var_to_text(name: str):
    """ Capitalize and replace underscores with spaces of settings variable names """
    return " ".join(name.capitalize().split("_"))


if __name__ == "__main__":

    def show_settings():
        dialog = SettingsDialog(title="Settings", parent=window)
        print(dialog.get_settings())
        return dialog.get_settings()

    window = tk.Tk()
    window.title('Dialog')
    settings_button = tk.Button(window, text='Settings', width=25, command=show_settings)
    settings_button.pack()
    window.mainloop()
