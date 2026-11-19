# 評閱報告與資料契約v1

## 人可閱讀的報告

先寫任務、版本、文件類型及階段，列出讀取／未讀取材料、原始需求是否取得及版面檢查依據。評分前先呈現全案脈絡摘要：整體用途、對象與時序、主要章節如何接續、個人／小組或其他責任單位，以及目標到證據及評量的關係。不得以「完整理解」四字取代內容。

原文與隨附PDF的文字比對只證明該次比對的涵蓋範圍；不要外推為即時Word分頁相同。若先前已看過評語或分數，記錄限制，不宣稱盲評。

然後呈現：

|向度|權重|0～4級分／未知|加權得分|具體位置、證據與理由|
|---|---:|---|---:|---|

每個降低的級分須說明錨點，以及相鄰較高級為何不足以反映納入反證後的功能影響。

問題表：`ID｜裁決類型｜位置與證據｜跨章反證與回查結果｜剩餘影響｜主要向度｜程度｜是否作扣分依據與理由｜修改要求｜通過條件`。欄位太寬時，使用短表配逐項段落，保留這些資訊即可。

裁決類型為已確認錯誤／設計缺漏、說明或銜接不清、待查、改進建議。反證欄記錄查過哪些相關段落、找到什麼及為何問題仍成立；已被其他章節解決的疑點撤銷，不放進扣分清單。待查與建議分區呈現且不扣分。
程度為blocking／major／minor／advisory。blocking為已確認的核心使用阻斷；其他分別是實質修訂、局部修訂、可選建議。

末尾列已符合優點、待查事項與重評需補材料。分數是工作規準下的判斷，不宣稱測得教學成效或正式法規合規。

批次報告逐組呈現任務條件、等級分布、分項平均、可排名清單及暫不排名者；共同缺失按每份文件是否出現計數。不同任務不排同榜。

## JSON輸入

使用UTF-8。`rubric.weights`的五項ID固定為R、C、E、U、F，總和100；自訂權重需另命名規準版本。`reviews`每份只放目前評閱版本，`submission_id`全檔唯一，避免原稿修訂稿被算成兩位學員。

```json
{
  "schema_version": 1,
  "rubric": {
    "version": "education-review-1.0",
    "weights": {
      "R": 20,
      "C": 15,
      "E": 25,
      "U": 25,
      "F": 15
    }
  },
  "reviews": [
    {
      "submission_id": "S01",
      "revision": "v1",
      "reviewer_id": "reviewer-1",
      "review_mode": "single-agent",
      "comparison": {
        "task_id": "reading-01",
        "document_type": "lesson-plan",
        "stage": "planning",
        "requirements_id": "brief-v1",
        "template_id": "template-01"
      },
      "criteria": {
        "R": {
          "level": 4,
          "reason": "需求吻合",
          "evidence": [
            {
              "location": "基本資料",
              "quote": "五年級40分鐘",
              "judgment": "符合任務"
            }
          ]
        },
        "C": {
          "level": 4,
          "reason": "必要欄位齊備",
          "evidence": [
            {
              "location": "正文與附表",
              "quote": "目標、流程、評量",
              "judgment": "可定位必要部分"
            }
          ]
        },
        "E": {
          "level": 4,
          "reason": "計算一致",
          "evidence": [
            {
              "location": "流程",
              "quote": "5+25+10=40",
              "judgment": "與總時間一致"
            }
          ]
        },
        "U": {
          "level": 3,
          "reason": "流程已有兩份文本比較；只有評量未明確描述引用線索，影響局部判分，未達4級可操作程度。既有核心任務可用，依U3而非需新增核心設計的U2。",
          "evidence": [
            {
              "location": "評量欄",
              "quote": "比較兩份文本",
              "judgment": "需更明確的達標描述"
            }
          ]
        },
        "F": {
          "level": null,
          "reason": "未取得最終版面",
          "evidence": []
        }
      },
      "issues": [
        {
          "id": "I01",
          "category": "assessment-clarity",
          "severity": "minor",
          "primary_dimension": "U",
          "location": "評量欄",
          "evidence": "比較任務沒有區分是否引用證據",
          "impact": "教師需自行補判準",
          "required_change": "補寫比較與引用依據的達標行為",
          "acceptance": "兩種不同品質作答能依描述區分",
          "finding_type": "說明或銜接不清",
          "counterevidence": "回查流程已有比較兩份文本的步驟；缺口限於評量判準，並非缺少比較任務。",
          "deduction_basis": "局部判準待補支持U3，無須重設核心流程，不支持U2。",
          "deduction_applied": true
        }
      ],
      "blockers": [],
      "verification_gaps": [
        "未檢視Word版面"
      ],
      "strengths": [
        "時數與主題符合任務"
      ]
    }
  ]
}
```

每個可評向度必須有非空理由、至少一筆`location`、`quote`與`judgment`；quote也可為明確的結構／計算觀察，不捏造逐字引言。降級時在`reason`記錄反證裁決、功能影響及相鄰較高級不適用的理由。未知向度保留原因。

JSON維持`schema_version: 1`相容既有資料。新版報告的問題可另外保存`finding_type`、`counterevidence`、`deduction_basis`及`deduction_applied`欄位；待查或建議的`deduction_applied`為false。現有程式會保留問題物件的額外欄位，但不驗證其語義，也不強制檢查這些補充欄位。脈絡摘要與完整裁決仍須交付人可閱讀的報告，不能僅交計分輸出充當完成全文理解。

`blockers`只引用`severity=blocking`的問題，格式為`{"issue_id":"I01","verified":true}`。有blocking問題而未列入blockers會被拒絕，避免高分掩蓋阻斷；無證據的blocking同樣拒絕。

腳本輸出不證明語義正確，也不驗證是否完成全文閱讀、跨章反證或嚴重程度判定。給分、查證和問題判讀需評閱者完成；程式只檢查契約及重算。完成資料可以改為0～100的任務權重，不能把另一來源的換分表隱性套入。
