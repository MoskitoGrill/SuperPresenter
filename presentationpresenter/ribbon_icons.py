"""Small, font-independent command symbols; scaled for Tk's display density."""
from PIL import Image, ImageDraw, ImageTk


def command_icon(root, name, color='#202020'):
    size = max(18, round(20 * float(root.tk.call('tk', 'scaling')) / (96 / 72)))
    image = Image.new('RGBA', (80, 80))
    pen = ImageDraw.Draw(image)
    if name == 'bucket':
        pen.line([(19, 31), (38, 12), (62, 36), (41, 58), (19, 36), (19, 31)], fill=color, width=5)
        pen.line([(28, 22), (18, 12), (12, 18), (32, 40)], fill=color, width=4)
        pen.line([(43, 55), (64, 35)], fill=color, width=5)
        pen.polygon([(65, 43), (57, 59), (59, 66), (65, 69), (71, 65), (72, 59)], fill=color)
        pen.line([(12, 75), (73, 75)], fill=color, width=5)
    elif name == 'bullets':
        for y in (17, 39, 61):
            pen.ellipse((7, y-4, 15, y+4), fill=color)
            pen.line([(26, y), (72, y)], fill=color, width=5)
    else:
        raise ValueError(name)
    return ImageTk.PhotoImage(image.resize((size, size), Image.Resampling.LANCZOS), master=root)
