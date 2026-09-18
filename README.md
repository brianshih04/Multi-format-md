# Multi-Format to Markdown Pipeline

在 Windows 11 本機批次將 PDF、Word、Excel、PowerPoint 與文字檔轉換成適合 AnythingLLM、RAG 與知識庫匯入的結構化 Markdown。

專案同時提供拖放式桌面 GUI 與 CLI，能保留來源目錄結構、增量略過未變更文件，並透過可設定的 OpenAI-compatible Vision API 解讀圖片、表格、架構圖與掃描頁。

## 主要功能

- 支援 `PDF`、`DOC`、`DOCX`、`XLS`、`XLSX`、`PPT`、`PPTX`、`TXT` 八種來源格式。
- Windows GUI 支援拖放多個檔案或資料夾。
- 可設定 API Key、Base URL、輸入格式、輸出格式、模型與並行數。
- 自動呼叫目前端點的 `/models` API，讓使用者從實際可用模型中選擇。
- 可選 `ai-enhanced` 模式，在精確解析後由模型整理標題、段落與清單。
- 支援 Markdown、純文字與 JSON 輸出。
- 遞迴掃描並保留原始子資料夾結構。
- 使用 `mtime` 與 SHA-256 Manifest 進行增量更新。
- HTTP 429、5xx、連線與逾時錯誤最多重試五次。
- 個別文件失敗不會中斷整批轉換。
- 舊版 Office 格式透過 LibreOffice 無介面轉檔。

## 格式支援

| 來源 | 處理內容 | 額外需求 |
|---|---|---|
| PDF | 原生文字、圖片、表格截圖、掃描頁及圖形密集頁面 | 視覺內容需要 Vision API |
| DOCX | 標題、段落、表格、內嵌圖片 | 圖片需要 Vision API |
| XLSX | 所有工作表轉為 Markdown Table，保留公式文字 | 無 |
| PPTX | 文字、表格、圖表數值、內嵌圖片及完整投影片視圖 | 完整投影片視圖需要 LibreOffice；視覺分析需要 Vision API |
| TXT | UTF-8、UTF-16、Big5/CP950、CP1252 | 無 |
| DOC / XLS / PPT | 先轉成 DOCX / XLSX / PPTX，再由對應解析器處理 | LibreOffice |

## Windows 11 快速開始

先安裝：

