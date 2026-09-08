"""Profile dialogs and layout persistence for the existing projector controls."""
from pathlib import Path
import logging
from types import SimpleNamespace
from tkinter import filedialog, messagebox

from screeninfo import get_monitors
from superpresenter.services.projection_config import (
    ConfigError, load_layout, match_monitor, monitor_identity, monitor_labels,
    save_layout, user_config_dir, validate_layout,
)
from superpresenter.ui.projector_window import ProjWindow


class ProjectionProfiles:
    def init_profiles(self):
        self.profile_dir = user_config_dir()
        self._profiles_ready = False
        self._autosave_error = False
        self._preserve_last = False
        self.monitor_names = []
        last = self.profile_dir / 'last-layout.json'
        if last.exists():
            self._preserve_last = not self.restore_profile(last)
        self._profiles_ready = True

    @staticmethod
    def monitor_signature(monitors):
        return [(m.name, m.x, m.y, m.width, m.height, getattr(m, 'is_primary', None)) for m in monitors]

    def start_monitor_watch(self):
        self._monitor_watch_closed = False
        self._monitor_seen = self.monitor_signature(getattr(self, 'monitors', []))
        self._monitor_timer = self.win.after(2000, self.poll_monitors)

    def stop_monitor_watch(self):
        self._monitor_watch_closed = True
        timer = getattr(self, '_monitor_timer', None)
        if timer is not None:
            self.win.after_cancel(timer)
            self._monitor_timer = None

    def poll_monitors(self):
        self._monitor_timer = None
        if getattr(self, '_monitor_watch_closed', False):
            return
        try:
            # Enumeration failures are transient; never replace a valid topology
            # with an invented display during automatic polling.
            current = sorted(get_monitors(), key=lambda m: (m.x, m.y))
            if current:
                editor = getattr(self, '_projection_editor', None)
                editing = editor is not None and editor.win.winfo_exists()
                if editing:
                    editor.refresh_topology(current)
                signature = self.monitor_signature(current)
                if signature != self._monitor_seen:
                    if self.update_connected_monitors(current, editing):
                        self._monitor_seen = signature
        except Exception:
            logging.getLogger(__name__).exception('Automatic monitor refresh failed; keeping current configuration')
        finally:
            if not getattr(self, '_monitor_watch_closed', False):
                self._monitor_timer = self.win.after(2000, self.poll_monitors)

    def update_connected_monitors(self, current, editing=False):
        resolved = [match_monitor(monitor_identity(self.monitors[p.monitor]), current) for p in self.projectors]
        changed_output = any(index is None or monitor_identity(self.monitors[proj.monitor]) != monitor_identity(current[index])
                             for proj, index in zip(self.projectors, resolved))
        stopped = self.runState and changed_output
        if stopped:
            self._preserve_last = True
            self.runState = False
            self._cleanup_after_stop()
        if any(index is None for index in resolved):
            # Do not put a fallback dialog over an editor with an unsaved draft.
            if editing:
                return False
            data = self.layout_snapshot()
            self._preserve_last = True
            self.restore_profile(None, data=data)
        else:
            for proj, index in zip(self.projectors, resolved):
                old = self.monitors[proj.monitor]
                if monitor_identity(old) != monitor_identity(current[index]):
                    proj.winPlacement = ''
                    proj.window_position = None
                proj.monitor = index
            self.monitors = current
            self.chooseProj['values'] = monitor_labels(current, getattr(self, 'monitor_names', []))
            self.openProjector()
        if stopped:
            messagebox.showwarning('Změna monitorů',
                'Používaná obrazovka byla odpojena nebo změnila polohu či rozlišení. '
                'Promítání bylo zastaveno. Zkontrolujte nastavení a spusťte ho znovu pomocí F5.')
        return True

    def getMonitors(self):
        try:
            self.monitors = sorted(get_monitors(), key=lambda m: (m.x, m.y))
        except Exception as exc:
            messagebox.showwarning('Monitory', f'Nelze zjistit monitory: {exc}\nPoužije se hlavní obrazovka.')
            self.monitors = []
        if not self.monitors:
            self.monitors = [SimpleNamespace(name='Hlavní obrazovka', x=0, y=0,
                width=self.win.winfo_screenwidth(), height=self.win.winfo_screenheight(), is_primary=True)]
        self.chooseProj['values'] = monitor_labels(self.monitors, getattr(self, 'monitor_names', []))

    def refresh_monitor_choices(self):
        if self.runState:
            return
        selected = self.projectorID
        self.restore_profile(None, data=self.layout_snapshot())
        self.projectorID = min(selected, len(self.projectors) - 1)
        self.openProjector()

    def layout_snapshot(self):
        outputs = []
        for proj in self.projectors:
            position = getattr(proj, 'window_position', None)
            if not proj.fullscreen and hasattr(proj, 'win'):
                position = [proj.win.winfo_x(), proj.win.winfo_y()]
            outputs.append(dict(style=self.projStyles[proj.style]['name'],
                monitor=monitor_identity(self.monitors[proj.monitor]),
                fullscreen=bool(proj.fullscreen), collection=bool(proj.collection),
                window_position=position))
        data = dict(version=2, outputs=outputs, monitor_names=getattr(self, 'monitor_names', []))
        if getattr(self, 'profile_name', None):
            data['profile_name'] = self.profile_name
        return data

    def persist_layout(self, explicit=True):
        if not getattr(self, '_profiles_ready', False):
            return
        if self._preserve_last and not explicit:
            return
        try:
            save_layout(self.profile_dir / 'last-layout.json', self.layout_snapshot(), self.projStyles)
            self._autosave_error = False
            self._preserve_last = False
        except (ConfigError, OSError) as exc:
            if not self._autosave_error:
                messagebox.showerror('Automatické uložení rozložení', str(exc))
            self._autosave_error = True

    def edit_profiles(self):
        if self.runState:
            messagebox.showinfo('Editor monitorů', 'Před úpravou monitorů zastavte promítání (F5).')
            return
        existing = getattr(self, '_projection_editor', None)
        if existing is not None and existing.win.winfo_exists():
            existing.win.lift()
            return
        if not self.restore_profile(None, data=self.layout_snapshot()):
            return
        from superpresenter.ui.projection_editor import ProjectionEditor
        self._projection_editor = ProjectionEditor(self)

    def apply_editor_layout(self, data, expected_monitors):
        validate_layout(data, self.projStyles)
        if any(match_monitor(output['monitor'], expected_monitors) is None for output in data['outputs']):
            raise ConfigError('Profil obsahuje odpojenou obrazovku. Lze ho uložit pomocí Save; před použitím obrazovku připojte nebo načtěte profil přes Load s bezpečným fallbackem.')
        previous = self.monitors
        self.getMonitors()
        current = self.monitors
        self.monitors = previous
        self.chooseProj['values'] = monitor_labels(previous, getattr(self, 'monitor_names', []))
        if [monitor_identity(m) for m in current] != [monitor_identity(m) for m in expected_monitors]:
            messagebox.showwarning('Změna monitorů',
                'Připojené monitory se během úprav změnily. Uložte případně návrh jako profil, '
                'zavřete editor a otevřete jej znovu. Rozložení nebylo změněno.')
            return False
        # Write before replacing the live layout; a failed save keeps the draft open.
        save_layout(self.profile_dir / 'last-layout.json', data, self.projStyles)
        self.monitors = current
        self.restore_profile(None, data=data, refresh=False)
        self._preserve_last = False
        self._autosave_error = False
        return True

    def load_profile(self):
        if self.runState:
            messagebox.showinfo('Načtení profilu', 'Před změnou rozložení zastavte promítání (F5).')
            return
        path = filedialog.askopenfilename(parent=self.win, title='Načíst projekční profil',
            initialdir=str(self.profile_dir / 'profiles'), filetypes=[('Projekční profil', '*.json')])
        if path and self.restore_profile(Path(path)):
            self.persist_layout()

    def restore_profile(self, path, data=None, refresh=True):
        try:
            if data is None:
                data = load_layout(path, self.projStyles)
            validate_layout(data, self.projStyles)
            # Refresh topology before resolving a stored layout.
            previous_monitors = self.monitors
            if refresh:
                self.getMonitors()
            monitors = self.monitors
            self.monitors = previous_monitors
            resolved = []
            missing = []
            for i, output in enumerate(data['outputs']):
                monitor = match_monitor(output['monitor'], monitors)
                if monitor is None:
                    missing.append(f'{i + 1}: {output["style"]} — ({output["monitor"]["x"]}, {output["monitor"]["y"]})')
                resolved.append(monitor)
            if missing and not messagebox.askyesno('Chybějící monitor',
                    '\n'.join(missing) + '\n\nObnovit tyto výstupy v běžném okně na hlavní obrazovce?\nNe = ponechat současné rozložení.'):
                self.chooseProj['values'] = monitor_labels(previous_monitors, getattr(self, 'monitor_names', []))
                self.openProjector()
                return False
            new_projectors = []
            names = [s['name'] for s in self.projStyles]
            primary = next((i for i, m in enumerate(monitors) if getattr(m, 'is_primary', False)), 0)
            for output, monitor in zip(data['outputs'], resolved):
                proj = ProjWindow(self)
                proj.style = names.index(output['style'])
                proj.monitor = primary if monitor is None else monitor
                proj.fullscreen = output['fullscreen'] if monitor is not None else False
                proj.collection = output['collection']
                position = output.get('window_position')
                mon = monitors[proj.monitor]
                if position and monitor is not None and mon.x <= position[0] < mon.x + mon.width - 50 and mon.y <= position[1] < mon.y + mon.height - 50:
                    proj.window_position = position
                    proj.winPlacement = f'{position[0]:+d}{position[1]:+d}'
                new_projectors.append(proj)
            self.monitors = monitors
            self.projectors = new_projectors
            self.profile_name = data.get('profile_name')
            self.monitor_names = data.get('monitor_names', [])
            self.chooseProj['values'] = monitor_labels(self.monitors, self.monitor_names)
            self.projectorID = 0 if self.projectors else -1
            self.openProjector()
            return True
        except (ConfigError, OSError) as exc:
            messagebox.showerror('Načtení projekčního profilu', str(exc))
            return False
