# Installation Guide

本文件說明如何在 Windows 11 安裝、設定、驗證及打包 Multi-Format to Markdown Pipeline。專案主要針對 Windows GUI 使用情境設計；macOS 與 Linux 可使用相同 Python CLI。

## 1. 系統需求

### 必要元件

- Windows 11 64-bit
- Python 3.10 或更新版本
- Git（若使用 `git clone` 下載）
- 可存取所選 OpenAI-compatible API 端點的網路連線（只有視覺內容需要）

### LibreOffice

處理下列功能時需要 [LibreOffice](https://www.libreoffice.org/download/download-libreoffice/)：

- `.doc` 轉 `.docx`
- `.xls` 轉 `.xlsx`
- `.ppt` 轉 `.pptx`
- 建立完整 PPTX 投影片預覽供 Vision 模型分析

程式會依序尋找：

1. PATH 中的 `soffice` 或 `libreoffice`
2. `C:\Program Files\LibreOffice\program\soffice.exe`
3. `C:\Program Files (x86)\LibreOffice\program\soffice.exe`

因此使用預設安裝位置時，不一定需要手動修改 PATH。

## 2. 取得專案

在 PowerShell 執行：

```powershell
git clone https://github.com/brianshih04/Multi-format-md.git
Set-Location .\Multi-format-md
```

如果沒有 Git，也可以在 GitHub 頁面選擇 **Code → Download ZIP**，解壓縮後從該資料夾開啟 PowerShell。

## 3. Windows 自動安裝

在專案根目錄執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

腳本會：

1. 優先使用 Windows Python Launcher `py`，否則使用 `python`，並確認版本至少為 3.10。
2. 建立專案專用的 `.venv`。
3. 更新虛擬環境內的 pip。
4. 安裝 `requirements.txt` 中的所有依賴。

安裝不會修改全域 Python 套件。

## 4. 手動安裝

若不使用安裝腳本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果 PowerShell 阻擋虛擬環境啟用，可只對目前程序放寬限制：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

也可以不啟用虛擬環境，直接使用完整路徑：

```powershell
.\.venv\Scripts\python.exe --version
```

## 5. 驗證安裝

### Python 與依賴

```powershell
.\.venv\Scripts\python.exe -c "import pymupdf, docx, openpyxl, pandas, pptx, PIL, openai, tkinter; print('Dependencies OK')"
```

### LibreOffice

使用程式本身的搜尋邏輯驗證：

```powershell
.\.venv\Scripts\python.exe -c "import doc_to_md_pipeline as p; print(p.find_soffice() or 'LibreOffice not found')"
```

若輸出 `LibreOffice not found`：

1. 確認 LibreOffice 已完成安裝。
2. 關閉並重新開啟 PowerShell。
3. 確認 `soffice.exe` 位於上述預設路徑，或把其目錄加入 PATH。

### 自動測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

安裝 LibreOffice 時，測試會額外建立並回讀 `.doc`、`.xls`、`.ppt`，驗證完整舊格式轉換流程。

## 6. API 設定

### 方法 A：在 GUI 輸入

直接在 GUI 的遮罩欄位貼上 API Key。這是最簡單的方式，金鑰只供本次程序使用，GUI 不會自動儲存。

### 方法 B：使用 `.env`

複製範例：

```powershell
Copy-Item .env.example .env
```

編輯 `.env`：

```dotenv
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

注意：

- `.env` 已被 Git 忽略，仍不應透過郵件、聊天或截圖分享。
- CLI 會從 `.env` 讀取 `DEEPSEEK_API_KEY`。
- GUI 也會使用 `.env` 中的 Base URL 與模型作為預設值。
- GUI 欄位中輸入的值會優先於環境中的 API Key。

### 方法 C：Windows 環境變數

只設定目前 PowerShell：

```powershell
$env:DEEPSEEK_API_KEY = "your_api_key_here"
```

不要把真實金鑰寫入可提交的 `.ps1`、`.bat` 或文件。

## 7. 啟動 GUI

最簡單的方式是雙擊：

```text
run_gui.bat
```

或從 PowerShell 啟動：

```powershell
.\.venv\Scripts\python.exe .\doc_to_md_gui.py
```

GUI 啟動後：

1. 加入檔案或資料夾。
2. 選擇輸入格式與輸出格式。
3. 設定輸出資料夾。
4. 輸入 API Key 與 Base URL。
5. 按「查詢模型」取得 `/models` 清單。
6. 選擇支援 Vision 的模型。
7. 按「開始轉換」。

若相容端點未實作 `/models`，模型欄位仍可手動輸入。

## 8. 使用 CLI

基本範例：

```powershell
.\.venv\Scripts\python.exe .\doc_to_md_pipeline.py `
  --input-dir "C:\Documents\raw" `
  --output-dir "C:\Documents\markdown" `
  --workers 4 `
  --output-format md
```

指定相容端點與模型：

```powershell
.\.venv\Scripts\python.exe .\doc_to_md_pipeline.py `
  --input-dir "C:\Documents\raw" `
  --output-dir "C:\Documents\markdown" `
  --base-url "https://api.deepseek.com" `
  --model "deepseek-flash"
```

輸出格式：

- `md`：含 YAML frontmatter 的 Markdown，建議用於 AnythingLLM。
- `txt`：文字檔，正文保留可讀的 Markdown 表格結構。
- `json`：來源中繼資料與 `content_markdown` 欄位。

## 9. 建立 Windows 應用程式

執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

腳本會安裝 `requirements-dev.txt` 中的 PyInstaller，並建立：

```text
dist\MultiFormatMarkdown\MultiFormatMarkdown.exe
```

這是 one-folder 形式；發佈時必須保留整個 `dist\MultiFormatMarkdown` 資料夾，不能只複製 `.exe`。LibreOffice 不會被打包，目標電腦若要處理舊 Office 格式仍需另外安裝。

## 10. 更新

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

再次執行安裝腳本會沿用 `.venv` 並更新缺少的依賴。

## 11. 常見問題

### 找不到 `py` 或 `python`

重新安裝 Python，並在安裝程式勾選 **Add Python to PATH**。安裝後重新開啟 PowerShell。

### 無法執行 PowerShell 腳本

使用一次性的 Bypass，不必永久變更系統政策：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

### 拖放沒有反應

確認 `tkinterdnd2` 已安裝：

```powershell
.\.venv\Scripts\python.exe -m pip show tkinterdnd2
```

即使拖放不可用，仍可使用「選擇檔案」及「選擇資料夾」。

### 查詢模型失敗

檢查：

- API Key 是否正確且未過期。
- Base URL 是否為服務商要求的 API 根路徑。
- 網路或公司代理是否允許連線。
- 相容端點是否實作 `GET /models`。

查詢失敗不會鎖住模型欄位，可直接輸入模型 ID。

### 出現「未設定 DEEPSEEK_API_KEY」

文件包含視覺內容，但目前程序沒有 API Key。請在 GUI 輸入，或設定 `.env`／環境變數後重試。

### 為什麼沒有 VLM 請求

一般 TXT、Excel 表格以及不含圖片的 DOCX 可完全在本機解析。這是正常行為，也能避免不必要的 API 成本。

### 個別文件失敗

檢查輸出目錄的：

```text
conversion_error.log
```

其他文件仍會繼續執行。修正問題後再次執行，Manifest 會重試先前失敗的文件。

### 第二次執行沒有重新轉換

這是增量處理的預期行為。使用 `--force` 或在 GUI 勾選「強制重新轉換」即可忽略 Manifest。

## 12. macOS / Linux

GUI 以 Windows 為主要驗證平台；CLI 可手動安裝：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python doc_to_md_pipeline.py \
  --input-dir ./raw_documents \
  --output-dir ./markdown \
  --output-format md
```

另請使用作業系統的套件管理器安裝 LibreOffice，並確認 `soffice` 或 `libreoffice` 位於 PATH。

## 13. 移除

刪除專案目錄即可移除程式。若只想重建 Python 環境，可刪除 `.venv` 後重新執行 `setup_windows.ps1`。輸出目錄與來源文件不會被安裝或移除腳本刪除。
