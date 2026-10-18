"""Fixed-size navigation centered independently of the Play button."""
from tkinter import font as tkfont


class NavigationLayout:
    def __init__(self, frame, play, group, buttons, counter, family):
        self.button_font = tkfont.Font(root=frame, family=family, size=13, weight='bold')
        self.counter_font = tkfont.Font(root=frame, family=family, size=13)
        for button in (*buttons, play):
            button.configure(font=self.button_font, width=4, height=1, relief='raised',
                             borderwidth=2, padx=3, pady=1)
        counter.configure(font=self.counter_font, width=11, height=1, borderwidth=0, padx=1, pady=1)
        # Use actual widget requests: font linespace omits native button insets.
        content_height = max(*(button.winfo_reqheight() for button in buttons),
                             counter.winfo_reqheight(), play.winfo_reqheight())
        frame.configure(height=content_height+16)
        self.normal_height = content_height+16
        frame.pack_propagate(False)
        group.place(relx=.5, y=8, anchor='n')
        play.pack_forget()
        # Reserve enough preview width to keep the centered group clear of Play.
        # Window resizing never changes fonts or control dimensions.
        group_width = sum(button.winfo_reqwidth()+4 for button in buttons)+counter.winfo_reqwidth()+8
        self.minimum_width = group_width+2*(play.winfo_reqwidth()+12)
        # Halfway between the preview's left edge and the first arrow.
        play.place(relx=.25, x=-group_width/4, y=8, anchor='n')
        self.play = play
        self.play_position = play.place_info()
        self.buttons = buttons
        self.children = [(child, child.pack_info()) for child in group.winfo_children()]

    def set_visibility(self, show_play, show_arrows):
        if show_play:
            self.play.place(**self.play_position)
        else:
            self.play.place_forget()
        for child, options in self.children:
            child.pack_forget()
            if show_arrows:
                child.pack(**options)
