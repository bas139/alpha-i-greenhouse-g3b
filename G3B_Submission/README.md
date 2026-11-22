# ALPHA I CODING TOURNAMENT 2026
--

## Team & Project Info
* **Team Name / ID:** 3B (Client ID: `G3B`)
* **Case:** `c.grh` — Greenhouse Environment State
* **Input Features:** `temperature_celsius`, `humidity_percentage`, `lux_lumen`, `CO2_ppm`
* **Target Classes:** `0: Normal_state`, `1: Alert_state`, `2: Alarm_state`
* **MQTT Broker:** `192.168.1.1:1883`
  * Phase 1 Data Collection (`subscriber.ipynb`): `idt/cpt/grh/publish-test` → `data/TRAIN.csv` (`800` rows), `data/test.csv` (`500` rows)
  * Phase 2 Real-time Prediction (`rt_prediction.py`): subscribes `idt/cpt/grh/ucdts-publish` → logs `p2_prediction.csv` (`500` rows) → publishes `idt/cd-alp/G3B`

## Model Methodology & Evaluation Results (Part 1)
* **Algorithm & Artifact:** Pure `DecisionTreeClassifier` saved to `model.joblib` (`195` leaves, `max_depth=12`, `min_samples_split=16`, `min_samples_leaf=8`, `ccp_alpha=0.00004`, `criterion="entropy"`, `random_state=42`, file size `34.7 KB` / `35,553` bytes)
* **Training Approach:** **Anti-Overfit GAM+DT Soft-Distilled Born-Again Decision Tree** (`USE_BORN_AGAIN_DISTILL = True`, `GAM_TEACHER_WEIGHT = 0.50` in `train_model.ipynb`) — blends a regularized cubic-spline Additive GAM (`SplineTransformer(n_knots=6, degree=3, knots="uniform") + LogisticRegression(C=10.0)`) 50/50 with a 200-tree regularized bootstrap committee of pure `DecisionTreeClassifier`s (`min_samples_leaf=6`, `max_features=3`) trained strictly on the training split (zero validation/test leakage), then distills smooth ensemble posteriors over 40,000 domain-bounded samples into one compact `DecisionTreeClassifier`.
* **Verified Evaluation Metrics:**
  * **Validation Split (20%, 160 rows):** Macro-F1 **`0.8799`**, Accuracy **`90.00%`**, Log-Loss **`0.2768`** (Per-class F1: `Normal_state 0.9400`, `Alert_state 0.8049`, `Alarm_state 0.8947`)
  * **Unseen `data/test.csv` (500 rows):** Macro-F1 **`0.8557`**, Accuracy **`88.60%`** (`443/500`), Log-Loss **`0.2683`** (Per-class F1: `Normal_state 0.9394`, `Alert_state 0.7574`, `Alarm_state 0.8701`)
  * **Stability & Anti-Overfit:** On 5×5 Repeated Stratified CV over `data/TRAIN.csv` (`120` teachers / `30,000` synth samples), this configuration achieved CV Macro-F1 **`0.8465`** (`±0.0388`) and CV Log-Loss **`0.296`** (`cvGap +0.0474` vs `+0.0622` prior), with Validation gap only **`+0.0060`**. The exported `model.joblib` is a single lightweight `DecisionTreeClassifier` (`34.7 KB`).

## Real-Time System & Dashboard (Part 2)
* **Live Phase 2 Output (`p2_prediction.csv`):** **`500` rows** (`2026-10-16 09:00:00` → `2026-10-16 09:08:19`), `0` nulls, `0` duplicate timestamps, probability sums `= 1.0`, exact schema match with `case_config.prediction_columns()`, predicted class counts: `Normal_state: 302 (60.4%)`, `Alert_state: 131 (26.2%)`, `Alarm_state: 67 (13.4%)`.
* **Node-RED Flow (`GreenHouse_flow.json` / `IDT-GREENHOUSE-FLOW.json`):** Botanical Smart Greenhouse theme at `http://127.0.0.1:1880/ui` (supports both `*_state` / full feature names and compact legacy keys):
  * **4 Sensor Gauges:** `Temperature` (°C), `Humidity` (%), `CO₂` (ppm), `Light (LUX)` (lm)
  * **3 Real-time Charts:** `TEMP_HUMID MONITOR`, `LUX MONITOR`, `CO2 MONITOR` plotted strictly on data `p.timestamp`
  * **Prediction Display:** AI Prediction status pill + Model Confidence probability bars + latest data timestamp
  * **3 Status LEDs:** `Normal`, `Alert`, `Alarm`
  * **Control:** **↻ RESET DASHBOARD** button clears charts, LEDs, gauges, and prediction card

