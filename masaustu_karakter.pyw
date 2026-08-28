import sys
import json
import os
import math
import random
from PyQt6.QtWidgets import QCheckBox
from datetime import datetime
from PyQt6.QtCore import Qt, QPoint, QTimer, QRectF, QTime
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QAction, QPixmap, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLineEdit, QPushButton, QListWidget, 
    QListWidgetItem, QMenu, QLabel, QFrame, QTimeEdit, QTabWidget
)

# EXE ve Python çalışma dizinini dinamik tespit eder
def get_resource_path(relative_path):
    """PyInstaller tek dosya (.exe) veya normal çalışma dizinini çözer."""
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

DATA_FILE = os.path.join(os.environ.get("APPDATA", ""), "spidey_tasks.json")

def load_scaled_pixmap(file_name, width=190, height=250):
    """Görseli dosyadan yükleyip keskin piksel ölçeklemesi uygular."""
    file_path = get_resource_path(file_name)
    pix = QPixmap(file_path)
    if not pix.isNull():
        return pix.scaled(
            width, height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
    # Eğer doğrudan bulamazsa mevcut dizinden dener
    pix = QPixmap(file_name)
    if not pix.isNull():
        return pix.scaled(
            width, height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
    return QPixmap()



class PlannerPanel(QWidget):
    def __init__(self, spidey_parent):
        super().__init__()
        self.spidey = spidey_parent
        self.setWindowFlags(
            Qt.WindowType.Tool | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(330, 480)

        self.pomo_seconds_left = 60 * 60
        self.pomo_is_running = False
        self.pomo_mode = "FOCUS"

        self.pomo_timer = QTimer(self)
        self.pomo_timer.timeout.connect(self.update_pomodoro_tick)
        self.pomo_timer.start(1000)

        # Alarm kontrolü
        self.alarm_checker = QTimer(self)
        self.alarm_checker.timeout.connect(self.check_task_deadlines)
        self.alarm_checker.start(1000)

        self.init_ui()
        self.load_tasks()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.card = QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background-color: #0b0f19;
                border-radius: 12px;
                border: 2px solid #e11d48;
            }
            QLabel { color: #f8fafc; font-weight: bold; border: none; }
            QLineEdit, QTimeEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px;
                font-size: 12px;
            }
            QLineEdit:focus, QTimeEdit:focus { border: 1px solid #e11d48; }
            QPushButton {
                background-color: #e11d48;
                color: #ffffff;
                border-radius: 6px;
                font-weight: bold;
                padding: 6px 10px;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover { opacity: 0.85; }
            QCheckBox {
                color: #94a3b8;
                font-size: 11px;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #e11d48;
                background-color: #0b0f19;
            }
            QCheckBox::indicator:checked {
                background-color: #e11d48;
            }
            QListWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 4px;
            }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #334155; }
            QListWidget::item:selected { background-color: #334155; border-radius: 4px; }
            QListWidget::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #e11d48;
                background-color: #0b0f19;
            }
            QListWidget::indicator:checked { background-color: #e11d48; border: 1px solid #e11d48; }
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #1e293b;
                color: #94a3b8;
                padding: 6px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 11px;
            }
            QTabBar::tab:selected { background: #e11d48; color: #ffffff; }
        """)

        card_layout = QVBoxLayout(self.card)
        self.tabs = QTabWidget()
        card_layout.addWidget(self.tabs)

        # TAB 1: Görevler
        task_tab = QWidget()
        task_layout = QVBoxLayout(task_tab)
        task_layout.setContentsMargins(4, 8, 4, 4)

        self.task_list = QListWidget()
        self.task_list.itemChanged.connect(self.on_item_changed)
        # Sağ tık menüsü ile silme desteği
        self.task_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self.show_task_context_menu)
        task_layout.addWidget(self.task_list)

        # Görev Giriş Satırı
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Yeni görev yaz...")
        self.task_input.returnPressed.connect(self.add_task)
        task_layout.addWidget(self.task_input)

        # Saat & Buton Satırı
        controls_row = QHBoxLayout()
        
        self.enable_time_cb = QCheckBox("⏰ Saat")
        self.enable_time_cb.toggled.connect(self.toggle_time_picker)
        controls_row.addWidget(self.enable_time_cb)

        self.time_picker = QTimeEdit()
        self.time_picker.setDisplayFormat("HH:mm")
        self.time_picker.setTime(QTime.currentTime().addSecs(1800))
        self.time_picker.setEnabled(False) # Başlangıçta kapalı
        controls_row.addWidget(self.time_picker)

        add_btn = QPushButton("Ekle")
        add_btn.clicked.connect(self.add_task)
        controls_row.addWidget(add_btn)

        task_layout.addLayout(controls_row)

        del_btn = QPushButton("Seçili Görevi Sil (Delete)")
        del_btn.setStyleSheet("background-color: #475569; color: #ffffff;")
        del_btn.clicked.connect(self.delete_selected_task)
        task_layout.addWidget(del_btn)

        self.tabs.addTab(task_tab, "📋 Görevler")

        # TAB 2: Pomodoro
        pomo_tab = QWidget()
        pomo_layout = QVBoxLayout(pomo_tab)
        pomo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pomo_title = QLabel("🍅 ODAKLANMA MODU")
        self.pomo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomo_title.setStyleSheet("font-size: 13px; color: #f43f5e;")
        pomo_layout.addWidget(self.pomo_title)

        self.pomo_display = QLabel("60:00")
        self.pomo_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomo_display.setStyleSheet("font-size: 42px; font-weight: bold; color: #ffffff; margin: 10px 0;")
        pomo_layout.addWidget(self.pomo_display)

        pomo_btn_row = QHBoxLayout()
        self.pomo_toggle_btn = QPushButton("Başlat")
        self.pomo_toggle_btn.clicked.connect(self.toggle_pomodoro)
        pomo_btn_row.addWidget(self.pomo_toggle_btn)

        pomo_reset_btn = QPushButton("Sıfırla")
        pomo_reset_btn.setStyleSheet("background-color: #475569; color: #ffffff;")
        pomo_reset_btn.clicked.connect(self.reset_pomodoro)
        pomo_btn_row.addWidget(pomo_reset_btn)

        pomo_layout.addLayout(pomo_btn_row)
        self.tabs.addTab(pomo_tab, "⏱️ Pomodoro")

        layout.addWidget(self.card)

    def toggle_time_picker(self, checked):
        """Kutucuk işaretlenirse saat seçiciyi aktif eder."""
        self.time_picker.setEnabled(checked)

    def toggle_pomodoro(self):
        self.pomo_is_running = not self.pomo_is_running
        self.pomo_toggle_btn.setText("Durdur" if self.pomo_is_running else "Devam Et")
        if self.pomo_is_running:
            self.spidey.trigger_alert("60 dk odaklanma başladı!")

    def reset_pomodoro(self):
        self.pomo_is_running = False
        self.pomo_mode = "FOCUS"
        self.pomo_seconds_left = 60 * 60
        self.pomo_display.setText("60:00")
        self.pomo_title.setText("🍅 ODAKLANMA MODU")
        self.pomo_toggle_btn.setText("Başlat")

    def update_pomodoro_tick(self):
        if self.pomo_is_running and self.pomo_seconds_left > 0:
            self.pomo_seconds_left -= 1
            mins = self.pomo_seconds_left // 60
            secs = self.pomo_seconds_left % 60
            self.pomo_display.setText(f"{mins:02d}:{secs:02d}")

            if self.pomo_seconds_left == 0:
                if self.pomo_mode == "FOCUS":
                    self.pomo_mode = "BREAK"
                    self.pomo_seconds_left = 10 * 60
                    self.pomo_title.setText("☕ MOLA ZAMANI")
                    self.spidey.trigger_alert("Tebrikler! 60 dk bitti. 10 dk mola ver!")
                else:
                    self.pomo_mode = "FOCUS"
                    self.pomo_seconds_left = 60 * 60
                    self.pomo_title.setText("🍅 ODAKLANMA MODU")
                    self.spidey.trigger_alert("Mola bitti! Yeni bir seansa hazır mısın?")
                self.pomo_is_running = False
                self.pomo_toggle_btn.setText("Başlat")

    def check_task_deadlines(self):
        """Sadece saat belirlenmiş görevlerin süresini denetler."""
        current_time_str = datetime.now().strftime("%H:%M")
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            task_data = item.data(Qt.ItemDataRole.UserRole)
            if task_data and task_data.get("time") and not task_data.get("done", False) and not task_data.get("alerted", False):
                if task_data.get("time") == current_time_str:
                    task_data["alerted"] = True
                    item.setData(Qt.ItemDataRole.UserRole, task_data)
                    self.save_tasks()
                    self.spidey.trigger_alert(f"Zamanı Geldi: {task_data['text']}!")

    def add_task(self):
        text = self.task_input.text().strip()
        if not text:
            return

        has_time = self.enable_time_cb.isChecked()
        time_str = self.time_picker.time().toString("HH:mm") if has_time else None

        display_text = f"[{time_str}] {text}" if has_time else text
        item = QListWidgetItem(display_text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
        item.setCheckState(Qt.CheckState.Unchecked)
        item.setData(Qt.ItemDataRole.UserRole, {
            "text": text,
            "time": time_str,
            "done": False,
            "alerted": False
        })
        self.task_list.addItem(item)
        self.task_input.clear()
        self.save_tasks()

    def on_item_changed(self, item):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        is_done = item.checkState() == Qt.CheckState.Checked
        data["done"] = is_done
        item.setData(Qt.ItemDataRole.UserRole, data)

        font = item.font()
        font.setStrikeOut(is_done)
        item.setFont(font)
        item.setForeground(QColor("#64748b") if is_done else QColor("#f8fafc"))
        self.save_tasks()

    def delete_selected_task(self):
        """Seçili tüm görevleri listeden güvenle siler."""
        selected_items = self.task_list.selectedItems()
        if not selected_items:
            # Seçim yoksa aktif satırdakini siler
            current_row = self.task_list.currentRow()
            if current_row >= 0:
                self.task_list.takeItem(current_row)
        else:
            for item in selected_items:
                self.task_list.takeItem(self.task_list.row(item))
        self.save_tasks()

    def show_task_context_menu(self, pos):
        """Görev listesine sağ tıklandığında silme menüsü açar."""
        item = self.task_list.itemAt(pos)
        if item:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #0b0f19;
                    color: #f8fafc;
                    border: 1px solid #e11d48;
                    border-radius: 6px;
                }
                QMenu::item:selected { background-color: #e11d48; }
            """)
            del_action = QAction("🗑️ Görevi Sil", self)
            del_action.triggered.connect(lambda: self.task_list.takeItem(self.task_list.row(item)))
            del_action.triggered.connect(self.save_tasks)
            menu.addAction(del_action)
            menu.exec(self.task_list.mapToGlobal(pos))

    def keyPressEvent(self, event):
        """Klavyeden Delete tuşuna basınca seçili görevi siler."""
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_task()
        else:
            super().keyPressEvent(event)

    def save_tasks(self):
        tasks = []
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            tasks.append(item.data(Qt.ItemDataRole.UserRole))
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_tasks(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                    for t in tasks:
                        display_text = f"[{t['time']}] {t['text']}" if t.get('time') else t['text']
                        item = QListWidgetItem(display_text)
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
                        is_checked = t.get("done", False)
                        item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
                        item.setData(Qt.ItemDataRole.UserRole, t)
                        font = item.font()
                        font.setStrikeOut(is_checked)
                        item.setFont(font)
                        if is_checked:
                            item.setForeground(QColor("#64748b"))
                        self.task_list.addItem(item)
            except Exception:
                pass

class BigMasterSpiderMan(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(450, 650)

        # Tavanda Kullanılacak 3 Pozun Yüklenmesi
        self.pix_hang  = load_scaled_pixmap("spidey.png", 275, 355)        # Ters asılı duruş
        self.pix_swing = load_scaled_pixmap("iple_savrulma.png", 250, 330) # İple savrulma
        self.pix_jump  = load_scaled_pixmap("iple_atlarken.png", 240, 320) # Tırmanış/İniş pozu

        self.planner = PlannerPanel(self)
        self.drag_position = QPoint()

        # Poz Durumları: 'DROPPING', 'HANGING', 'SWINGING', 'CLIMBING'
        self.state = "DROPPING"
        self.state_timer = 0

        self.web_length = 10.0
        self.max_web_length = 210.0
        self.swing_angle = 0.0
        self.swing_speed = 0.040
        self.time_counter = 0

        self.alert_message = ""
        self.alert_timer = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_behavior_loop)
        self.timer.start(16)

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, 0)

    def trigger_alert(self, text):
        self.alert_message = text
        self.alert_timer = 360
        self.state = "CLIMBING"

    def update_behavior_loop(self):
        """Tavanda ters sarkma ve savrulma arasında süreli döngü."""
        self.time_counter += 1

        if self.alert_timer > 0:
            self.alert_timer -= 1
            if self.alert_timer == 0:
                self.alert_message = ""

        # Tavandan aşağı iniş
        if self.state == "DROPPING":
            if self.web_length < self.max_web_length:
                self.web_length += 5.0
            else:
                self.state = "HANGING"
                self.state_timer = 360  # 6 saniye ters sarkma

        # 1. Aşama: Ters Sarkma (6 saniye)
        elif self.state == "HANGING":
            self.swing_angle = 0.20 * math.sin(self.time_counter * 0.04)
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "SWINGING"
                self.state_timer = 360  # 6 saniye savrulma

        # 2. Aşama: İple Savrulma (6 saniye)
        elif self.state == "SWINGING":
            self.swing_angle = 0.25 * math.sin(self.time_counter * 0.040)
            self.state_timer -= 1
            if self.state_timer <= 0:
                # Süre dolunca yukarı tırmanıp tekrar insin:
                self.state = "CLIMBING"

        # 3. Aşama: Yukarı Tırmanma
        elif self.state == "CLIMBING":
            if self.web_length > 15:
                self.web_length -= 6.0
            else:
                self.web_length = 15.0
                self.state = "DROPPING"

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        origin_x = self.width() / 2
        origin_y = 0

        spidey_x = origin_x + self.web_length * math.sin(self.swing_angle)
        spidey_y = origin_y + self.web_length * math.cos(self.swing_angle)

        # Duruma göre görsel seçimi:
        if self.state in ["DROPPING", "CLIMBING"]:
            current_pixmap = self.pix_jump   # Atlama/Tırmanış pozu
        elif self.state == "SWINGING":
            current_pixmap = self.pix_swing  # Savrulma pozu
        else:
            current_pixmap = self.pix_hang   # Ters sarkma pozu

        # 1. Örümcek Ağı Çizimi
        painter.setPen(QPen(QColor(255, 255, 255, 235), 2))
        painter.drawLine(int(origin_x), int(origin_y), int(spidey_x), int(spidey_y))
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(origin_x - 3, 0, 6, 6))

        # 2. Spider-Man Karakter Çizimi
        if current_pixmap and not current_pixmap.isNull():
            painter.save()
            painter.translate(spidey_x, spidey_y)
            painter.rotate(math.degrees(self.swing_angle))

            # --- HER POZ İÇİN ÖZEL AĞ BAĞLANTI (TUTUŞ) NOKTASI ---
            if self.state == "SWINGING":
                # İple Savrulma Pozu (Elin olduğu yer)
                anchor_x = int(current_pixmap.width() * 0.42)   # Sağa-Sola kaydırmak için burayı değiştirin (0.40 - 0.60 arası)
                anchor_y = int(current_pixmap.height() * 0.13)  # Yukarı-Aşağı kaydırmak için burayı değiştirin (0.02 - 0.15 arası)

            elif self.state in ["DROPPING", "CLIMBING"]:
                # İple Atlama / Tırmanış Pozu (Yukarı uzanan el)
                anchor_x = int(current_pixmap.width() * 0.45)   # Sağa-Sola kaydırmak için burayı değiştirin
                anchor_y = int(current_pixmap.height() * 0.09)  # Yukarı-Aşağı kaydırmak için burayı değiştirin

            else:
                # Klasik Ters Sarkma (Ayakların tutunduğu yer)
                anchor_x = int(current_pixmap.width() / 2) - 16
                # Karakter ipten çok aşağıda kalıyorsa bu değeri artırın:
                # (Görselin yüksekliğinin %12'si kadar karakteri yukarı çeker)
                anchor_y = int(current_pixmap.height() * 0.37)

            # Görseli tam belirlenen tutuş noktasına göre çiz:
            painter.drawPixmap(-anchor_x, -anchor_y, current_pixmap)
            painter.restore()

        # 3. Görev / Uyarı Balonu
        if self.alert_message:
            bubble_rect = QRectF(25, spidey_y + 245, self.width() - 50, 55)
            painter.setBrush(QBrush(QColor("#0b0f19")))
            painter.setPen(QPen(QColor("#e11d48"), 2))
            painter.drawRoundedRect(bubble_rect, 10, 10)

            painter.setPen(QColor("#ffffff"))
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(bubble_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, f"🕷️ {self.alert_message}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos.x(), 0)

            if self.planner.isVisible():
                self.planner.move(self.x() + self.width() + 10, 80)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.planner.isVisible():
                self.planner.hide()
            else:
                self.planner.move(self.x() + self.width() + 10, 80)
                self.planner.show()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0b0f19;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected { background-color: #1e293b; }
        """)

        climb_act = QAction("🕸️ Ağı Topla & Tekrar İndir", self)
        climb_act.triggered.connect(lambda: setattr(self, 'state', 'CLIMBING'))
        menu.addAction(climb_act)

        toggle_action = QAction("Planlayıcıyı Aç/Kapat", self)
        toggle_action.triggered.connect(lambda: self.planner.setVisible(not self.planner.isVisible()))
        menu.addAction(toggle_action)

        menu.addSeparator()

        exit_action = QAction("Çıkış", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_action)

        menu.exec(event.globalPos())

    def closeEvent(self, event):
        self.planner.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    spidey = BigMasterSpiderMan()
    spidey.show()
    sys.exit(app.exec())
