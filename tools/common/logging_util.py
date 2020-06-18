"""

Utilities for logging information to avoid depending on the debug console

"""

import adsk.core
import adsk.fusion
import time


class LoggingUtil:

    def __init__(self):
        app = adsk.core.Application.get()
        ui = app.userInterface
        self.text_palette = ui.palettes.itemById('TextCommands')

        # Make sure the palette is visible.
        if not self.text_palette.isVisible:
            self.text_palette.isVisible = True

    def log_text(self, txt_str=""):
        print(txt_str)
        self.text_palette.writeText(txt_str)
        adsk.doEvents()

    def log_time(self, txt_str=""):
        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        time_txt_str = f"{time_stamp} {txt_str}"
        print(time_txt_str)
        self.text_palette.writeText(time_txt_str)
        adsk.doEvents()
