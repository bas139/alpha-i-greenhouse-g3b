# iDekTep Alpha-I Coding for AI Tournament 2026 — Project Documentation
**Case:** `c.grh` — Greenhouse Environment State Classification  
**Team Name / ID:** `3B` (Client ID: `G3B`)

---

## 1. ภาพรวมระบบและสถาปัตยกรรม (System Overview & Architecture)

ระบบจำแนกสภาพแวดล้อมโรงเรือนอัจฉริยะแบบเรียลไทม์ รับข้อมูลเซ็นเซอร์ 4 ตัว (`temperature_celsius`, `humidity_percentage`, `lux_lumen`, `CO2_ppm`) ผ่าน MQTT Broker แล้วทำนายสถานะออกเป็น 3 ระดับ:
* **`0` — `Normal_state`:** สภาพแวดล้อมปกติ
* **`1` — `Alert_state`:** เริ่มมีความเสี่ยง ควรเฝ้าระวัง
* **`2` — `Alarm_state`:** ผิดปกติระดับเตือนภัย

```
┌────────────────────────┐   MQTT (192.168.1.1:1883)
│  Phase 1 Collector     │   Topic: idt/cpt/grh/publish-test
│  subscriber.ipynb      ├──────────────────────────────────────► data/TRAIN.csv (800 rows)
└────────────────────────┘                                        data/test.csv  (500 rows)
                                                                         │
                                                                         ▼
┌────────────────────────┐   Anti-Overfit GAM+DT Distillation     ┌──────────────┐
│  train_model.ipynb     ├───────────────────────────────────────►│ model.joblib │ (DecisionTreeClassifier,
└────────────────────────┘   Zero Test/Val Leakage                └──────┬───────┘  195 leaves, 34.7 KB)
                                                                         │
┌────────────────────────┐   MQTTv5 QoS=1                         ┌──────▼──────────────┐
│  Competition Stream    │   idt/cpt/grh/ucdts-publish            │  rt_prediction.py   │
│  (192.168.1.1:1883)    ├───────────────────────────────────────►│  (Client ID: G3B)   │
└────────────────────────┘                                        └──┬───────────────┬──┘
                                                                     │               │
                             Logs 500 rows (0 nulls, 0 dupes)        ▼               ▼  Publishes idt/cd-alp/G3B
                                                       p2_prediction.csv    ┌──────────────────────────────┐
                                                                            │ Node-RED Dashboard (Port1880)│
                                                                            │ 4 Gauges | 3 Charts | 3 LEDs │
                                                                            │ AI State & Confidence | Reset│
                                                                            └──────────────────────────────┘
```

---

## 2. แนวทางการพัฒนาโมเดลและการป้องกัน Overfitting (Part 1 Methodology)

### 2.1 โครงสร้างโมเดลที่ส่งมอบ (`model.joblib`)
* **โมเดลปลายทาง:** `sklearn.tree.DecisionTreeClassifier` แท้ต้นเดียว (`criterion="entropy"`, `max_depth=12`, `min_samples_split=16`, `min_samples_leaf=8`, `ccp_alpha=0.00004`, `random_state=42`)
* **ขนาดและความเร็ว:** `195` leaves (`depth = 12`), ขนาดไฟล์ **`34.7 KB`** (`35,553` bytes) ใช้เวลาทำนายระดับ sub-millisecond ต่อแถวบน CPU

### 2.2 เทคนิค Anti-Overfit GAM+DT Soft-Distilled Born-Again Decision Tree
ข้อมูลเซ็นเซอร์โรงเรือนมีความเสี่ยงที่เพิ่มขึ้นอย่างต่อเนื่องตามแนวแกนและมี noise บริเวณเส้นแบ่ง หากเทรน `DecisionTreeClassifier` ต้นเดียวแบบปกติจะมีเส้นแบ่งเป็นขั้นบันไดหยาบและความน่าจะเป็น (probability) ไม่เรียบ (`Log-Loss` สูง) จึงออกแบบกระบวนการเทรนใน `train_model.ipynb` ดังนี้:
1. **Teacher Committee (เทรนเฉพาะบนข้อมูลชุดฝึก 100% ปราศจาก Data Leakage):**
   * **50% Cubic-Spline Additive GAM:** `SplineTransformer(n_knots=6, degree=3, knots="uniform") + LogisticRegression(C=10.0)` จับแนวโน้มความเสี่ยงแบบเรียบในแต่ละเซ็นเซอร์ ลด variance บริเวณขอบเขต
   * **50% Regularized Bootstrap Decision Tree Ensemble:** คณะ `DecisionTreeClassifier` `200` ต้น (`min_samples_leaf=6`, `max_features=3`) จับจุดตัดเฉพาะและอันตรกิริยาแบบ non-linear ระหว่างเซ็นเซอร์