- Python 3.10 或更新版本
- [LibreOffice](https://www.libreoffice.org/download/download-libreoffice/)（舊版 Office 文件必須）

下載並安裝專案：

```powershell
git clone https://github.com/brianshih04/Multi-format-md.git
Set-Location .\Multi-format-md
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

安裝完成後，雙擊 `run_gui.bat`。

完整的環境檢查、API 設定、打包與疑難排解請參考 [installation.md](installation.md)。

## GUI 使用方式

1. 將文件或資料夾拖放到輸入區，也可使用「選擇檔案」或「選擇資料夾」。
2. 勾選需要處理的來源格式。
3. 選擇輸出目錄、輸出格式與轉換模式。
4. 輸入 API Key 與 Base URL。
5. 按「查詢模型」，或展開模型選單，自動取得端點目前提供的模型。
6. 選擇模型後按「開始轉換」。

預設 DeepSeek 設定：

```text
Base URL: https://api.deepseek.com
Model:    deepseek-flash
```

API Key 欄位使用遮罩顯示，GUI 不會自行儲存輸入內容。在預設 `hybrid` 模式下，只有需要視覺分析的內容會發送圖片請求；`ai-enhanced` 模式則會另外把擷取後的非表格文字分段傳送到 API。

### 轉換模式

- `hybrid`（預設）：本機提取文字與表格，只有圖片、掃描頁、圖表及完整投影片視圖交給 Vision API。
- `ai-enhanced`：完成 hybrid 流程後，再由所選模型整理 Markdown 的標題層級、段落與清單。Markdown 表格及 code fence 保持原樣；若數值、URL、Email、識別碼或內容長度驗證失敗，該段自動退回原文並記錄警告。

AI Enhanced 以約 24,000 字元分段處理，因此一份大型文件可能產生多次文字 API 請求。它不會摘要或刻意縮短內容，但模型服務仍可能看到文件中的文字資料。

## CLI 使用方式

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe .\doc_to_md_pipeline.py `
  --input-dir "C:\Documents\raw" `
  --output-dir "C:\Documents\anythingllm" `
  --workers 4 `
  --output-format md `
  --processing-mode hybrid `
  --base-url "https://api.deepseek.com" `
  --model "deepseek-flash"
```

支援的參數：

| 參數 | 說明 |
|---|---|
| `--input-dir` | 要遞迴掃描的來源根目錄 |
| `--output-dir` | 轉換結果、Manifest 與錯誤記錄的輸出目錄 |
| `--workers` | 並行處理數，預設為 `4` |
| `--output-format` | `md`、`txt` 或 `json`，預設為 `md` |
| `--processing-mode` | `hybrid` 或 `ai-enhanced`，預設為 `hybrid` |
| `--model` | Vision 模型 ID，預設為 `deepseek-flash` |
| `--base-url` | OpenAI-compatible API Base URL |
| `--force` | 忽略 Manifest 並重新處理所有文件 |

強制重建全部輸出：

```powershell
.\.venv\Scripts\python.exe .\doc_to_md_pipeline.py `
  --input-dir "C:\Documents\raw" `
  --output-dir "C:\Documents\anythingllm" `
  --force
```

## 增量更新

輸出根目錄會建立 `.conversion_manifest.json`：

1. 修改時間、成功狀態、模型、端點、格式與輸出位置都相同：直接略過，不重新計算雜湊。
2. 只有修改時間改變：計算 SHA-256；內容相同時只更新 Manifest。
3. 內容、模型、Base URL、轉換模式或輸出格式改變，或輸出遺失、前次失敗：重新轉換。
4. 每完成一份文件就原子更新 Manifest，意外中止時仍保留已完成進度。

同一目錄若有 `report.pdf` 與 `report.docx`，輸出會自動使用 `report.pdf.md` 與 `report.docx.md`，避免覆寫。

## 輸出內容

Markdown 會包含來源追蹤資訊：

```yaml
---
original_file: "hardware/soc_spec.pdf"
converted_date: "2026-09-18T10:00:00Z"
model: "deepseek-flash"
processing_mode: "hybrid"
---
```

錯誤與非致命警告會寫入輸出目錄的 `conversion_error.log`。CLI 與 GUI 都會顯示掃描、略過、成功、失敗、VLM 圖片請求數及 AI 整理請求數。

## 隱私與憑證

- 文件解析在本機執行。
- `hybrid` 模式只傳送擷取出的視覺內容；`ai-enhanced` 會另外傳送擷取後的非表格文字。
- API Key 不會寫入 Markdown、Manifest 或錯誤日誌。
- `.env`、本機測試輸出、虛擬環境與打包產物均由 `.gitignore` 排除。
- 請勿把含公司或個人資料的轉換輸出提交到公開儲存庫。

## 測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

目前測試涵蓋：

- 增量更新、雜湊略過、強制處理與輸出遺失。
- 模型變更觸發重新轉換。
- 同名來源的輸出防碰撞。
- PDF、DOCX、XLSX、PPTX、TXT 解析。
- 模型清單查詢與 JSON 輸出。
- AI Enhanced 分段、表格保護、數值驗證與不安全結果回退。
- LibreOffice 可用時，實際執行 DOC、XLS、PPT 往返整合測試。

### Windows 11 實機驗證

2026-09-18 使用一組實際週報資料執行端對端驗證：

- 來源共 12 份文件（3 個 DOCX、9 個 XLSX），全部成功轉換，失敗、警告及圖片請求皆為 0。
- `ai-enhanced` 使用 `deepseek-flash` 產生 4 次非表格文字整理請求：3 次來自 DOCX 段落，另 1 次來自 XLSX 的「工作表標題＋空白工作表」標記；Markdown 表格全程保留在本機處理。
- 空白工作表標記經 AI 處理後沒有內容變化；這項實測數據用於辨識後續可減少的不必要請求。
- 產生 12 份含正確 frontmatter 的 Markdown，Manifest 也包含 12 筆成功狀態。
- 未修改來源直接執行第二次時，12 份全部由 Manifest 略過，AI 請求數為 0。

實際測試文件、轉換結果、API Key 與內部路徑均不納入公開儲存庫。

## 專案結構

```text
doc_to_md_gui.py       Windows 桌面 GUI
doc_to_md_pipeline.py  CLI、掃描、解析、Vision API 與增量處理
setup_windows.ps1      建立虛擬環境並安裝執行依賴
run_gui.bat            雙擊啟動 GUI
build_windows.ps1      使用 PyInstaller 建立 Windows 應用程式
requirements.txt       執行依賴
requirements-dev.txt   打包依賴
installation.md        完整安裝與疑難排解
spec.md                功能規格
tests/                 自動測試
```

## 參考文件

- [完整安裝指南](installation.md)
- [功能規格](spec.md)
- [DeepSeek Vision](https://api-docs.deepseek.com/guides/vision/)
- [DeepSeek Models API](https://api-docs.deepseek.com/api/list-models/)
- [DeepSeek API Quick Start](https://api-docs.deepseek.com/)