## Project Files
* `DOCUMENTATION.md` — Full bilingual technical guide (Architecture, Model/Anti-Overfit details, Dashboard Guide, 5 Pitfalls prevention, Usage Runbook)
* `case_config.py` — Shared case schema (`FEATURES`, `CLASS_LABELS`, CSV/probability helpers)
* `subscriber.ipynb` — MQTT v2 data collector with duplicate-timestamp filtering → `data/TRAIN.csv`, `data/test.csv`
* `train_model.ipynb` — Soft-Distilled Born-Again `DecisionTreeClassifier` training & unseen-test evaluation → `model.joblib`, `team3B_training_submit.csv`, `team3B_testing_submit.csv`
* `rt_prediction.py` — Real-time MQTT predictor (`G3B-rt`), finite-value validation, CSV logger (`p2_prediction.csv`), Node-RED forwarder
* `p2_prediction.csv` — Verified 500-row Phase 2 real-time prediction output (`0` nulls, `0` duplicate timestamps)
* `GreenHouse_flow.json` / `IDT-GREENHOUSE-FLOW.json` — Node-RED dashboard flow exports
* `G3B_Submission/` & `G3B_Submission.zip` — Clean, self-contained submission package containing all 15 final deliverables (`backup_G3B_2026.zip` mirrors the same clean archive)

## Phase 2 Usage & Competition-Day Runbook
1. **Collect / Verify Data:** Run `subscriber.ipynb` (with `OVERWRITE_EXISTING = True`) to record clean `data/TRAIN.csv` and `data/test.csv`.
2. **Train & Evaluate Model:** Run Cell 1 & Cell 2 in `train_model.ipynb` (`importlib.reload(cfg)` reloads `case_config.py` automatically) and verify `model.joblib` scores on `data/test.csv`.
3. **Verify MQTT & CSV State:** Confirm `BROKER_HOST`, `TOPIC_IN`, `TOPIC_OUT`, and `START_NEW_CSV` in `rt_prediction.py`, and remove any stale practice `p2_prediction.csv` before starting a new official round.
4. **Reset Dashboard:** Open `http://127.0.0.1:1880/ui` and click **↻ RESET DASHBOARD** before the live stream begins.
5. **Run Phase 2 & Package:** Start `rt_prediction.py` alongside Node-RED until the round completes (`500` rows logged cleanly to `p2_prediction.csv`), then submit `G3B_Submission/` (or `G3B_Submission.zip`).

## Prerequisites
### Main Program
* Visual Studio Code

### Tools / Environment
* Python: 3.13.11
* Node.js: 24.13.0
* Node-RED
* Jupyter (ipykernel, jupyter_client, jupyter_core)

### Libraries
* numpy
* pandas
* scipy
* matplotlib
* scikit-learn
* joblib
* paho-mqtt

## Installation & Setup Environment
### Windows
#### Python 3.13.11
* Download & Install Python 3.13.11 Installer: Follow the instructions below.
```shell
https://www.python.org/downloads/windows/
```
* Verify Python Version:
```shell
python --version # Should print "Python 3.13.11".
```
* Note: Don’t forget to select the "Add Python to PATH" option.
* If you see "Disable path length limit", click it as well.
#### Node.js 24.13.0
* Download & Install Node.js: Follow the instructions below.
```shell
https://nodejs.org/en/download
```
* Verify Node.js version:
```shell
node -v # Should print "v24.13.0".
npm -v # Should print "11.6.2".
```
#### Node-RED
* Install Node-RED:
```shell
npm install -g --unsafe-perm node-red
```
* Start Node-RED:
```shell
node-red # host -> http://localhost:1880 OR http://127.0.0.1:1880
```
#### Visual Studio Code
* Download & Install Visual Studio Code: Follow the instructions below.
```shell
https://code.visualstudio.com/download
```
#### Visual Studio Code Extensions
* Install Visual Studio Code Extensions:
Python
```shell
Python
```
Jupyter
```shell
Jupyter
```
#### Python Environment (venv)
* Create Environment (venv):
Shortcut
```shell
Ctrl + Shift + P
> Python: Create Environment...
> Venv
```
* Activate Environment (venv):
```shell
.venv\Scripts\activate
```
* Install Python Libraries
```shell
pip install numpy pandas scipy matplotlib scikit-learn joblib paho-mqtt
```
* Install Jupyter (ipykernel, jupyter_client, jupyter_core)
```shell
pip install ipykernel jupyter_client jupyter_core
```

