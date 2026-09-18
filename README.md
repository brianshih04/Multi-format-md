# Enterprise Multi-Format to Markdown Pipeline

將 PDF、Word、Excel、PowerPoint 與純文字文件遞迴轉換成適合匯入 AnythingLLM 的結構化 Markdown。程式會保留來源目錄層級，並透過 Manifest 只重做內容有變動的文件。

## 支援格式

- PDF：提取原生文字、內嵌圖片、偵測到的表格截圖，以及掃描頁／圖形密集頁面。
- DOCX：依文件順序提取標題、段落、表格與內嵌圖片。
- XLSX：逐工作表輸出 Markdown Table，保留公式文字。
- PPTX：提取文字、表格、圖表資料與圖片；若 LibreOffice 可用，另將含視覺結構的投影片交由 VLM 解讀。
- TXT：支援 UTF-8、UTF-16、Big5/CP950 與 CP1252 的常見文字檔。
- DOC、XLS、PPT：先以 LibreOffice 轉成現代格式，再交給對應解析器。

## 環境需求

- Python 3.10+
- [LibreOffice](https://www.libreoffice.org/download/download-libreoffice/)：舊版 `.doc`、`.xls`、`.ppt` 必須使用。PPTX 即使沒有 LibreOffice 仍可提取內容，但無法建立完整投影片預覽。
- DeepSeek API Key：只有文件含有圖片或需要頁面視覺分析時才會呼叫 API。

確認 LibreOffice CLI：

```bash
soffice --version
```

Windows 若沒有把 LibreOffice 加入 PATH，程式也會檢查預設安裝位置：

```text
C:\Program Files\LibreOffice\program\soffice.exe
```

## 安裝

建議建立虛擬環境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS / Linux：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

在本機 `.env` 填入 `DEEPSEEK_API_KEY`。`.env` 已列入 `.gitignore`，請勿提交金鑰。

## 使用方式

### Windows 11 GUI（建議）

第一次使用，在專案資料夾按右鍵選擇「在終端機中開啟」，執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

完成後雙擊 `run_gui.bat`。GUI 提供：

- 拖放多個檔案或資料夾，並可勾選要處理的來源格式。
- 選擇輸出目錄，以及 Markdown、純文字或 JSON 輸出。
- 遮罩式 API Key 欄位；GUI 不會儲存輸入的金鑰。
- 可編輯 Base URL，支援 DeepSeek 官方或其他 OpenAI-compatible 端點。
- 使用 `/models` 自動查詢可用 LLM/VLM，再由使用者從下拉選單挑選；端點若未支援模型清單，仍可手動輸入模型 ID。
- 背景轉換、進度列、即時結果與錯誤摘要。

若 `.env` 或 Windows 環境已有 `DEEPSEEK_API_KEY`，API Key 欄位可留白。模型清單查詢會使用目前輸入的 Base URL 與金鑰。

### CLI

```bash
python doc_to_md_pipeline.py \
  --input-dir ./raw_documents \
  --output-dir ./anythingllm_knowledge_base \
  --workers 4 \
  --output-format md
```

PowerShell 可寫成：

```powershell
python .\doc_to_md_pipeline.py `
  --input-dir .\raw_documents `
  --output-dir .\anythingllm_knowledge_base `
  --workers 4
```

強制重新處理所有文件：

```bash
python doc_to_md_pipeline.py --input-dir ./raw_documents --output-dir ./anythingllm_knowledge_base --force
```

目前 DeepSeek V4.1 Flash 的正式 API 模型名稱是 `deepseek-flash`。如服務端日後改名，可直接覆寫：

```bash
python doc_to_md_pipeline.py \
  --input-dir ./raw_documents \
  --output-dir ./anythingllm_knowledge_base \
  --model deepseek-flash \
  --base-url https://api.deepseek.com
```

## 增量處理

輸出根目錄的 `.conversion_manifest.json` 記錄來源 SHA-256、修改時間、目標路徑、狀態與轉換時間。

1. `mtime`、成功狀態、輸出路徑都相同且 Markdown 存在：不計算雜湊，直接略過。
2. `mtime` 改變時才計算 SHA-256；內容相同則只更新 `mtime`。
3. 內容改變、輸出遺失、前次失敗或指定 `--force`：重新轉換。
4. 每完成一個文件就以原子寫入方式更新 Manifest；單一文件失敗不會中止整批作業。

不同格式若同目錄下使用相同檔名（例如 `report.pdf` 與 `report.docx`），輸出會自動命名為 `report.pdf.md` 與 `report.docx.md`，避免互相覆寫。

## 輸出與錯誤

每份 Markdown 都包含：

```yaml
---
original_file: "hardware/soc_spec.pdf"
converted_date: "2026-09-18T10:00:00Z"
model: "deepseek-flash"
---
```

檔案級錯誤與不影響完成的警告會寫入輸出根目錄的 `conversion_error.log`。CLI 最後會列出掃描、略過、成功、失敗與 VLM 圖片請求數；只要有文件失敗，程序結束碼就是 `1`。

## 測試

```bash
python -m unittest discover -s tests -v
```

測試涵蓋首次處理、`mtime` 快速略過、雜湊略過、內容變更、輸出遺失、強制處理及同名輸出防碰撞。

## 建立 Windows 應用程式

如需不顯示 Python 終端視窗的可攜執行檔，執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

產物位於 `dist\MultiFormatMarkdown\MultiFormatMarkdown.exe`。LibreOffice 仍需另外安裝在使用者電腦上，才能處理舊版 Office 格式與完整投影片預覽。

## API 相容性

本專案依 DeepSeek 官方 OpenAI-compatible Chat Completions 格式傳送 Base64 PNG，並對 HTTP 429、5xx、連線與逾時錯誤進行最多 5 次指數退避重試。官方參考：

- [DeepSeek Vision](https://api-docs.deepseek.com/guides/vision/)
- [DeepSeek API quick start](https://api-docs.deepseek.com/)
- [DeepSeek Lists Models](https://api-docs.deepseek.com/api/list-models/)
