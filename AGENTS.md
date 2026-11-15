These AGENTS.md instructions replace all previously provided AGENTS.md instructions.

# 必須遵守的規則 MANDATORY RULES（最高優先，不可略過）

以下規則是使用者明確要求、**每一次都必須遵守**的硬性規則，優先於其他預設做法。不可因為趕時間、任務看似簡單或文件很短而略過。
These rules are mandatory and must be followed every time. They take priority over default behavior.

## 規則一：教學文件的雙語中學生標準 Teaching Documents

適用範圍：所有教學相關文件，包括講義、教程、步驟說明、練習題、操作指南、課堂材料、README 教學段落等。

每份教學文件交付前，**必須**通過以下兩個測試：

1. **只懂中文的中學生測試**：模擬一個只懂中文的中學生，把文件看一次、照著做一次。學生必須看得懂，而且能跟著步驟做完。
2. **只懂英文的中學生測試**：模擬一個只懂英文的中學生，學生也必須看得懂，而且能跟著步驟做完。因此教學文件必須有中英對照（或同時提供中文版與英文版），不能只靠其中一種語言才看得懂。

例外：羽毛球（Badminton）相關的教學文件，包括 `~/Desktop/Badminton/` 資料夾內的所有內容，**只需要繁體中文，不需要雙語**。這類文件只做「只懂中文的中學生測試」，不做英文學生測試，也不用加中英對照。

寫法要求：
- 每一步只做一件事，寫清楚要按哪裡、輸入什麼、應該看到什麼結果。
- 專有名詞第一次出現時要解釋，並附上中英文對照。
- 不要跳步驟，不要假設讀者已經懂背景知識。

交付前檢查（必做）：
- 自己扮演兩位學生，各從頭到尾逐步走一遍；有任何看不懂或卡住的地方，先修改再交付。
- 交付時用一行說明已完成「中文學生 / 英文學生」兩項測試，以及修改了哪些卡住的地方。

## 規則二：答案必須驗證 Verify Every Answer

- 給答案前**必須**先驗證，不可隨便給答案。能執行的就實際執行（跑程式、跑測試、重新計算、查原始資料或文件）來確認答案正確。
- 回覆時說明是怎樣驗證的。
- 如果無法驗證，必須明確標示「未驗證」並說明原因，不可當作已確認的答案。

---

## Jev Global Routing

- Use the `jev` skill for repeated yes/no decisions, classification, and scoring over text when useful. It is not for writing, arithmetic, images, or general reasoning.
- Local command: `~/.local/bin/jev`; script: `~/.local/share/jev/claude/scripts/jev.py` (use `/usr/bin/python3`). The installation is local and does not depend on iCloud downloads.
- Try 3–5 representative rows before a full batch. Review choice/score answers with confidence below 0.6 and identify Jev results in reports.
- Requests send the supplied text to TypeSafe or OpenRouter. Follow the user's data-sharing instructions; never print or log API keys. Credentials are read from environment variables or macOS Keychain (`jev-typesafe` / `jev-openrouter`).

---

# badminton 網站維護指示

修改前先讀 [網站維護規則](docs/網站維護規則.md)、[網站排版與發佈規範](docs/網站排版與發佈規範.md) 與 [網站優化決策紀錄](docs/網站優化決策紀錄.md)。本段保存其他網站任務要求，在上方最新強制規則及羽毛球例外下套用。

## 使用者的固定要求

- **分眾：`learn/` 對象為國一至國三／F1–F3 學生，手機優先；`technology/` 對象為教練，著重訓練應用、量測可信度、使用條件與成本。**
- **羽毛球專案只需繁體中文，只做中文中學生逐步測試；英文測試依 P24 例外不適用。** 語氣清楚、有成長目標、適合中學生。網站定位為「小選手，大目標」，以國際賽場為長遠方向；學生學習頁本期聚焦五項基礎細節；科技頁使用教練分析語氣。
- `learn/` 先提供重點，再按需要展開細節；每項包含一句提示、具體練習與可記錄的檢查。保留圖片、對照表、關聯圖與 Markdown 文字版。
- **推薦來源須免費公開觀看，學生不需要信用卡、付費會員或購買課程。** 影片頁打得開、HTTP 200、有縮圖或頻道有「加入」按鈕，都不足以判斷。
- 保留使用者歷來的優化要求。新要求追加記錄；修改舊規則時保留歷史並註明取代關係。使用者最新明確要求優先，不得把歷史錯字恢復成現在設定。

## 交付與驗證

- 本專案適用羽毛球例外：只做中文學生測試。不要把一般文件的雙語要求套回此專案。
- 教學步驟一次一件事，說明操作、輸入及預期結果；首次出現的專有名詞以繁體中文解釋。
- 交付前以中文中學生身分從頭閱讀並逐步照做，卡住先修正；回覆指出測試範圍和修正。
- 每個答案先驗證，回覆交代方法；無法核實的明確標為「未驗證」及原因。

## 修改與來源

- 同步維護本機教學來源、此期 `index.html`、同目錄的 `學習精華_瀏覽版.html`、共享樣式／腳本、相關 Markdown 與圖片。不要只改其中一份。
- `learn/` 學生入口預設一次顯示一個細節；較長的來源、教練備註與限制可展開閱讀。按鈕與文字不可在窄螢幕溢出，底部捷徑不可遮住操作。
- 新增或替換影片時，記錄影片 ID、未登入播放權限、核對日期、內容依據與精確片段。會員或權限不明的影片不列入學生推薦。
- 引用片段改變時，要重整相關練法、適用情境、時間、圖片、索引與試練標記；不能只換網址沿用不相符的內容。
- 較早發布的補充影片標明年份，不計作本月新片。區分已讀字幕、僅讀簡介／章節與尚未核實內容；區分原片內容和本頁編製的練習建議。
- 使用者提示原文保存在本機工作區的「網站維護」資料夾。此儲存庫保存整理後的長期規則和決策紀錄；不要把本機個人路徑、憑證或對話工具輸出加入網站。

## 版本與部署

- 儲存庫：`WingLao/badminton`。GitHub Pages 使用 `main` 分支根目錄。目前路徑全部小寫：`learn/badminton-2026-11-15/` 與 `technology/badminton-2026-11-15/`。P23 已取代早期大寫路徑。
- 頁面：https://winglao.github.io/badminton/learn/badminton-2026-11-15/
- 對本網站已授權的例行修改，完成適當檢查後直接提交、推送與部署，不反覆詢問已授權的步驟。
- 完成標準：推送成功、GitHub Pages 工作流程成功、線上網址回應正常且內容符合本次版本。不能只完成本地檔案或回覆建議。
- 有介面修改時檢查手機與桌機尺寸、選題／影片跳轉及相關互動；純文件修改以文件連結、版本和部署檢查為主。
- 保留其他人的既有改動與歷史，先檢查工作區，推送前同步遠端；不要強制推送。
- 使用者要求「打開網站」時，開啟目前已發佈的 HTTPS 頁面，依工具實際結果回報。

## 共用紀錄與教練科技頁

- 追加提示前讀取目前紀錄，使用尚未使用的編號及穩定識別；不得覆蓋其他工作階段已保存的提示。
- 科技頁不是學生小挑戰：保留較完整的比較表、來源依據、訓練應用與成本條件；不把學生沒有信用卡套成教練的條件。
- 科技頁的影片觀看權限與器材／軟體費用分開說明；未驗證的效能、價格或採購結論須標示未驗證。