### Linux (Debian: Ubuntu & etc.)
#### Python 3.13.11
* Install Python Dependencies:
```shell
sudo apt update 
sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libffi-dev liblzma-dev tk-dev curl git python3 python3-pip python3-venv
```
* Install pyenv (Python Installer):
```shell
curl https://pyenv.run | bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
pyenv --version
```
* Install Python 3.13.11:
```shell
pyenv install 3.13.11
pyenv global 3.13.11
```
* Verify Python Version:
```shell
python --version # Should print "Python 3.13.11".
```
* Note: If you see a different Python version, run the following:
```shell
pyenv rehash
```
#### Node.js 24.13.0
* Download & Install nvm:
```shell
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
\. "$HOME/.nvm/nvm.sh"
```
* Download and install Node.js:
```shell
nvm install 24
```
* Verify Node.js version:
```shell
node -v # Should print "v24.13.0".
npm -v # Should print "11.6.2".
```
#### Node-RED
* Install Node-RED:
```shell
sudo npm install -g --unsafe-perm node-red
```
* Start Node-RED:
```shell
node-red # host -> http://localhost:1880 OR http://127.0.0.1:1880
```
#### Visual Studio Code
* Download & Install Visual Studio Code: After Download Visual Studio Code.
```shell
https://code.visualstudio.com/download
```
* Install Visual Studio Code:
```shell
cd Downloads
sudo apt install ./<filename>.deb
```
* Note: If you see "Add Microsoft apt repository for Visual Studio Code", click "No".
* Run Visual Studio Code:
```shell
code
```
#### Visual Studio Code Extensions
* Install Visual Studio Code Extensions:
Python
```shell
Python
```
Jupyter
```shell
Jupyter
```
#### Python Environment (venv)
* Create Environment (venv):
Shortcut
```shell
Ctrl + Shift + P
> Python: Create Environment...
> Venv
```
* Activate Environment (venv):
```shell
source venv/bin/activate
```
* Install Python Libraries
```shell
pip install numpy pandas scipy matplotlib scikit-learn joblib paho-mqtt
```
* Install Jupyter (ipykernel, jupyter_client, jupyter_core)
```shell
pip install ipykernel jupyter_client jupyter_core
```

### macOS
#### Python 3.13.11
* Download & Install Python 3.13.11 Installer: Follow the instructions below.
```shell
https://www.python.org/downloads/macOS/
```
* Verify Python Version:
```shell
python --version # Should print "Python 3.13.11".
```
#### Node.js 24.13.0
* Download & Install Node.js: Follow the instructions below.
```shell
https://nodejs.org/en/download
```
* Verify Node.js version:
```shell
node -v # Should print "v24.13.0".
npm -v # Should print "11.6.2".
```
#### Node-RED
* Install Node-RED:
```shell
npm install -g --unsafe-perm node-red
```
* Start Node-RED:
```shell
node-red # host -> http://localhost:1880 OR http://127.0.0.1:1880
```
#### Visual Studio Code
* Download & Install Visual Studio Code: Follow the instructions below.
```shell
https://code.visualstudio.com/download
```
#### Visual Studio Code Extensions
* Install Visual Studio Code Extensions:
Python
```shell
Python
```
Jupyter
```shell
Jupyter
```
#### Python Environment (venv)
* Create Environment (venv):
Shortcut
```shell
Cmd + Shift + P
> Python: Create Environment...
> Venv
```
* Activate Environment (venv):
```shell
source venv/bin/activate
```
* Install Python Libraries
```shell
pip install numpy pandas scipy matplotlib scikit-learn joblib paho-mqtt
```
* Install Jupyter (ipykernel, jupyter_client, jupyter_core)
```shell
pip install ipykernel jupyter_client jupyter_core
```
