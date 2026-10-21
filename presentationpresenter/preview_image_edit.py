"""Opt-in direct manipulation in the main preview; commit only on release."""
from dataclasses import replace
from .domain import ImageSection
from .editor import editable_section
from .layout import Rect, PlacedImage, geometry, paginate, LayoutError
from .composition import constrain, with_image_box, camera_core


def resized_box(box, corner, dx, dy, config):
    """Keep aspect and opposite corner fixed, including at output/camera limits."""
    left, top = corner[0] == 'w', corner[1] == 'n'
    ratio = box.height / box.width
    width = max(4, box.width + ((-dx if left else dx) + ratio * (-dy if top else dy)) / (1+ratio*ratio))
    ax, ay = (box.x+box.width if left else box.x), (box.y+box.height if top else box.y)
    w, h, camera, _ = geometry(config)
    width = min(width, ax if left else w-ax, (ay if top else h-ay)/ratio)

    def candidate(size):
        return Rect(ax-size if left else ax, ay-size*ratio if top else ay, size, size*ratio)

    proposed = candidate(width)
    core = camera_core(camera) if camera else None
    if core and proposed.intersects(core):
        low, high = min(4, width), width
        for _ in range(32):
            middle = (low+high)/2
            trial = candidate(middle)
            if not trial.intersects(core):
                low = middle
            else:
                high = middle
        proposed = candidate(low)
    return proposed


