import os
import sys
import shutil
import threading
import tempfile
from datetime import datetime
from io import BytesIO
import concurrent.futures

import fitz
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import configparser

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk


def get_program_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


TEXTS = {
    "pt-br": {
        "target_label": "Tamanho alvo (MB):",
        "lang_label": "Idioma:",
        "dev_by": "Desenvolvido por Alex 'OAleex' Félix",
        "none_selected": "Nenhum arquivo selecionado",
        "filedialog_title": "Selecione os PDFs",
        "selected_n": "Selecionado(s): {n}",
        "ignored_n": " (ignorados: {n})",
        "and_more_files": "... e mais {n} arquivos",
        "none_valid": "Nenhum PDF válido selecionado",
        "warning_title": "Atenção",
        "warn_select_valid": "Selecione pelo menos um PDF válido.",
        "invalid_title": "Valor inválido",
        "invalid_body": "Informe um tamanho alvo (MB) válido maior que zero.",
        "exists_title": "Arquivos já existem",
        "exists_body": "Os seguintes arquivos já existem na pasta de destino:\n\n{file_list}\n\nDeseja sobrescrever?",
        "processing": "Processando...",
        "finished_label": "Processamento concluído",
        "finished_title": "Finalizado!",
        "finished_body": "Processamento concluído!",
        "button_select": "Selecionar PDFs…",
        "button_compress": "Comprimir",
        "button_open": "Abrir pasta de saída",
        "open_error_title": "Erro",
        "open_error_body": "Não foi possível abrir a pasta:\n{e}",
    },
    "en": {
        "target_label": "Target size (MB):",
        "lang_label": "Language:",
        "dev_by": "Developed by Alex 'OAleex' Félix",
        "none_selected": "No files selected",
        "filedialog_title": "Select PDFs",
        "selected_n": "Selected: {n}",
        "ignored_n": " (ignored: {n})",
        "and_more_files": "... and {n} more files",
        "none_valid": "No valid PDF selected",
        "warning_title": "Warning",
        "warn_select_valid": "Select at least one valid PDF.",
        "invalid_title": "Invalid value",
        "invalid_body": "Enter a valid target size (MB) greater than zero.",
        "exists_title": "Files already exist",
        "exists_body": "The following files already exist in the destination folder:\n\n{file_list}\n\nOverwrite?",
        "processing": "Processing...",
        "finished_label": "Processing finished",
        "finished_title": "Done!",
        "finished_body": "Processing finished!",
        "button_select": "Select PDFs…",
        "button_compress": "Compress",
        "button_open": "Open output folder",
        "open_error_title": "Error",
        "open_error_body": "Could not open folder:\n{e}",
    },
    "es": {
        "target_label": "Tamaño objetivo (MB):",
        "lang_label": "Idioma:",
        "dev_by": "Desarrollado por Alex 'OAleex' Félix",
        "none_selected": "Ningún archivo seleccionado",
        "filedialog_title": "Selecciona los PDFs",
        "selected_n": "Seleccionado(s): {n}",
        "ignored_n": " (ignorados: {n})",
        "and_more_files": "... y {n} archivos más",
        "none_valid": "Ningún PDF válido seleccionado",
        "warning_title": "Atención",
        "warn_select_valid": "Selecciona al menos un PDF válido.",
        "invalid_title": "Valor no válido",
        "invalid_body": "Ingrese un tamaño objetivo (MB) válido mayor que cero.",
        "exists_title": "Los archivos ya existen",
        "exists_body": "Los siguientes archivos ya existen en la carpeta de destino:\n\n{file_list}\n\n¿Desea sobrescribir?",
        "processing": "Procesando...",
        "finished_label": "Procesamiento completado",
        "finished_title": "¡Finalizado!",
        "finished_body": "¡Procesamiento completado!",
        "button_select": "Seleccionar PDFs…",
        "button_compress": "Comprimir",
        "button_open": "Abrir carpeta de salida",
        "open_error_title": "Error",
        "open_error_body": "No se pudo abrir la carpeta:\n{e}",
    },
}

CURRENT_LANG = "en"


