import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from config import Config
from api_client import APIClient
from pdf_extractor import extract_text, split_chunks
from ocr_extractor import is_sparse, ocr_pdf
from summary_exporter import save_as_pdf
from ui.settings_dialog import SettingsDialog

STYLE_PATH = os.path.join(os.path.dirname(__file__), 'style.css')

SUMMARY_SYSTEM = """You are a professional document analyst. Your task is to read the provided document and produce a clear, concise one-page summary.

Your summary must contain:
1. A bold title line: the document's title or topic
2. A 2-3 sentence overview paragraph
3. Between 5 and 10 bullet points covering the most important facts, arguments, findings, or takeaways

Format your response exactly like this:

**[Document Title or Topic]**

[2-3 sentence overview]

• [Key point 1]
• [Key point 2]
• [Key point 3]
(continue for 5-10 points)

Be specific and informative. Avoid vague generalities. Use the actual names, figures, and facts from the document."""

COMBINE_SYSTEM = """You are a professional document analyst. You have been given several partial summaries of sections of a large document. Combine them into a single cohesive one-page summary.

Your summary must contain:
1. A bold title line: the document's overall title or topic
2. A 2-3 sentence overview paragraph
3. Between 5 and 10 bullet points covering the most important facts, arguments, findings, or takeaways across the whole document

Format:

**[Document Title or Topic]**

[2-3 sentence overview]

• [Key point 1]
• [Key point 2]
(continue for 5-10 points)"""


