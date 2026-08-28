# 🕷️ Spider-Man Desktop Companion & Task Tracker

An interactive, transparent desktop companion featuring animated Spider-Man poses, an integrated task manager, and a customizable Pomodoro focus timer built with **Python** and **PyQt6**.

---

## ✨ Features

* **Dynamic Pose Cycling:** Transitions automatically between swinging, hanging upside-down, and web-climbing animations.
* **To-Do & Deadline Alerts:** Create standalone or timed tasks. Spider-Man notifies you with a speech bubble when deadlines arrive.
* **Pomodoro Focus Timer:** 60-minute focus sessions accompanied by 10-minute breaks.
* **Non-Intrusive Overlay:** Transparent background, draggable interface, and always-on-top positioning.
* **Persistent Storage:** Saves tasks locally in JSON format between sessions.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9 or newer

### Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/spidey-desktop-companion.git](https://github.com/YOUR_USERNAME/spidey-desktop-companion.git)
   cd spidey-desktop-companion
Install dependencies:

Bash
pip install -r requirements.txt
Run the application:

Bash
python masaustu_karakter.py
🛠️ Build Executable (.exe)
To bundle the application and image assets into a single portable executable:

Bash
pyinstaller --onefile --windowed --add-data "spidey.png;." --add-data "iple_savrulma.png;." --add-data "iple_atlarken.png;." masaustu_karakter.py
🎮 Controls
Left Click + Drag: Move Spider-Man along the top edge of your screen.

Double Click: Open or minimize the Task & Pomodoro planner panel.

Right Click: Open the context menu to reset animations or exit.

Delete Key / Right Click (Planner): Remove selected tasks.