def get_config_path():
    return os.path.join(get_program_dir(), "config.ini")


def load_language_from_ini():
    global CURRENT_LANG
    cfg = configparser.ConfigParser()
    cfg_path = get_config_path()
    if not os.path.exists(cfg_path):
        try:
            cfg["app"] = {"language": CURRENT_LANG}
            with open(cfg_path, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception:
            pass
        return CURRENT_LANG
    try:
        cfg.read(cfg_path, encoding="utf-8")
        lang = cfg.get("app", "language", fallback=CURRENT_LANG).lower()
        if lang not in TEXTS:
            lang = CURRENT_LANG
        CURRENT_LANG = lang
        return CURRENT_LANG
    except Exception:
        return CURRENT_LANG


def tr(key, **kwargs):
    base = TEXTS.get(CURRENT_LANG, TEXTS["pt-br"]).get(key)
    if base is None:
        base = TEXTS["pt-br"].get(key, key)
    try:
        return base.format(**kwargs)
    except Exception:
        return base


def save_language_to_ini(lang_key: str):
    try:
        cfg = configparser.ConfigParser()
        cfg_path = get_config_path()
        if os.path.exists(cfg_path):
            cfg.read(cfg_path, encoding="utf-8")
        if "app" not in cfg:
            cfg["app"] = {}
        cfg["app"]["language"] = lang_key
        with open(cfg_path, "w", encoding="utf-8") as f:
            cfg.write(f)
    except Exception:
        pass


def load_target_mb_from_ini(default_value: float = 20.0) -> float:
    try:
        cfg = configparser.ConfigParser()
        cfg_path = get_config_path()
        if not os.path.exists(cfg_path):
            return default_value
        cfg.read(cfg_path, encoding="utf-8")
        val = cfg.get("app", "target_mb", fallback=str(default_value))
        try:
            mb = float(val)
            if mb > 0:
                return mb
        except Exception:
            pass
        return default_value
    except Exception:
        return default_value


def save_target_mb_to_ini(value: float):
    try:
        cfg = configparser.ConfigParser()
        cfg_path = get_config_path()
        if os.path.exists(cfg_path):
            cfg.read(cfg_path, encoding="utf-8")
        if "app" not in cfg:
            cfg["app"] = {}
        cfg["app"]["target_mb"] = str(value)
        with open(cfg_path, "w", encoding="utf-8") as f:
            cfg.write(f)
    except Exception:
        pass


def ensure_ini_defaults(default_mb: float = 20.0):
    try:
        cfg = configparser.ConfigParser()
        cfg_path = get_config_path()
        if os.path.exists(cfg_path):
            cfg.read(cfg_path, encoding="utf-8")
        if "app" not in cfg:
            cfg["app"] = {}
        if not cfg["app"].get("language"):
            cfg["app"]["language"] = CURRENT_LANG
        if not cfg["app"].get("target_mb"):
            cfg["app"]["target_mb"] = str(default_mb)
        with open(cfg_path, "w", encoding="utf-8") as f:
            cfg.write(f)
    except Exception:
        pass


def ensure_unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while True:
        candidate = f"{base} ({i}){ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


def is_valid_pdf(path: str) -> bool:
    try:
        if not os.path.isfile(path):
            return False
        if not path.lower().endswith('.pdf'):
            return False
        with open(path, 'rb') as f:
            head = f.read(1024)
            if b"%PDF-" not in head:
                try:
                    doc = fitz.open(path)
                    doc.close()
                except Exception:
                    return False
        return True
    except Exception:
        return False


def build_output_dir():
    base = ensure_base_output_dir()
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(base, date_str)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def open_output_dir(out_dir):
    try:
        if sys.platform.startswith("win"):
            os.startfile(out_dir)
        elif sys.platform == "darwin":
            os.system(f"open '{out_dir}'")
        else:
            os.system(f"xdg-open '{out_dir}'")
    except Exception as e:
        messagebox.showerror(tr("open_error_title"), tr("open_error_body", e=e))


def ensure_base_output_dir():
    base_dir = os.path.join(get_program_dir(), "App")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def _render_pages_raw(input_path, dpi):
    doc = fitz.open(input_path)
    pages = []
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
            pages.append((pix.width, pix.height, bytes(pix.samples)))
    finally:
        doc.close()
    return pages


def _build_pdf_from_pages(pages_raw, jpeg_quality):
    pdf_buf = BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    width, height = A4

    max_workers = max(1, min(4, (os.cpu_count() or 1)))

    def encode(idx, iw, ih, rgb):
        img = Image.frombytes("RGB", (iw, ih), rgb)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
        data = buf.getvalue()
        buf.close()
        img.close()
        return (idx, iw, ih, data)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(encode, i, iw, ih, rgb) for i, (iw, ih, rgb) in enumerate(pages_raw)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        results.sort(key=lambda t: t[0])

    for idx, iw, ih, jpeg_bytes in results:
        img_buf = BytesIO(jpeg_bytes)
        scale = min(width / iw, height / ih)
        nw, nh = iw * scale, ih * scale
        x, y = (width - nw) / 2, (height - nh) / 2
        c.drawImage(ImageReader(img_buf), x, y, width=nw, height=nh)
        c.showPage()
        img_buf.close()

    c.save()
    pdf_bytes = pdf_buf.getvalue()
    pdf_buf.close()
    return pdf_bytes


def compress_to_target(input_path, output_path, target_mb, progress_cb=None):
    current_mb = os.path.getsize(input_path) / (1024 * 1024)
    compression_ratio = target_mb / current_mb if current_mb > 0 else 1.0

    if compression_ratio > 0.8:
        dpi_range = [300, 250, 200, 180, 150]
    elif compression_ratio > 0.6:
        dpi_range = [250, 200, 180, 150, 120, 100]
    elif compression_ratio > 0.4:
        dpi_range = [200, 150, 120, 100, 90, 80]
    elif compression_ratio > 0.25:
        dpi_range = [150, 120, 100, 90, 80, 70]
    else:
        dpi_range = [120, 100, 90, 80, 70, 60]

    target_bytes = int(target_mb * 1024 * 1024)

    best_pdf_bytes = None
    best_size = float("inf")

    bin_steps = 6
    total_attempts = len(dpi_range) * bin_steps
    attempt_idx = 0

    out_dir = os.path.dirname(output_path)
    base_noext, _ = os.path.splitext(os.path.basename(output_path))
    temp_path = os.path.join(out_dir, f"tmp.pdf")

    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass

    def write_temp(data: bytes):
        try:
            with open(temp_path, "wb") as f:
                f.write(data)
        except Exception:
            pass

    try:
        for dpi in dpi_range:
            try:
                pages_raw = _render_pages_raw(input_path, dpi)
            except Exception:
                continue

            q_low, q_high = 40, 95
            candidate_pdf = None
            candidate_size = None

            for _ in range(bin_steps):
                attempt_idx += 1
                q_mid = (q_low + q_high) // 2

                if callable(progress_cb):
                    try:
                        progress_cb(attempt_idx, total_attempts)
                    except Exception:
                        pass

                try:
                    pdf_bytes = _build_pdf_from_pages(pages_raw, q_mid)
                except Exception:
                    q_high = q_mid - 1
                    continue

                size_bytes = len(pdf_bytes)
                size_mb = size_bytes / (1024 * 1024)

                if size_mb < best_size:
                    best_size = size_mb
                    best_pdf_bytes = pdf_bytes
                    write_temp(pdf_bytes)

                if size_bytes > target_bytes:
                    q_high = q_mid - 1
                else:
                    candidate_pdf = pdf_bytes
                    candidate_size = size_mb
                    q_low = q_mid + 1

            if candidate_pdf is not None:
                try:
                    write_temp(candidate_pdf)
                    os.replace(temp_path, output_path)
                except Exception:
                    with open(output_path, "wb") as f:
                        f.write(candidate_pdf)
                return True, candidate_size if candidate_size is not None else (best_size if best_size != float("inf") else 0.0)

        if best_pdf_bytes is not None:
            try:
                write_temp(best_pdf_bytes)
                os.replace(temp_path, output_path)
            except Exception:
                with open(output_path, "wb") as f:
                    f.write(best_pdf_bytes)
            return True, best_size
        return False, 0.0

    except Exception:
        return False, 0.0


selected_files = []
busy = False


def main():
    global busy

    root = tk.Tk()
    root.geometry("500x150")
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", root.quit)


    load_language_from_ini()
    ensure_ini_defaults(20.0)
    ensure_base_output_dir()
    root.title(tr("pyPDFCompress"))

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    lbl_target = ttk.Label(frm, text=tr("target_label"))
    lbl_target.grid(row=0, column=0, sticky="w")
    ent_target = ttk.Entry(frm, width=10)
    default_target = load_target_mb_from_ini(20.0)
    ent_target.insert(0, f"{default_target:g}")
    ent_target.grid(row=0, column=1, sticky="w", padx=(6, 0))

    lbl_info = ttk.Label(frm, text=tr("none_selected"))
    lbl_info.grid(row=0, column=2, sticky="w", padx=(16, 0))

    lang_frame = ttk.Frame(frm)
    lang_frame.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))
    lbl_lang = ttk.Label(lang_frame, text=tr("lang_label"))
    lbl_lang.pack(side="left", padx=(0, 4))
    lang_var = tk.StringVar()
    key_to_disp = {"pt-br": "PT-BR", "en": "EN", "es": "ES"}
    disp_to_key = {v: k for k, v in key_to_disp.items()}
    lang_values = ["PT-BR", "EN", "ES"]
    lang_combo = ttk.Combobox(lang_frame, width=6, state="readonly", values=lang_values, textvariable=lang_var)
    lang_combo.pack(side="left")
    lang_var.set(key_to_disp.get(CURRENT_LANG, "EN"))
    dev_label = ttk.Label(lang_frame, text=tr("dev_by"))
    dev_label.pack(side="left", padx=(12, 0))

    progress = ttk.Progressbar(frm, mode="determinate")
    progress.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 0))

    def pick_files():
        if busy:
            return
        nonlocal last_invalid_count
        paths = filedialog.askopenfilenames(title=tr("filedialog_title"), filetypes=[("PDF", "*.pdf")])
        if not paths:
            return
        valid = [p for p in paths if is_valid_pdf(p)]
        invalid = len(paths) - len(valid)
        last_invalid_count = invalid
        selected_files.clear()
        selected_files.extend(valid)
        
        if selected_files:
            lbl = tr("selected_n", n=len(selected_files))
            if invalid:
                lbl += tr("ignored_n", n=invalid)
            lbl_info.config(text=lbl)
            btn_compress.config(state="normal")
        else:
            lbl_info.config(text=tr("none_valid"))
            btn_compress.config(state="disabled")

    def do_compress():
        global busy
        if busy:
            return
        if not selected_files:
            messagebox.showwarning(tr("warning_title"), tr("warn_select_valid"))
            return
        try:
            target = float(ent_target.get())
            if target <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror(tr("invalid_title"), tr("invalid_body"))
            return

        try:
            save_target_mb_to_ini(target)
        except Exception:
            pass

        out_dir = build_output_dir()
        total = len(selected_files)
        ok_count = 0
        file_progress = 0

        existing_files = []
        for src in selected_files:
            name = os.path.basename(src)
            dst = os.path.join(out_dir, name)
            if os.path.exists(dst):
                existing_files.append(name)
        
        if existing_files:
            file_list = '\n'.join(existing_files[:5])
            if len(existing_files) > 5:
                file_list += '\n' + tr('and_more_files', n=(len(existing_files) - 5))
            
            result = messagebox.askyesno(
                tr("exists_title"),
                tr("exists_body", file_list=file_list),
                icon="warning"
            )
            if not result:
                return

        busy = True
        btn_compress.config(state="disabled")
        btn_pick.config(state="disabled")
        ent_target.config(state="disabled")
        progress.config(maximum=100, value=0)
        lbl_info.config(text=tr("processing"))

        def update_progress(current_attempt, total_attempts):
            file_prog = (current_attempt / total_attempts) * 80
            overall_prog = (file_progress / total) * 100
            combined_prog = (file_progress / total) * 20 + file_prog / total
            root.after(0, progress.config, {"value": combined_prog})

        def worker():
            nonlocal ok_count, file_progress
            
            for i, src in enumerate(selected_files, 1):
                file_progress = i - 1
                name = os.path.basename(src)
                dst = os.path.join(out_dir, name)
                
                root.after(0, lbl_info.config, {"text": tr("processing")})
                
                try:
                    src_mb = os.path.getsize(src) / (1024 * 1024)
                    
                    if src_mb <= target:
                        shutil.copy2(src, dst)
                        ok_count += 1
                        root.after(0, progress.config, {"value": (i / total) * 100})
                    else:
                        ok, out_size = compress_to_target(src, dst, target, update_progress)
                        if ok:
                            ok_count += 1
                    
                except Exception:
                    pass

            def finish():
                nonlocal ok_count
                global busy
                busy = False
                
                progress.config(value=100)
                lbl_info.config(text=tr("finished_label"))
                btn_compress.config(state="normal" if selected_files else "disabled")
                btn_pick.config(state="normal")
                ent_target.config(state="normal")
                
                if ok_count > 0:
                    open_output_dir(out_dir)
                
                messagebox.showinfo(tr("finished_title"), 
                    tr("finished_body", ok=ok_count, total=total, out_dir=out_dir))

            root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def open_out():
        out_dir = build_output_dir()
        open_output_dir(out_dir)

    btn_pick = ttk.Button(frm, text=tr("button_select"), command=pick_files)
    btn_pick.grid(row=1, column=0, pady=(12, 0), sticky="w")
    btn_compress = ttk.Button(frm, text=tr("button_compress"), command=do_compress, state="disabled")
    btn_compress.grid(row=1, column=1, pady=(12, 0), sticky="w", padx=(6, 0))
    btn_open = ttk.Button(frm, text=tr("button_open"), command=open_out)
    btn_open.grid(row=1, column=2, pady=(12, 0), sticky="w", padx=(12, 0))

    last_invalid_count = 0

    _save_job = {"id": None}

    def _schedule_save():
        if _save_job["id"] is not None:
            try:
                root.after_cancel(_save_job["id"])
            except Exception:
                pass
            _save_job["id"] = None
        def _do():
            try:
                v = float(ent_target.get())
                if v > 0:
                    save_target_mb_to_ini(v)
            except Exception:
                pass
        _save_job["id"] = root.after(500, _do)

    def on_target_keyrelease(event=None):
        _schedule_save()

    def on_target_focus_out(event=None):
        try:
            v = float(ent_target.get())
            if v > 0:
                save_target_mb_to_ini(v)
        except Exception:
            pass

    ent_target.bind("<KeyRelease>", on_target_keyrelease)
    ent_target.bind("<FocusOut>", on_target_focus_out)

    def apply_i18n():
        lbl_target.config(text=tr("target_label"))
        btn_pick.config(text=tr("button_select"))
        btn_compress.config(text=tr("button_compress"))
        btn_open.config(text=tr("button_open"))
        lbl_lang.config(text=tr("lang_label"))
        dev_label.config(text=tr("dev_by"))
        if busy:
            lbl_info.config(text=tr("processing"))
        else:
            if selected_files:
                info = tr("selected_n", n=len(selected_files))
                if last_invalid_count:
                    info += tr("ignored_n", n=last_invalid_count)
                lbl_info.config(text=info)
            else:
                lbl_info.config(text=tr("none_selected"))

    def on_lang_selected(event=None):
        disp = lang_var.get()
        key = disp_to_key.get(disp, CURRENT_LANG)
        if key != CURRENT_LANG:
            globals()["CURRENT_LANG"] = key
            save_language_to_ini(key)
            apply_i18n()

    lang_combo.bind("<<ComboboxSelected>>", on_lang_selected)
    apply_i18n()

    frm.columnconfigure(3, weight=1)
    root.mainloop()


if __name__ == "__main__":
    main()