class PreviewImageEdit:
    def __init__(self, owner):
        self.owner = owner
        self.enabled = False
        self.selected = None
        self.drag = None
        self.ghost = None
        canvas = owner.preview
        canvas.bind('<Button-1>', self.press)
        canvas.bind('<B1-Motion>', self.motion)
        canvas.bind('<ButtonRelease-1>', self.release)
        canvas.bind('<Motion>', self.hover)
        canvas.bind('<Escape>', self.escape)
        self.update_button()

    @property
    def active(self):
        return self.enabled or self.owner.settings.direct_image_edit

    def update_button(self):
        self.owner.image_edit_button.configure(
            state='disabled' if self.owner.settings.direct_image_edit else 'normal',
            relief='sunken' if self.active else 'raised')

    def preference_changed(self):
        self.drag = None
        self.ghost = None
        self.selected = None
        self.enabled = False
        if self.active and self.owner.viewing_live():
            self.owner.toggle_draft_preview()
        self.update_button()
        self.owner.render_preview()
        self.owner.status.set('Obrázky lze upravovat přímo v rozpracovaném náhledu.' if self.active
                              else 'Úpravy obrázků se zapínají tlačítkem Upravit obrázky.')

    def toggle(self):
        if self.owner.settings.direct_image_edit:
            return
        self.owner.finish_editing()
        self.enabled = not self.enabled
        self.drag = None
        if self.enabled and self.owner.viewing_live():
            self.owner.toggle_draft_preview()
        self.update_button()
        self.owner.status.set('Úprava obrázků: tažením přesunete, rohem změníte velikost. Escape zruší tah.'
                              if self.enabled else 'Úprava obrázků vypnuta.')
        self.owner.render_preview()

    def context(self):
        o = self.owner
        if not self.active or o.viewing_live() or not o.plan or not o.plan.slides or o.plan.source != o.document:
            return None
        slide = o.plan.slides[o.current]
        if slide.black:
            return None
        section = next((s for s in o.document.sections if s.id == slide.section_id), None)
        layout = getattr(slide, o.output.get())
        if not section or not layout:
            return None
        images = layout.images
        if isinstance(section, ImageSection) and layout.image_box:
            images = (PlacedImage(section.id, layout.image_locator, layout.image_box),)
        scale, origin = o.preview_geometry
        return section, images, scale, origin, slide.id, o.output.get()

    def painted(self):
        context = self.context()
        self.owner.preview.configure(cursor='')
        if self.drag and (not context or self.drag['document'] is not self.owner.document or
                          self.drag['key'] != context[2:]):
            self.drag = None
        if context:
            for image in context[1]:
                if image.item_id == self.selected:
                    self.outline(image.box, context)

    def outline(self, box, context):
        canvas = self.owner.preview
        canvas.delete('image-edit')
        scale, (ox, oy) = context[2:4]
        x, y = ox+box.x*scale, oy+box.y*scale
        right, bottom = x+box.width*scale, y+box.height*scale
        canvas.create_rectangle(x, y, right, bottom, outline='#dddddd', width=2, tags='image-edit')
        for px, py in ((x, y), (right, y), (x, bottom), (right, bottom)):
            canvas.create_rectangle(px-5, py-5, px+5, py+5, fill='#dddddd', outline='#333333', tags='image-edit')

    def hit(self, event, context):
        scale, (ox, oy) = context[2:4]
        images = sorted(reversed(context[1]), key=lambda p: p.item_id == self.selected, reverse=True)
        for image in images:
            b = image.box
            for corner, px, py in (('wn', b.x, b.y), ('en', b.x+b.width, b.y),
                                   ('ws', b.x, b.y+b.height), ('es', b.x+b.width, b.y+b.height)):
                if abs(event.x-ox-px*scale) <= 8 and abs(event.y-oy-py*scale) <= 8:
                    return image, corner
            if ox+b.x*scale <= event.x <= ox+(b.x+b.width)*scale and oy+b.y*scale <= event.y <= oy+(b.y+b.height)*scale:
                return image, None
        return None

    def hover(self, event):
        if self.drag:
            return
        context = self.context()
        hit = self.hit(event, context) if context else None
        self.owner.preview.configure(cursor=('sizing' if hit[1] else 'fleur') if hit else '')

    def press(self, event):
        self.owner.preview.focus_set()
        if not self.active:
            return
        self.owner.finish_editing()
        context = self.context()
        hit = self.hit(event, context) if context else None
        if hit:
            image, corner = hit
            self.selected = image.item_id
            self.drag = dict(document=self.owner.document, context=context, key=context[2:],
                             image=image, corner=corner, start=(event.x, event.y))
            self.outline(image.box, context)
        else:
            self.selected = None
            self.owner.preview.delete('image-edit')
        return 'break'

    def proposed(self, event):
        drag = self.drag
        context = self.context()
        if not context or drag['document'] is not self.owner.document or drag['key'] != context[2:]:
            self.drag = None
            return None
        dx, dy = ((event.x-drag['start'][0])/context[2], (event.y-drag['start'][1])/context[2])
        box = drag['image'].box
        config = getattr(self.owner.document, context[-1])
        if drag['corner']:
            return resized_box(box, drag['corner'], dx, dy, config)
        return constrain(replace(box, x=box.x+dx, y=box.y+dy), config)

    def motion(self, event):
        if self.drag:
            try:
                box = self.proposed(event)
                if box:
                    from PIL import Image, ImageTk
                    from .media import decode
                    canvas = self.owner.preview
                    context = self.drag['context']
                    scale, (ox, oy) = context[2:4]
                    self.outline(box, context)
                    canvas.itemconfigure('image:'+self.selected, state='hidden')
                    image = decode(self.drag['image'].locator).resize(
                        (max(1, round(box.width*scale)), max(1, round(box.height*scale))), Image.Resampling.LANCZOS)
                    self.ghost = ImageTk.PhotoImage(image, master=canvas)
                    canvas.create_image(ox+(box.x+box.width/2)*scale, oy+(box.y+box.height/2)*scale,
                                        image=self.ghost, tags='image-edit')
                    canvas.tag_lower(canvas.find_withtag('image-edit')[-1], canvas.find_withtag('image-edit')[0])
            except (ValueError, LayoutError) as exc:
                self.owner.status.set(str(exc))
        return 'break' if self.active else None

    def release(self, event):
        if not self.drag:
            return
        drag = self.drag
        try:
            box = self.proposed(event)
            if box and any(abs(getattr(box, f)-getattr(drag['image'].box, f)) > .01 for f in ('x', 'y', 'width', 'height')):
                context = drag['context']
                section = editable_section(context[0])
                item_id = section.images[0].id if isinstance(context[0], ImageSection) else self.selected
                section = with_image_box(self.owner.document, section, item_id, context[-1], box)
                document = replace(self.owner.document, sections=tuple(
                    section if s.id == section.id else s for s in self.owner.document.sections))
                # Reject an impossible text reflow before changing the draft/history.
                paginate(document, self.owner.metrics, self.owner.typography)
                self.drag = None
                self.selected = item_id
                self.owner.end_group()
                self.owner.commit(document)
                self.owner.rebuild()
        except (ValueError, LayoutError) as exc:
            self.owner.status.set('Úpravu nelze použít: '+str(exc))
        finally:
            self.drag = None
            self.ghost = None
            self.owner.render_preview()
        return 'break'

    def escape(self, event=None):
        if self.drag:
            self.drag = None
            self.ghost = None
            self.owner.render_preview()
        elif self.owner.settings.direct_image_edit:
            self.selected = None
            self.owner.render_preview()
        elif self.enabled:
            self.toggle()
        return 'break'
