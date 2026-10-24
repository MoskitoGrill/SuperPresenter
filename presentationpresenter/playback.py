"""Single cancellable playback timer; independent of Tk and input adapters."""
import math


def interval_ms(value):
    try:
        seconds = float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        raise ValueError('Interval musí být číslo od 0,1 do 86400 sekund.') from None
    if not math.isfinite(seconds) or not .1 <= seconds <= 86400:
        raise ValueError('Interval musí být číslo od 0,1 do 86400 sekund.')
    return round(seconds * 1000)


class Playback:
    def __init__(self, scheduler, session, advance, changed=lambda: None):
        self.scheduler, self.session, self.advance, self.changed = scheduler, session, advance, changed
        self.running = False
        self.job = None
        self.generation = 0
        self.delay = 5000
        self.repeat = False

    def cancel(self):
        self.generation += 1
        if self.job is not None:
            self.scheduler.after_cancel(self.job)
            self.job = None

    def start(self, interval, repeat=False):
        delay = interval_ms(interval)
        self.stop()
        session = self.session()
        if not session or not session.plan.slides or session.current_slide_id is None:
            return False
        self.delay, self.repeat, self.running = delay, bool(repeat), True
        self.reset()
        return True

    def stop(self):
        self.cancel()
        self.running = False
        self.changed()

    def reset(self):
        self.cancel()
        session = self.session()
        if not session or not session.plan.slides or session.current_slide_id is None:
            self.running = False
        if self.running and not session.blackout:
            generation = self.generation
            self.job = self.scheduler.after(self.delay, lambda: self.tick(generation))
        self.changed()

    def tick(self, generation):
        if generation != self.generation or not self.running:
            return
        self.job = None
        session = self.session()
        if not session or session.blackout:
            self.reset()
            return
        index = next(i for i, slide in enumerate(session.plan.slides) if slide.id == session.current_slide_id)
        if index + 1 == len(session.plan.slides):
            if not self.repeat:
                self.stop()
                return
            index = -1
        self.advance(index + 1)
        self.reset()