2. **Soft Knowledge Distillation (`40,000` จุดในขอบเขตข้อมูลฝึก):** คำนวณค่าความน่าจะเป็นเฉลี่ยแบบ soft posterior จาก Teacher ทั้งสองฝั่ง แล้วกลั่น (distill) ลงใน **`DecisionTreeClassifier` เพียงต้นเดียว** พร้อมตัดแต่งด้วย `ccp_alpha=0.00004` และจำกัด `min_samples_leaf=8`

### 2.3 ผลการประเมินผล (Verified Evaluation Results)

| ชุดข้อมูล | จำนวนแถว | Macro-F1 | Accuracy | Log-Loss | Per-Class F1 (`Normal / Alert / Alarm`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **80/20 Validation Set** | `160` | **`0.8799`** | **`90.00%`** | **`0.2768`** | `0.9400` / `0.8049` / `0.8947` |
| **Full Training (`data/TRAIN.csv`)** | `800` | `0.8851` | `91.13%` | `0.2199` | `0.9531` / `0.8349` / `0.8673` |
| **Unseen Test (`data/test.csv`)** | **`500`** | **`0.8557`** | **`88.60%`** (`443/500`) | **`0.2683`** | **`0.9394` / `0.7574` / `0.8701`** |

* **Confusion Matrix บน Unseen `data/test.csv` (500 แถว):**
  ```
  Rows = True (Normal, Alert, Alarm) | Cols = Predicted
  [[287  12   0]    <- Normal_state : Precision 0.9199 | Recall 0.9599 (ไม่หลุดเป็น Alarm เลย 0 แถว)
   [ 25  89   4]    <- Alert_state  : Precision 0.7607 | Recall 0.7542
   [  0  16  67]]   <- Alarm_state  : Precision 0.9437 | Recall 0.8072 (ไม่หลุดเป็น Normal เลย 0 แถว)
  ```
* **หลักฐานความทนทานและไม่ Overfit:**
  * 5×5 Repeated Stratified CV บน `data/TRAIN.csv` (`120` teachers / `30,000` synth samples) ได้ `CV Macro-F1 = 0.8465 ± 0.0388`, `CV Log-Loss = 0.296` (`cvGap = +0.0474` ลดลงจาก `+0.0622` ก่อนทำ Regularization)
  * ช่องว่างคะแนนระหว่าง Train กับ Validation แคบมาก (`Val gap = +0.0060`) และบน `data/TRAIN.csv` → Unseen 500 แถวมี gap เพียง `+0.0294` พร้อมทดสอบ **Gaussian Noise Stress Test (+5% / +10% noise)** ได้ `Macro-F1 = 0.8660 / 0.8545` (บนชุดทดสอบ 400 แถว สูงกว่าต้นไม้ดั้งเดิม `0.8224`)

---

## 3. ระบบเรียลไทม์และแดชบอร์ด (Part 2 Real-Time & Dashboard)

### 3.1 Real-Time Predictor (`rt_prediction.py`)
* เชื่อมต่อ MQTTv5 (`192.168.1.1:1883`, `CLIENT_ID = "G3B"`, `QoS = 1`, `SessionExpiryInterval = 300s`)
* Subscribe หัวข้อ `idt/cpt/grh/ucdts-publish` → ตรวจสอบความครบถ้วนและค่าจำกัด (`math.isfinite`, non-empty `timestamp`) → ทำนายคลาสและ probability จาก `model.joblib`
* บันทึกลง `p2_prediction.csv` แบบต่อท้ายอัตโนมัติ (`START_NEW_CSV = False`, ป้องกัน timestamp ซ้ำด้วย `seen_timestamps`) และส่งต่อผลลัพธ์ไปยัง Node-RED ผ่านหัวข้อ `idt/cd-alp/G3B`

### 3.2 ผลการตรวจสอบไฟล์ผลลัพธ์ Phase 2 (`p2_prediction.csv`)
* **จำนวนแถว:** `500` แถวข้อมูลครบถ้วน + `1` แถวหัวตาราง (`2026-10-16 09:00:00` → `2026-10-16 09:08:19`)
* **ความถูกต้องของสคีมา:** ตรงกับ `case_config.prediction_columns()` 100% (`timestamp`, `temperature_celsius`, `humidity_percentage`, `lux_lumen`, `CO2_ppm`, `y_pred`, `y_label_pred`, `y_pred_prob_Normal_state`, `y_pred_prob_Alert_state`, `y_pred_prob_Alarm_state`)
* **ความสมบูรณ์ของข้อมูล:** `0` missing/null values, `0` duplicate timestamps, ผลรวม probability ทั้ง 3 คลาสเท่ากับ `1.0` ทุกแถว, `y_pred` ตรงกับ `y_label_pred` 100%
* **สัดส่วนการทำนาย:** `Normal_state`: `302` (`60.4%`) | `Alert_state`: `131` (`26.2%`) | `Alarm_state`: `67` (`13.4%`)

### 3.3 Node-RED Dashboard (`GreenHouse_flow.json` / `IDT-GREENHOUSE-FLOW.json`)
เปิดใช้งานได้ที่ `http://127.0.0.1:1880/ui` ออกแบบธีม **Botanical Smart Greenhouse** เพื่อการอ่านค่าที่ชัดเจน:
* **4 Sensor Gauges (20 คะแนน):**
  * `Temperature` (`0–50 °C`, ช่วงสี `34 / 39`)
  * `Humidity` (`0–100 %`, ช่วงสี `38 / 86`)
  * `CO₂` (`0–2000 ppm`, ช่วงสี `1200 / 1500`)
  * `Light (LUX)` (`0–60000 lm`, ช่วงสี `45000 / 55000`)
* **3 Real-Time Charts (20 คะแนน):** `TEMP_HUMID MONITOR` (2 เส้นกราฟ Temp + Humidity), `LUX MONITOR`, `CO2 MONITOR` โดยทุกจุดใช้ `p.timestamp` จากข้อมูลจริง
* **Prediction Display (5 คะแนน):** ป้ายสถานะ `AI Prediction` แยกสี (`เขียว / เหลือง / แดงกระพริบเตือน`) + แถบ `MODEL CONFIDENCE` แสดง `%` ความมั่นใจทั้ง 3 คลาสและ timestamp ล่าสุด
* **3 Status LEDs (5 คะแนน):** ไฟสถานะ `Normal` (`#10b981`), `Alert` (`#f59e0b`), `Alarm` (`#ef4444`)
* **Control & Dual-Schema Support:** ปุ่ม **↻ RESET DASHBOARD** ล้างทุกกราฟ เกจ ไฟ LED และข้อความสถานะให้พร้อมเริ่มรอบใหม่ พร้อมรองรับทั้งคอลัมน์/label แบบใหม่ (`temperature_celsius`, `Normal_state`, `y_pred_prob_Normal_state`) และแบบเก่า (`temp_c`, `normal`, `y_pred_prob_normal`)

---

## 4. การป้องกัน 5 ข้อผิดพลาดที่พบบ่อย (Risk Mitigation)

| ข้อผิดพลาดตามเกณฑ์ | แนวทางป้องกันที่ใช้จริงในโปรเจกต์ |
| :--- | :--- |
| **1. ข้อมูลไม่พร้อมใช้งาน (รูปแบบผิด/ไม่ต่อเนื่อง/ไม่ครบ)** | `subscriber.ipynb`, `train_model.ipynb` และ `rt_prediction.py` ตรวจสอบชื่อคอลัมน์จาก `case_config.py`, ตัดช่องว่างชื่อคอลัมน์, กรองค่า `NaN`/`±Inf`, และกัน timestamp ซ้ำอัตโนมัติ (ตรวจสอบ `p2_prediction.csv` แล้วได้ 500/500 แถว 0 nulls 0 dupes) |
| **2. โมเดลไม่ทั่วไป (Overfitting)** | แยก Train/Validation ด้วย Stratified Split ก่อนทำ Distillation เสมอ ไม่นำ `test.csv` มาเทรนเด็ดขาด ใช้ GAM+DT Soft Distillation + `ccp_alpha` pruning ลด Validation gap เหลือ `+0.0060` และรักษา Macro-F1 บน Noise stress-test |
| **3. แดชบอร์ดสื่อสารผิดพลาด** | จัดกลุ่มชัดเจน แยกสีตามความรุนแรง (`เขียว/เหลือง/แดง`), แสดงค่าความมั่นใจ % และ timestamp จริงควบคู่กัน, กราฟแยก 3 หมวดชัดเจนไม่ซ้อนปนสเกล (Temp+Humidity / Lux / CO₂) |
| **4. ละเลยการตรวจสอบความถูกต้อง** | ทดสอบครบทั้ง 5×5 Stratified CV, 20% Holdout Validation, Unseen `test.csv` 500 แถว, Unit-Test ฟังก์ชัน Node-RED ด้วย `node`, และการตรวจคุณภาพ `p2_prediction.csv` หลังจบรอบจริง |
| **5. ไม่เข้าใจผู้ใช้งานจริง** | ออกแบบ Dashboard อ่านง่ายสำหรับผู้คุมโรงเรือน มีปุ่ม **↻ RESET DASHBOARD**, ป้าย Alarm แบบ pulse เตือนสายตา, แถบความมั่นใจช่วยให้ตัดสินใจหน้างานได้, และ `rt_prediction.py` รองรับการรันต่ออัตโนมัติหากเครือข่ายสะดุด |

---

## 5. คู่มือการใช้งานและรายการไฟล์ในแพ็กเกจ (Usage Guide & Package Contents)

### 5.1 รายการไฟล์ในแพ็กเกจส่งงาน (`G3B_Submission`)
* `README.md` — สรุปข้อมูลทีม โครงสร้างไฟล์ Runbook วันแข่ง และวิธีติดตั้งสภาพแวดล้อม
* `DOCUMENTATION.md` — เอกสารอธิบายแนวทาง สถาปัตยกรรม รายละเอียดโมเดล แดชบอร์ด และการตรวจสอบครบชุด
* `case_config.py` — ไฟล์กำหนดโครงสร้างคอลัมน์และคลาสกลาง (`c.grh`)
* `subscriber.ipynb` — โน้ตบุ๊กเก็บข้อมูล MQTT → `data/TRAIN.csv`, `data/test.csv`
* `train_model.ipynb` — โน้ตบุ๊กเทรนและประเมินผล `DecisionTreeClassifier` → `model.joblib`
* `rt_prediction.py` — สคริปต์ทำนายผลเรียลไทม์ MQTT + บันทึก CSV + ส่งต่อ Node-RED
* `model.joblib` — ไฟล์โมเดล `DecisionTreeClassifier` ที่เทรนพร้อมใช้งาน (`34.7 KB`)
* `p2_prediction.csv` — ผลลัพธ์การทำนายเรียลไทม์ Phase 2 (`500` แถวสมบูรณ์)
* `GreenHouse_flow.json` / `IDT-GREENHOUSE-FLOW.json` — ไฟล์ Import สำหรับ Node-RED Dashboard
* `team3B_training_submit.csv` / `team3B_testing_submit.csv` — ประวัติบันทึกคะแนน Validation & Test
* `data/TRAIN.csv` (`800` แถว) & `data/test.csv` (`500` แถว) — ชุดข้อมูลฝึกและทดสอบ

### 5.2 ขั้นตอนการใช้งานซ้ำ (Quick Start)
```powershell
# 1. เปิดใช้งานสภาพแวดล้อม Python (ในโฟลเดอร์โปรเจกต์)
.venv\Scripts\activate

# 2. (กรณีต้องฝึกโมเดลใหม่) เปิดรัน train_model.ipynb ทั้ง 2 เซลล์เพื่อสร้างและทดสอบ model.joblib

# 3. เปิด Node-RED และ Import ไฟล์ GreenHouse_flow.json จากนั้น Deploy แล้วเปิดหน้า Dashboard
node-red   # เปิด http://127.0.0.1:1880/ui และกดปุ่ม "↻ RESET DASHBOARD"

# 4. รันระบบทำนายผลเรียลไทม์ Phase 2 (ตรวจสอบ MQTT_CONFIG ใน rt_prediction.py ก่อน)
python rt_prediction.py
```
