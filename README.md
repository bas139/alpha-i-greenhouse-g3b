# ALPHA I CODING TOURNAMENT 2026
--

## Team & Project Info
* **Team ID:** G3B / 3B
* **Team Members:** <!-- TODO: Fill in team member names -->
* **Case:** `c.grh` — Greenhouse Environment State (`DecisionTreeClassifier`, classes: `0: normal`, `1: alert`, `2: alarm`)
* **MQTT Broker:** `192.168.1.1:1883`
  * Phase 1 Data Collection (`subscriber.ipynb`): subscribes `idt/pt/grh/pbtest` → `data/test.csv`
  * Phase 2 Real-time Prediction (`rt_prediction.py`): subscribes `idt/pt/grh/usdts` → saves `p2_prediction.csv` → publishes `idt/cd-alp/G3B`
* **Project Files:**
  * `case_config.py` — Shared case configuration (do not modify)
  * `subscriber.ipynb` — MQTT data collector to CSV
  * `train_model.ipynb` — Train (`data/train.csv`) and evaluate (`data/test.csv`) `DecisionTreeClassifier` (`criterion="entropy"`, `max_depth=8`, `min_samples_split=18`, `min_samples_leaf=2`, `random_state=42`) → `model.joblib`
  * `rt_prediction.py` — Real-time MQTT inference + CSV logger + Node-RED forwarder
  * `GreenHouse_flow.json` / `IDT-GREENHOUSE-FLOW.json` — Node-RED Dashboard flow (LEDs, 4 gauges, 3 charts using `p.timestamp`, Predicted state, Reset button)
  * `p2_prediction.csv` — Phase 2 real-time prediction output (delete or start fresh with `START_NEW_CSV = True` before the official round)

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
