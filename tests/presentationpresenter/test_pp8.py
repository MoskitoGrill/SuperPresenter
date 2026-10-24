import unittest
from types import SimpleNamespace
from dataclasses import replace
from presentationpresenter.playback import Playback, interval_ms
from presentationpresenter.session import ProjectionSession


class Clock:
    def __init__(self):
        self.jobs = {}
        self.serial = 0
    def after(self, delay, callback):
        self.serial += 1
        self.jobs[self.serial] = (delay, callback)
        return self.serial
    def after_cancel(self, job):
        self.jobs.pop(job, None)
    def fire(self):
        job = next(iter(self.jobs))
        _, callback = self.jobs.pop(job)
        callback()


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.plan = SimpleNamespace(slides=[SimpleNamespace(id=str(i)) for i in range(3)])
        self.session = ProjectionSession(self.plan, '0')
        self.player = Playback(self.clock, lambda: self.session, self.advance)
    def advance(self, index):
        self.session = replace(self.session, current_slide_id=str(index))
    def test_validation(self):
        for value in ('', 'nan', 'inf', 0, -.1, 86401, 'abc'):
            with self.assertRaises(ValueError): interval_ms(value)
        self.assertEqual(interval_ms('0,1'), 100)
    def test_full_wait_end_and_repeat(self):
        self.player.start(2)
        self.assertEqual(self.session.current_slide_id, '0')
        self.assertEqual(next(iter(self.clock.jobs.values()))[0], 2000)
        self.clock.fire(); self.clock.fire()
        self.assertEqual(self.session.current_slide_id, '2')
        self.assertTrue(self.player.running)
        self.clock.fire()
        self.assertFalse(self.player.running)
        self.assertFalse(self.clock.jobs)
        self.player.start(1, True)
        self.clock.fire()
        self.assertEqual(self.session.current_slide_id, '0')
    def test_blackout_manual_live_confirmation_and_stale_callback(self):
        self.player.start(3)
        stale = next(iter(self.clock.jobs.values()))[1]
        self.session = replace(self.session, blackout=True)
        self.player.reset()
        stale()
        self.assertFalse(self.clock.jobs)
        self.assertEqual(self.session.current_slide_id, '0')
        self.advance(1)
        self.player.reset()
        self.assertFalse(self.clock.jobs)
        self.session = replace(self.session, blackout=False)
        self.player.reset()
        self.assertEqual(next(iter(self.clock.jobs.values()))[0], 3000)
        self.session = ProjectionSession(SimpleNamespace(slides=[SimpleNamespace(id='1')]), '1')
        self.player.reset()
        self.assertEqual(len(self.clock.jobs), 1)
        self.clock.fire()
        self.assertFalse(self.player.running)
        self.player.start(1)
        self.session = None
        self.player.reset()
        self.assertFalse(self.clock.jobs)
    def test_stop_restart_invalid_input(self):
        self.player.start(1)
        stale = next(iter(self.clock.jobs.values()))[1]
        self.player.stop(); self.player.start(2)
        stale()
        self.assertEqual(self.session.current_slide_id, '0')
        self.assertEqual(len(self.clock.jobs), 1)
        with self.assertRaises(ValueError): self.player.start('bad')
        self.assertEqual(len(self.clock.jobs), 1)
        self.player.stop()

from tests.presentationpresenter import test_pp4


