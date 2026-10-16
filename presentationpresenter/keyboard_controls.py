"""Approved local keyboard/presenter controls, without global hooks."""
TEXT_INPUTS = {'Text', 'Entry', 'TEntry', 'Spinbox', 'TSpinbox', 'TCombobox'}


def bind_navigation(window, owner):
    def navigate(event):
        if event.widget.winfo_class() in TEXT_INPUTS or event.state & (0x4 | 0x8 | 0x20000):
            return
        key = event.keysym
        shifted = bool(event.state & 1)
        if shifted and key not in ('Left', 'Right'):
            return
        if shifted:
            owner.navigate_presenter('previous_section' if key == 'Left' else 'next_section')
        else:
            owner.navigate_presenter(-1 if key in ('Left', 'Up', 'Prior') else 1)
        return 'break'
    for key in ('Left', 'Right', 'Up', 'Down', 'Prior', 'Next'):
        window.bind('<KeyPress-' + key + '>', navigate)
        window.bind('<Shift-KeyPress-' + key + '>', navigate)

    def lifecycle(event):
        if event.widget.winfo_class() in TEXT_INPUTS or event.state & (0x4 | 0x8 | 0x20000):
            return
        if event.keysym == 'F5':
            owner.projection_controls.start(from_current=bool(event.state & 1))
        else:
            if event.state & 1:
                return
            owner.stop_projection()
        return 'break'
    window.bind('<F5>', lifecycle)
    window.bind('<Shift-F5>', lifecycle)
    window.bind('<Escape>', lifecycle)


def section_destination(plan, current, direction):
    """Section starts include their black prelude, including a merged start."""
    starts = []
    for section in plan.source.sections:
        index = next((i for i, slide in enumerate(plan.slides) if slide.section_id == section.id), None)
        if index is not None:
            if not starts and index > 0 and plan.slides[index-1].black:
                index -= 1
            starts.append(index)
    if direction > 0:
        return next((index for index in starts if index > current), len(plan.slides)-1)
    active = next((i for i in range(len(starts)-1, -1, -1) if starts[i] <= current), 0)
    # A trailing black slide is after the last section, so back enters that section.
    if plan.slides[current].section_id is None and current == len(plan.slides)-1:
        return starts[-1] if starts else 0
    return starts[max(0, active-1)] if starts else 0
