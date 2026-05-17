import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

MODELS = [
    'anthropic/claude-3.5-sonnet',
    'anthropic/claude-3-opus',
    'openai/gpt-4o',
    'openai/gpt-4o-mini',
    'google/gemini-pro-1.5',
]


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, config):
        super().__init__(title='Settings', transient_for=parent, modal=True)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(420, 200)

        box = self.get_content_area()
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)
        grid.set_border_width(20)
        box.pack_start(grid, True, True, 0)

        grid.attach(Gtk.Label(label='OpenRouter API Key:', xalign=1), 0, 0, 1, 1)
        self._key_entry = Gtk.Entry()
        self._key_entry.set_hexpand(True)
        self._key_entry.set_visibility(False)
        self._key_entry.set_text(config.api_key)
        self._key_entry.set_placeholder_text('sk-or-...')
        grid.attach(self._key_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label='Model:', xalign=1), 0, 1, 1, 1)
        self._model_combo = Gtk.ComboBoxText()
        for m in MODELS:
            self._model_combo.append(m, m)
        if config.model in MODELS:
            self._model_combo.set_active_id(config.model)
        else:
            self._model_combo.set_active(0)
        grid.attach(self._model_combo, 1, 1, 1, 1)

        link = Gtk.Label()
        link.set_markup('<a href="https://openrouter.ai/keys">Get a free API key at openrouter.ai</a>')
        link.set_xalign(0)
        grid.attach(link, 1, 2, 1, 1)

        self.show_all()

    def get_values(self):
        return self._key_entry.get_text().strip(), self._model_combo.get_active_id()