class PlaybackIntegrationTests(test_pp4.ProjectionTests):
    def test_playback_live_draft_blackout_apply_and_shutdown(self):
        w = self.w
        w.text.insert('1.0', 'Živý obsah')
        self.root.update()
        self.assertTrue(w.start_projection(('hall', 'stream')))
        w.auto_interval.set('2')
        w.start_playback()
        original = w.session.current_slide_id
        self.assertEqual(w.session.current_slide_id, original)
        job = w.playback.job
        w.jump(0)
        self.assertNotEqual(w.playback.job, job)
        w.toggle_blackout()
        self.assertIsNone(w.playback.job)
        w.title.set('Nový název')
        self.assertTrue(w.apply_live())
        self.assertIsNone(w.playback.job)
        w.toggle_blackout()
        self.assertIsNotNone(w.playback.job)
        w.view_version.set('draft')
        w.switch_version()
        draft_position = w.current
        self.root.after_cancel(w.playback.job)
        w.playback.tick(w.playback.generation)
        self.assertEqual(w.current, draft_position)
        # Stop after the simulated deadline.
        w.playback.stop()
        w.start_playback()
        w.stop_projection('hall')
        self.assertTrue(w.playback.running)
        w.stop_projection('stream')
        self.assertFalse(w.playback.running)
        self.assertIsNone(w.playback.job)
        self.assertTrue(w.start_projection(('hall',)))
        w.start_playback()
        w.projections['hall'].window.destroy()
        self.assertFalse(w.playback.running)
        self.assertIsNone(w.playback.job)


    def test_local_navigation_keys_and_text_focus(self):
        w = self.w
        w.text.insert('1.0', 'Obsah')
        self.root.update()
        self.assertTrue(w.start_projection(('hall',)))
        self.root.deiconify()
        self.root.update()
        w.preview.focus_force()
        self.root.update()
        w.navigate_presenter('first')
        for key in ('Right', 'Down', 'Next'):
            w.preview.event_generate('<KeyPress-' + key + '>')
            self.root.update()
            self.assertEqual(w.session.current_slide_id, w.session.plan.slides[1].id)
            w.navigate_presenter('first')
        for key in ('Left', 'Up', 'Prior'):
            w.navigate_presenter('first')
            w.navigate_presenter(1)
            w.preview.event_generate('<KeyPress-' + key + '>')
            self.root.update()
            self.assertEqual(w.session.current_slide_id, w.session.plan.slides[0].id)
        w.preview.event_generate('<Shift-KeyPress-Right>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, w.session.plan.slides[-1].id)
        w.preview.event_generate('<Shift-KeyPress-Left>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, w.session.plan.slides[0].id)
        for widget in (w.text, w.title_entry):
            widget.focus_force()
            self.root.update()
            widget.event_generate('<KeyPress-Right>')
            self.root.update()
            self.assertEqual(w.session.current_slide_id, w.session.plan.slides[0].id)
        w.start_playback()
        job = w.playback.job
        w.view_version.set('draft')
        w.switch_version()
        draft = w.current
        canvas = w.projections['hall'].canvas
        canvas.focus_force()
        self.root.update()
        canvas.event_generate('<KeyPress-Next>')
        self.root.update()
        self.assertEqual(w.current, draft)
        self.assertEqual(w.session.current_slide_id, w.session.plan.slides[1].id)
        self.assertNotEqual(w.playback.job, job)
        w.toggle_blackout()
        canvas.event_generate('<KeyPress-Prior>')
        self.root.update()
        self.assertIsNone(w.playback.job)
        self.assertTrue(w.session.blackout)

    def test_f5_start_and_escape_stop_all(self):
        w = self.w
        w.text.insert('1.0', 'Projekce')
        self.root.deiconify()
        self.root.update()
        w.preview.focus_force()
        self.root.update()
        w.preview.event_generate('<F5>')
        self.root.update()
        self.assertIsNotNone(w.session)
        self.assertTrue(w.start_projection(('hall', 'stream')))
        w.start_playback()
        w.projections['stream'].canvas.focus_force()
        self.root.update()
        w.projections['stream'].canvas.event_generate('<Escape>')
        self.root.update()
        self.assertFalse(w.projections)
        self.assertIsNone(w.session)
        self.assertIsNone(w.playback.job)
        self.assertFalse(w.playback.running)
        w.title_entry.focus_force()
        self.root.update()
        w.title_entry.event_generate('<F5>')
        self.root.update()
        self.assertIsNone(w.session)
        w.preview.focus_force()
        self.root.update()
        w.preview.event_generate('<F5>')
        self.root.update()
        self.assertIsNotNone(w.session)
        # Starting native projection windows can move the actual keyboard focus.
        # Generate the next key on the canvas that is really focused.
        w.preview.focus_force()
        self.root.update()
        w.preview.event_generate('<Escape>')
        self.root.update()
        self.assertIsNone(w.session)

    def test_section_jumps_and_click_releases_text_focus(self):
        w = self.w
        w.text.insert('1.0', 'První')
        self.root.update()
        w.add_section()
        w.text.insert('1.0', 'Druhý')
        self.root.update()
        self.assertTrue(w.start_projection(('hall',)))
        plan = w.session.plan
        second = next(i for i, s in enumerate(plan.slides) if s.section_id == w.document.sections[1].id)
        self.assertTrue(plan.slides[second].black)
        w.navigate_presenter('first')
        self.root.deiconify()
        self.root.update()
        w.preview.focus_force()
        self.root.update()
        w.preview.event_generate('<Shift-KeyPress-Right>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, plan.slides[second].id)
        w.preview.event_generate('<Shift-KeyPress-Right>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, plan.slides[-1].id)
        w.preview.event_generate('<Shift-KeyPress-Left>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, plan.slides[second].id)
        w.preview.event_generate('<Shift-KeyPress-Left>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, plan.slides[0].id)
        for entry in (w.text, w.title_entry):
            entry.focus_force()
            self.root.update()
            self.assertEqual(self.root.focus_get(), entry)
            # A neutral label/background, rather than the preview's own focus binding.
            self.root.event_generate('<Button-1>', x=1, y=1)
            self.root.update()
            self.assertNotEqual(self.root.focus_get(), entry)
            self.root.focus_get().event_generate('<KeyPress-b>')
            self.root.update()
            self.assertTrue(w.session.blackout)
            w.toggle_blackout()


    def test_shift_f5_current_and_f5_beginning(self):
        w = self.w
        w.text.insert('1.0', 'Aktuální obsah')
        self.root.deiconify()
        self.root.update()
        w.navigate_presenter('last')
        selected = w.plan.slides[w.current].id
        self.assertNotEqual(selected, w.plan.slides[0].id)
        w.preview.focus_force()
        self.root.update()
        w.preview.event_generate('<Shift-F5>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, selected)
        snapshot = w.session
        w.preview.event_generate('<F5>')
        self.root.update()
        self.assertEqual(w.session, snapshot)
        w.stop_projection()
        w.navigate_presenter('last')
        w.preview.focus_force()
        self.root.update()
        w.preview.event_generate('<F5>')
        self.root.update()
        self.assertEqual(w.session.current_slide_id, w.session.plan.slides[0].id)

class SectionDestinationTests(unittest.TestCase):
    def test_continuations_disabled_break_and_boundaries(self):
        from presentationpresenter.keyboard_controls import section_destination
        slides = [SimpleNamespace(section_id=sid, black=black) for sid, black in
                  [(None, True), ('a', False), ('a', False), ('b', True), ('b', False), ('c', False), (None, True)]]
        plan = SimpleNamespace(source=SimpleNamespace(sections=[SimpleNamespace(id=sid) for sid in ('a', 'b', 'c')]), slides=slides)
        for current, direction, expected in [(0, 1, 3), (2, 1, 3), (4, 1, 5), (5, 1, 6), (6, 1, 6), (6, -1, 5), (5, -1, 3), (4, -1, 0), (0, -1, 0)]:
            self.assertEqual(section_destination(plan, current, direction), expected)
