# Specification: Enterprise Multi-Format to Markdown Batch Pipeline

## 1. 目標

建立可在 Windows 11 本機執行的 Python 3.10+ 文件轉換工具，提供桌面 GUI 與 CLI，將企業文件批次轉為 AnythingLLM 可用的結構化內容。

支援輸入：PDF、DOC、DOCX、XLS、XLSX、PPT、PPTX、TXT。

支援輸出：

- Markdown (`.md`，預設且建議用於 AnythingLLM)
- 純文字 (`.txt`)
- JSON (`.json`，內含 Markdown 正文與來源中繼資料)

## 2. Windows GUI

GUI 必須提供：

- 拖放多個檔案或資料夾。
- 檔案與資料夾選擇器、移除與清空操作。
- 八種來源格式的個別篩選。
- 輸出目錄與輸出格式選擇。
- 工作執行緒數與強制重跑設定。
- 遮罩式 API Key 輸入，不由 GUI 自動儲存。
- 可編輯的 OpenAI-compatible Base URL。
- 呼叫目前端點的 `GET /models` 自動取得模型清單，再由使用者選擇；端點未實作該 API 時允許手動輸入模型 ID。
- 背景執行、進度顯示、逐檔結果與錯誤摘要，執行期間不得凍結 GUI。

Windows 交付包含環境安裝腳本、雙擊啟動批次檔與 PyInstaller 打包腳本。

## 3. 文件處理

- 舊版 Office (`.doc/.xls/.ppt`)：使用 LibreOffice `soffice --headless` 轉為現代格式。
- TXT：嘗試 UTF-8、UTF-16、CP950 與 CP1252。
- XLSX：逐工作表輸出 Markdown Table。
- DOCX：依原順序提取標題、段落、表格與內嵌圖片。
- PPTX：逐頁提取文字、表格、圖表數值與圖片；LibreOffice 可用時產生完整投影片預覽供 VLM 分析。
- PDF：依頁提取原生文字與圖片，將偵測到的非純文字表格、掃描頁及圖形密集頁面轉為圖片。

同名不同格式的來源不得互相覆寫，例如 `report.pdf` 與 `report.docx` 對應 `report.pdf.md` 與 `report.docx.md`。

## 4. Vision API

預設端點為 `https://api.deepseek.com`，預設模型為官方現行 V4.1 Flash API ID `deepseek-flash`。Base URL 與模型均可由 GUI 或 CLI 覆寫。

圖片以 Base64 PNG 置於 OpenAI-compatible Chat Completions `image_url` user content block。系統提示要求輸出 Markdown 表格，或完整描述流程圖、架構圖、電路圖的標籤、連線與技術規格。

HTTP 429、5xx、連線與逾時錯誤使用指數退避，最多嘗試五次。API Key 從本次 GUI 輸入、`DEEPSEEK_API_KEY` 環境變數或本機 `.env` 取得，不可寫入日誌或 Manifest。

## 5. 增量處理

輸出根目錄維護 `.conversion_manifest.json`。每個來源項目至少記錄：

```json
{
  "docs/sample.pdf": {
    "sha256": "...",
    "last_modified": 1718000000.0,
    "output_md": "docs/sample.md",
    "converted_at": "2026-09-18T10:00:00Z",
    "status": "success",
    "model": "deepseek-flash",
    "base_url": "https://api.deepseek.com",
    "output_format": "md"
  }
}
```

判斷順序：

1. `mtime`、輸出位置、模型、端點與格式未變，且成功輸出仍存在：直接略過。
2. `mtime` 改變：計算 SHA-256；內容相同時只更新 `mtime`。
3. 內容、模型、端點或輸出格式改變，輸出遺失，前次失敗，或指定 `--force`：重新處理。
4. Manifest 與輸出檔使用原子寫入；每完成一檔立即更新狀態。

## 6. 可靠性與回報

- 單一檔案失敗不得中斷其他檔案。
- 錯誤與非致命警告寫入 `conversion_error.log`。
- 執行摘要包含掃描、略過、成功、失敗及預估 VLM 圖片請求數。
- LibreOffice 呼叫需序列化，避免多執行緒共用使用者設定檔造成轉檔衝突。

## 7. 驗收

- 第一次處理全部來源；第二次未改動時全部快速略過；修改單一來源後只重做該檔。
- 修改檔案 `mtime` 但內容未變時，不重送 VLM。
- 切換模型、Base URL 或輸出格式時重新產生內容。
- 巢狀目錄結構在輸出端保持一致。
- TXT、PDF、DOCX、XLSX、PPTX 解析有自動測試；舊版 Office 格式在安裝 LibreOffice 的 Windows 環境驗證。
- GUI 可在 Windows 11 啟動，拖放可用，模型清單查詢在背景執行。

## 8. 交付內容

- `doc_to_md_pipeline.py`
- `doc_to_md_gui.py`
- `requirements.txt` / `requirements-dev.txt`
- `.env.example`
- `setup_windows.ps1` / `run_gui.bat` / `build_windows.ps1`
- `README.md`
- `tests/`