def _load_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(STYLE_PATH)
    except Exception:
        pass
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Digest')
        self.set_default_size(780, 620)
        self.set_position(Gtk.WindowPosition.CENTER)
        _load_css()

        self.config = Config()
        self.api = APIClient(self.config)
        self._filepath = None
        self._page_count = 0
        self._full_text = ''
        self._chunks = []
        self._chunk_summaries = []
        self._busy = False

        self._build_ui()

    def _build_ui(self):
        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title('Digest')
        self.set_titlebar(header)

        open_btn = Gtk.Button(label='Open PDF')
        open_btn.get_style_context().add_class('action-btn')
        open_btn.connect('clicked', self._on_open)
        header.pack_start(open_btn)

        settings_btn = Gtk.Button()
        settings_btn.set_image(Gtk.Image.new_from_icon_name(
            'preferences-system-symbolic', Gtk.IconSize.BUTTON))
        settings_btn.set_tooltip_text('Settings')
        settings_btn.connect('clicked', self._on_settings)
        header.pack_end(settings_btn)

        # Main layout
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main)

        # OCR warning bar
        self._ocr_warning = Gtk.InfoBar()
        self._ocr_warning.set_message_type(Gtk.MessageType.WARNING)
        self._ocr_warning.get_content_area().pack_start(
            Gtk.Label(label='This PDF appears to be a scanned image with little or no selectable text.'),
            True, True, 0
        )
        self._ocr_warning.add_button('Run OCR', 1)
        self._ocr_warning.add_button('Dismiss', 2)
        self._ocr_warning.connect('response', self._on_ocr_response)
        self._ocr_warning.set_no_show_all(True)
        main.pack_start(self._ocr_warning, False, False, 0)

        # API warning bar
        self._api_warning = Gtk.InfoBar()
        self._api_warning.set_message_type(Gtk.MessageType.WARNING)
        self._api_warning.get_content_area().pack_start(
            Gtk.Label(label='No API key set. Open Settings (⚙) to add your OpenRouter API key.'),
            True, True, 0
        )
        self._api_warning.add_button('Open Settings', 1)
        self._api_warning.connect('response', lambda bar, r: self._on_settings(None) if r == 1 else None)
        self._api_warning.set_no_show_all(True)
        main.pack_start(self._api_warning, False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_border_width(20)
        main.pack_start(content, True, True, 0)

        # File area
        file_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        file_area.get_style_context().add_class('file-area')

        file_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        icon = Gtk.Image.new_from_icon_name('application-pdf', Gtk.IconSize.LARGE_TOOLBAR)
        file_top.pack_start(icon, False, False, 0)

        file_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._file_name_label = Gtk.Label(label='No file selected', xalign=0)
        self._file_name_label.get_style_context().add_class('file-name')
        self._file_meta_label = Gtk.Label(label='Open a PDF to get started', xalign=0)
        self._file_meta_label.get_style_context().add_class('file-meta')
        file_info.pack_start(self._file_name_label, False, False, 0)
        file_info.pack_start(self._file_meta_label, False, False, 0)
        file_top.pack_start(file_info, True, True, 0)

        file_area.pack_start(file_top, False, False, 0)
        content.pack_start(file_area, False, False, 0)

        # Generate button row
        gen_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._gen_btn = Gtk.Button(label='Generate Summary')
        self._gen_btn.get_style_context().add_class('action-btn')
        self._gen_btn.connect('clicked', self._on_generate)
        self._gen_btn.set_sensitive(False)
        gen_row.pack_start(self._gen_btn, False, False, 0)

        self._spinner = Gtk.Spinner()
        gen_row.pack_start(self._spinner, False, False, 0)

        self._progress_label = Gtk.Label(label='', xalign=0)
        self._progress_label.get_style_context().add_class('file-meta')
        gen_row.pack_start(self._progress_label, False, False, 0)

        content.pack_start(gen_row, False, False, 0)

        # Summary area
        summary_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        summary_header.pack_start(Gtk.Label(label='Summary', xalign=0), True, True, 0)

        self._copy_btn = Gtk.Button(label='Copy')
        self._copy_btn.get_style_context().add_class('secondary-btn')
        self._copy_btn.connect('clicked', self._on_copy)
        self._copy_btn.set_sensitive(False)
        summary_header.pack_end(self._copy_btn, False, False, 0)

        self._save_pdf_btn = Gtk.Button(label='Save as PDF')
        self._save_pdf_btn.get_style_context().add_class('secondary-btn')
        self._save_pdf_btn.connect('clicked', self._on_save_pdf)
        self._save_pdf_btn.set_sensitive(False)
        summary_header.pack_end(self._save_pdf_btn, False, False, 0)

        self._save_btn = Gtk.Button(label='Save as TXT')
        self._save_btn.get_style_context().add_class('secondary-btn')
        self._save_btn.connect('clicked', self._on_save)
        self._save_btn.set_sensitive(False)
        summary_header.pack_end(self._save_btn, False, False, 0)

        content.pack_start(summary_header, False, False, 0)

        summary_scroll = Gtk.ScrolledWindow()
        summary_scroll.set_vexpand(True)
        summary_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._summary_view = Gtk.TextView()
        self._summary_view.set_editable(False)
        self._summary_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._summary_view.set_left_margin(12)
        self._summary_view.set_right_margin(12)
        self._summary_view.set_top_margin(10)
        self._summary_view.set_bottom_margin(10)
        self._summary_view.get_style_context().add_class('summary-view')
        self._summary_buf = self._summary_view.get_buffer()
        summary_scroll.add(self._summary_view)
        content.pack_start(summary_scroll, True, True, 0)

        # Status bar
        self._status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._status_bar.get_style_context().add_class('status-bar')
        self._status_label = Gtk.Label(label='', xalign=0)
        self._status_bar.pack_start(self._status_label, True, True, 0)
        main.pack_start(self._status_bar, False, False, 0)

        self._check_api_key()

    def _on_open(self, btn):
        dialog = Gtk.FileChooserDialog(
            title='Open PDF',
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        f = Gtk.FileFilter()
        f.set_name('PDF files')
        f.add_mime_type('application/pdf')
        f.add_pattern('*.pdf')
        dialog.add_filter(f)

        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK and path:
            self._load_pdf(path)

    def _load_pdf(self, path):
        try:
            text, pages = extract_text(path)
            self._filepath = path
            self._page_count = pages
            self._full_text = text
            self._chunks = split_chunks(text)

            self._file_name_label.set_text(os.path.basename(path))
            self._update_meta()
            self._gen_btn.set_sensitive(bool(text.strip()))
            self._summary_buf.set_text('')
            self._copy_btn.set_sensitive(False)
            self._save_btn.set_sensitive(False)
            self._save_pdf_btn.set_sensitive(False)
            self._ocr_warning.set_visible(False)
            self._set_status(f'Loaded: {os.path.basename(path)}')

            if is_sparse(text, pages):
                self._ocr_warning.set_visible(True)
                self._ocr_warning.show_all()
                self._gen_btn.set_sensitive(False)

        except Exception as e:
            self._show_error('Could not read PDF', str(e))

    def _update_meta(self, ocr=False):
        label = 'OCR text' if ocr else 'characters'
        self._file_meta_label.set_text(
            f'{self._page_count} pages · {len(self._full_text):,} {label} · '
            f'{len(self._chunks)} chunk{"s" if len(self._chunks) > 1 else ""} to process'
        )

    def _on_ocr_response(self, bar, response_id):
        bar.set_visible(False)
        if response_id != 1 or not self._filepath:
            return

        self._busy = True
        self._gen_btn.set_sensitive(False)
        self._spinner.start()
        self._set_progress('Running OCR…')

        import threading
        from gi.repository import GLib

        def run():
            try:
                def progress(current, total):
                    GLib.idle_add(self._set_progress, f'OCR: page {current} of {total}…')
                text, pages = ocr_pdf(self._filepath, on_progress=progress)
                GLib.idle_add(self._on_ocr_done, text, pages)
            except Exception as e:
                GLib.idle_add(self._on_ocr_error, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _on_ocr_done(self, text, pages):
        self._busy = False
        self._spinner.stop()
        self._full_text = text
        self._page_count = pages
        self._chunks = split_chunks(text)
        self._update_meta(ocr=True)
        self._gen_btn.set_sensitive(bool(text.strip()))
        self._set_progress('')
        self._set_status('OCR complete — ready to summarise.')

    def _on_ocr_error(self, error_msg):
        self._busy = False
        self._spinner.stop()
        self._set_progress('')
        self._show_error('OCR failed', error_msg)

    def _on_generate(self, btn):
        if self._busy or not self._full_text:
            return
        self._busy = True
        self._gen_btn.set_sensitive(False)
        self._copy_btn.set_sensitive(False)
        self._save_btn.set_sensitive(False)
        self._spinner.start()
        self._summary_buf.set_text('')
        self._chunk_summaries = []
        self._process_next_chunk()

    def _process_next_chunk(self):
        idx = len(self._chunk_summaries)
        total = len(self._chunks)

        if idx >= total:
            if total == 1:
                self._finalise(self._chunk_summaries[0])
            else:
                self._combine()
            return

        if total > 1:
            self._set_progress(f'Summarising part {idx + 1} of {total}…')
        else:
            self._set_progress('Generating summary…')

        self.api.complete_async(
            messages=[{'role': 'user', 'content': f'Please summarise this document section:\n\n{self._chunks[idx]}'}],
            system=SUMMARY_SYSTEM,
            on_done=self._on_chunk_done,
            on_error=self._on_error,
        )

    def _on_chunk_done(self, summary):
        self._chunk_summaries.append(summary)
        self._process_next_chunk()

    def _combine(self):
        self._set_progress('Combining summaries…')
        combined = '\n\n---\n\n'.join(
            f'Part {i + 1}:\n{s}' for i, s in enumerate(self._chunk_summaries)
        )
        self.api.complete_async(
            messages=[{'role': 'user', 'content': f'Combine these partial summaries:\n\n{combined}'}],
            system=COMBINE_SYSTEM,
            on_done=self._finalise,
            on_error=self._on_error,
        )

    def _finalise(self, summary):
        self._busy = False
        self._spinner.stop()
        self._gen_btn.set_sensitive(True)
        self._set_progress('')
        self._summary_buf.set_text(summary)
        self._copy_btn.set_sensitive(True)
        self._save_btn.set_sensitive(True)
        self._save_pdf_btn.set_sensitive(True)
        self._set_status('Summary complete.')

    def _on_error(self, error_msg):
        self._busy = False
        self._spinner.stop()
        self._gen_btn.set_sensitive(True)
        self._set_progress('')
        self._set_status(f'Error: {error_msg}')
        self._show_error('Could not generate summary', error_msg)

    def _on_copy(self, btn):
        buf = self._summary_buf
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        self._set_status('Summary copied to clipboard.')

    def _on_save(self, btn):
        buf = self._summary_buf
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        if not text.strip():
            return

        dialog = Gtk.FileChooserDialog(
            title='Save Summary',
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_do_overwrite_confirmation(True)
        base = os.path.splitext(os.path.basename(self._filepath or 'summary'))[0]
        dialog.set_current_name(f'{base}_summary.txt')

        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK and path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self._set_status(f'Saved to {path}')
            except Exception as e:
                self._show_error('Could not save file', str(e))

    def _on_save_pdf(self, btn):
        buf = self._summary_buf
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        if not text.strip():
            return

        dialog = Gtk.FileChooserDialog(
            title='Save Summary as PDF',
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_do_overwrite_confirmation(True)
        base = os.path.splitext(os.path.basename(self._filepath or 'summary'))[0]
        dialog.set_current_name(f'{base}_summary.pdf')

        f = Gtk.FileFilter()
        f.set_name('PDF files')
        f.add_mime_type('application/pdf')
        f.add_pattern('*.pdf')
        dialog.add_filter(f)

        resp = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()

        if resp == Gtk.ResponseType.OK and path:
            try:
                save_as_pdf(text, path, source_filename=os.path.basename(self._filepath or ''))
                self._set_status(f'Saved PDF to {path}')
            except Exception as e:
                self._show_error('Could not save PDF', str(e))

    def _on_settings(self, btn):
        dialog = SettingsDialog(self, self.config)
        resp = dialog.run()
        if resp == Gtk.ResponseType.OK:
            key, model = dialog.get_values()
            self.config.api_key = key
            self.config.model = model
            self.config.save()
            self.api = APIClient(self.config)
            self._check_api_key()
        dialog.destroy()

    def _check_api_key(self):
        if not self.config.api_key:
            self._api_warning.set_visible(True)
            self._api_warning.show_all()
        else:
            self._api_warning.set_visible(False)

    def _set_status(self, msg):
        self._status_label.set_text(msg)

    def _set_progress(self, msg):
        self._progress_label.set_text(msg)

    def _show_error(self, title, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=title,
        )
        dialog.format_secondary_text(msg)
        dialog.run()
        dialog.destroy()
