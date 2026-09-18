#!/usr/bin/env python3
"""Windows-friendly desktop GUI for the document conversion pipeline."""

from __future__ import annotations

import argparse
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

from dotenv import load_dotenv

import doc_to_md_pipeline as pipeline

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    DND_AVAILABLE = False


FORMAT_LABELS = {
    "Markdown (.md)": "md",
    "純文字 (.txt)": "txt",
    "JSON (.json)": "json",
}


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Multi-Format to Markdown Pipeline")
        self.root.geometry("940x780")
        self.root.minsize(800, 680)
        self.selected_paths: list[Path] = []
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.running = False
        self.querying_models = False
        self.last_model_query: tuple[str, int, str] | None = None

        self.output_dir = tk.StringVar()
        self.api_key = tk.StringVar()
        self.base_url = tk.StringVar(value=os.environ.get("DEEPSEEK_BASE_URL", pipeline.DEFAULT_BASE_URL))
        self.model = tk.StringVar(value=os.environ.get("DEEPSEEK_MODEL", pipeline.DEFAULT_MODEL))
        self.output_format = tk.StringVar(value="Markdown (.md)")
        self.workers = tk.IntVar(value=min(4, max(1, os.cpu_count() or 1)))
        self.force = tk.BooleanVar(value=False)
        self.show_key = tk.BooleanVar(value=False)
        self.extension_vars = {
            extension: tk.BooleanVar(value=True) for extension in sorted(pipeline.SUPPORTED_EXTENSIONS)
        }

        self._configure_style()
        self._build_ui()
        self.root.after(100, self._drain_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Hint.TLabel", foreground="#555555")
        style.configure("Drop.TLabel", padding=18, anchor="center", relief="solid")

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="企業文件批次轉 Markdown", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="拖放檔案或資料夾，設定 DeepSeek 相容端點後開始轉換。",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        source_frame = ttk.LabelFrame(container, text="1. 輸入檔案與資料夾", padding=10)
        source_frame.pack(fill="both", expand=True)

        self.drop_label = ttk.Label(
            source_frame,
            text="將 PDF / Office / TXT 檔案或資料夾拖放到這裡\n也可以使用下方按鈕選取",
            style="Drop.TLabel",
        )
        self.drop_label.pack(fill="x", pady=(0, 8))
        if DND_AVAILABLE:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self.drop_label.configure(text=self.drop_label.cget("text") + "\n（未安裝 tkinterdnd2，按鈕選取仍可使用）")

        list_frame = ttk.Frame(source_frame)
        list_frame.pack(fill="both", expand=True)
        self.path_list = tk.Listbox(list_frame, height=7, selectmode="extended", font=("Segoe UI", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.path_list.yview)
        self.path_list.configure(yscrollcommand=scrollbar.set)
        self.path_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        button_row = ttk.Frame(source_frame)
        button_row.pack(fill="x", pady=(8, 0))
        ttk.Button(button_row, text="選擇檔案…", command=self._choose_files).pack(side="left")
        ttk.Button(button_row, text="選擇資料夾…", command=self._choose_folder).pack(side="left", padx=6)
        ttk.Button(button_row, text="移除選取", command=self._remove_selected).pack(side="left")
        ttk.Button(button_row, text="全部清除", command=self._clear_paths).pack(side="left", padx=6)

        filter_frame = ttk.LabelFrame(container, text="2. 輸入與輸出格式", padding=10)
        filter_frame.pack(fill="x", pady=10)
        ttk.Label(filter_frame, text="處理格式：").grid(row=0, column=0, sticky="w")
        extensions_frame = ttk.Frame(filter_frame)
        extensions_frame.grid(row=0, column=1, columnspan=3, sticky="w")
        for index, extension in enumerate(sorted(self.extension_vars)):
            ttk.Checkbutton(
                extensions_frame,
                text=extension.upper().lstrip("."),
                variable=self.extension_vars[extension],
            ).grid(row=index // 8, column=index % 8, padx=(0, 10), sticky="w")

        ttk.Label(filter_frame, text="輸出格式：").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Combobox(
            filter_frame,
            textvariable=self.output_format,
            values=list(FORMAT_LABELS),
            state="readonly",
            width=22,
        ).grid(row=1, column=1, sticky="w", pady=(10, 0))
        ttk.Label(filter_frame, text="並行數：").grid(row=1, column=2, sticky="e", padx=(24, 6), pady=(10, 0))
        ttk.Spinbox(filter_frame, from_=1, to=32, textvariable=self.workers, width=6).grid(
            row=1, column=3, sticky="w", pady=(10, 0)
        )

        output_frame = ttk.Frame(filter_frame)
        output_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        output_frame.columnconfigure(1, weight=1)
        ttk.Label(output_frame, text="輸出目錄：").grid(row=0, column=0, sticky="w")
        ttk.Entry(output_frame, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(output_frame, text="瀏覽…", command=self._choose_output).grid(row=0, column=2)
        ttk.Checkbutton(output_frame, text="強制重新轉換", variable=self.force).grid(
            row=1, column=1, sticky="w", pady=(6, 0)
        )

        api_frame = ttk.LabelFrame(container, text="3. API 與模型", padding=10)
        api_frame.pack(fill="x")
        api_frame.columnconfigure(1, weight=1)
        ttk.Label(api_frame, text="API Key：").grid(row=0, column=0, sticky="w")
        self.key_entry = ttk.Entry(api_frame, textvariable=self.api_key, show="●")
        self.key_entry.grid(row=0, column=1, sticky="ew", padx=6)
        self.key_entry.bind("<FocusOut>", lambda _event: self._refresh_models(manual=False))
        ttk.Checkbutton(api_frame, text="顯示", variable=self.show_key, command=self._toggle_key).grid(
            row=0, column=2, sticky="w"
        )
        key_hint = "已有環境或 .env 金鑰；留白即沿用。" if os.environ.get("DEEPSEEK_API_KEY") else "只供本次執行使用，不會由 GUI 儲存。"
        ttk.Label(api_frame, text=key_hint, style="Hint.TLabel").grid(
            row=1, column=1, columnspan=2, sticky="w", padx=6
        )

        ttk.Label(api_frame, text="Base URL：").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.base_url_combo = ttk.Combobox(
            api_frame,
            textvariable=self.base_url,
            values=(pipeline.DEFAULT_BASE_URL, "https://api.deepseek.com/v1"),
        )
        self.base_url_combo.grid(row=2, column=1, columnspan=2, sticky="ew", padx=6, pady=(8, 0))
        self.base_url_combo.bind("<FocusOut>", lambda _event: self._refresh_models(manual=False))
        self.base_url_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_models(manual=False))

        ttk.Label(api_frame, text="LLM / VLM：").grid(row=3, column=0, sticky="w", pady=(8, 0))
        model_row = ttk.Frame(api_frame)
        model_row.grid(row=3, column=1, columnspan=2, sticky="ew", padx=6, pady=(8, 0))
        model_row.columnconfigure(0, weight=1)
        self.model_combo = ttk.Combobox(
            model_row,
            textvariable=self.model,
            values=("deepseek-flash", "deepseek-v4-flash-vision-exp"),
            postcommand=lambda: self._refresh_models(manual=False),
        )
        self.model_combo.grid(row=0, column=0, sticky="ew")
        self.model_query_button = ttk.Button(
            model_row, text="查詢模型", command=lambda: self._refresh_models(manual=True)
        )
        self.model_query_button.grid(row=0, column=1, padx=(6, 0))
        ttk.Label(
            api_frame,
            text="下拉選單會從 /models 自動更新；含圖片的文件必須選擇支援 Vision 的模型。",
            style="Hint.TLabel",
        ).grid(row=4, column=1, columnspan=2, sticky="w", padx=6, pady=(2, 0))
        self.model_status = tk.StringVar(value="尚未查詢模型")
        ttk.Label(api_frame, textvariable=self.model_status, style="Hint.TLabel").grid(
            row=5, column=1, columnspan=2, sticky="w", padx=6, pady=(2, 0)
        )

        action_frame = ttk.Frame(container)
        action_frame.pack(fill="x", pady=(10, 6))
        self.start_button = ttk.Button(action_frame, text="開始轉換", command=self._start)
        self.start_button.pack(side="right")
        self.progress = ttk.Progressbar(action_frame, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.status = tk.StringVar(value="就緒")
        ttk.Label(container, textvariable=self.status).pack(anchor="w")
        self.log = ScrolledText(container, height=7, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=False, pady=(4, 0))
        if os.environ.get("DEEPSEEK_API_KEY"):
            self.root.after(500, lambda: self._refresh_models(manual=False))

    def _toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key.get() else "●")

    def _on_drop(self, event: Any) -> None:
        self._add_paths([Path(value) for value in self.root.tk.splitlist(event.data)])

    def _choose_files(self) -> None:
        values = filedialog.askopenfilenames(
            title="選擇要轉換的文件",
            filetypes=[
                ("支援的文件", "*.pdf *.doc *.docx *.xls *.xlsx *.ppt *.pptx *.txt"),
                ("所有檔案", "*.*"),
            ],
        )
        self._add_paths([Path(value) for value in values])

    def _choose_folder(self) -> None:
        value = filedialog.askdirectory(title="選擇包含文件的資料夾")
        if value:
            self._add_paths([Path(value)])

    def _choose_output(self) -> None:
        value = filedialog.askdirectory(title="選擇輸出資料夾")
        if value:
            self.output_dir.set(value)

    def _add_paths(self, paths: list[Path]) -> None:
        known = {str(path.resolve()).casefold() for path in self.selected_paths}
        unsupported: list[str] = []
        for path in paths:
            resolved = path.expanduser().resolve()
            if not resolved.exists():
                continue
            if resolved.is_file() and resolved.suffix.lower() not in pipeline.SUPPORTED_EXTENSIONS:
                unsupported.append(resolved.name)
                continue
            key = str(resolved).casefold()
            if key not in known:
                self.selected_paths.append(resolved)
                known.add(key)
                self.path_list.insert("end", str(resolved))
        if unsupported:
            messagebox.showwarning("不支援的格式", "已略過：\n" + "\n".join(unsupported[:10]))
        if self.selected_paths and not self.output_dir.get():
            first = self.selected_paths[0]
            parent = first.parent
            self.output_dir.set(str(parent / "anythingllm_knowledge_base"))

    def _remove_selected(self) -> None:
        indexes = list(self.path_list.curselection())
        for index in reversed(indexes):
            del self.selected_paths[index]
            self.path_list.delete(index)

    def _clear_paths(self) -> None:
        self.selected_paths.clear()
        self.path_list.delete(0, "end")

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _refresh_models(self, manual: bool) -> None:
        if self.querying_models:
            return
        api_key = self.api_key.get().strip() or os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = self.base_url.get().strip().rstrip("/")
        if not api_key:
            self.model_status.set("輸入 API Key 後即可自動查詢模型")
            if manual:
                messagebox.showinfo("需要 API Key", "請先輸入 API Key，再查詢可用模型。")
            return
        if not base_url:
            self.model_status.set("請先輸入 Base URL")
            return
        signature = (base_url, len(api_key), api_key[-4:])
        if not manual and signature == self.last_model_query:
            return
        self.querying_models = True
        self.model_query_button.configure(state="disabled")
        self.model_status.set("正在從端點查詢模型…")
        threading.Thread(
            target=self._query_models_worker,
            args=(api_key, base_url, signature),
            daemon=True,
            name="model-query-worker",
        ).start()

    def _query_models_worker(
        self, api_key: str, base_url: str, signature: tuple[str, int, str]
    ) -> None:
        try:
            models = pipeline.list_available_models(api_key, base_url)
            self.events.put(("models", (models, signature)))
        except Exception as exc:
            self.events.put(("models_error", f"{type(exc).__name__}: {exc}"))

    def _start(self) -> None:
        if self.running:
            return
        if not self.selected_paths:
            messagebox.showerror("缺少輸入", "請加入至少一個檔案或資料夾。")
            return
        if not self.output_dir.get().strip():
            messagebox.showerror("缺少輸出目錄", "請選擇輸出目錄。")
            return
        extensions = {extension for extension, variable in self.extension_vars.items() if variable.get()}
        if not extensions:
            messagebox.showerror("缺少格式", "請至少勾選一種輸入格式。")
            return
        if not self.base_url.get().strip() or not self.model.get().strip():
            messagebox.showerror("API 設定不完整", "Base URL 與模型不可空白。")
            return
        try:
            workers = int(self.workers.get())
            if workers < 1:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("並行數錯誤", "並行數必須是大於 0 的整數。")
            return

        args = argparse.Namespace(
            output_dir=self.output_dir.get().strip(),
            workers=workers,
            force=self.force.get(),
            model=self.model.get().strip(),
            base_url=self.base_url.get().strip().rstrip("/"),
            output_format=FORMAT_LABELS[self.output_format.get()],
            api_key=self.api_key.get().strip() or None,
        )
        paths = list(self.selected_paths)
        self.running = True
        self.start_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self.status.set("掃描與轉換中…")
        self._append_log(f"開始處理 {len(paths)} 個選取項目。")
        threading.Thread(
            target=self._run_worker,
            args=(args, paths, extensions),
            daemon=True,
            name="conversion-worker",
        ).start()

    def _run_worker(self, args: argparse.Namespace, paths: list[Path], extensions: set[str]) -> None:
        try:
            exit_code = pipeline.run_pipeline_paths(
                args,
                paths,
                allowed_extensions=extensions,
                progress_callback=lambda result, current, total: self.events.put(
                    ("progress", (result, current, total))
                ),
                quiet=True,
            )
            self.events.put(("done", (exit_code, getattr(args, "run_summary", {}), args.output_dir)))
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def _drain_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "progress":
                    result, current, total = payload
                    if str(self.progress.cget("mode")) != "determinate":
                        self.progress.stop()
                        self.progress.configure(mode="determinate", maximum=max(1, total))
                    self.progress["value"] = current
                    state = "完成" if result.success else "失敗"
                    self.status.set(f"{current} / {total}：{result.job.relative_source.as_posix()}")
                    self._append_log(f"[{state}] {result.job.relative_source.as_posix()}")
                    if result.error:
                        self._append_log(f"       {result.error}")
                    for warning in result.warnings:
                        self._append_log(f"[警告] {warning}")
                elif event == "done":
                    exit_code, summary, output_dir = payload
                    self._finish_run()
                    self.progress["value"] = self.progress["maximum"]
                    self.status.set("完成" if exit_code == 0 else "完成，但有檔案失敗")
                    self._append_log(
                        "摘要：掃描 {total}、略過 {skipped}、成功 {converted}、失敗 {failed}、VLM 請求 {image_requests}".format(
                            **summary
                        )
                    )
                    if exit_code == 0:
                        messagebox.showinfo("轉換完成", f"輸出位置：\n{output_dir}")
                    else:
                        messagebox.showwarning("轉換完成", f"部分檔案失敗，請查看錯誤記錄：\n{output_dir}")
                elif event == "error":
                    self._finish_run()
                    self.status.set("執行失敗")
                    self._append_log(f"[錯誤] {payload}")
                    messagebox.showerror("執行失敗", payload)
                elif event == "models":
                    models, signature = payload
                    self.querying_models = False
                    self.last_model_query = signature
                    self.model_query_button.configure(state="normal")
                    self.model_combo.configure(values=models)
                    if self.model.get() not in models:
                        preferred = "deepseek-flash" if "deepseek-flash" in models else models[0]
                        self.model.set(preferred)
                    self.model_status.set(f"已查詢到 {len(models)} 個模型")
                elif event == "models_error":
                    self.querying_models = False
                    self.model_query_button.configure(state="normal")
                    self.model_status.set("模型查詢失敗；仍可手動輸入模型 ID")
                    self._append_log(f"[模型查詢失敗] {payload}")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._drain_events)

    def _finish_run(self) -> None:
        self.running = False
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.start_button.configure(state="normal")


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
