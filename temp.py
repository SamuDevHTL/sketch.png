from PyQt6.QtWidgets import (QApplication, QGraphicsScene, QGraphicsView, QGraphicsItem,
                             QGraphicsPixmapItem, QPushButton, QFileDialog, QVBoxLayout, QWidget, QHBoxLayout, QInputDialog, QGraphicsTextItem,
                             QGraphicsLineItem, QGraphicsRectItem, QColorDialog)
from PyQt6.QtGui import QPixmap, QPainter, QKeyEvent, QPen, QFont, QColor
from PyQt6.QtCore import Qt, QLineF, QRectF
import sys

COMPONENTS = {
    "resistor": "components/resistor.png",
    "capacitor": "components/capacitor.png",
    "transistor": "components/transistor.png",
    "opv": "components/opv.png"
}

class CircuitComponent(QGraphicsPixmapItem):
    """ A draggable circuit component. """
    def __init__(self, component_type):
        super().__init__(QPixmap(COMPONENTS[component_type]))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation) #smooth rotation
        self.component_type = component_type

        if component_type == "transistor":
            self.default_image = QPixmap(COMPONENTS["transistor"])
            self.alt_image = QPixmap("transistor2.png")
            self.current_image = True  # Track active image
            self.setPixmap(self.default_image)

    def switch_transistor_image(self): #key = s
        if self.component_type == "transistor":
            self.current_image = not self.current_image
            self.setPixmap(self.default_image if self.current_image else self.alt_image)
        
    def rotate_component(self):
        self.setRotation(self.rotation() + 90)  #rotate +90

    def mirror_vertically(self):
        transform = self.transform()
        current_scale_y = transform.m22() #state of y-axis
        if current_scale_y > 0:
            self.setTransform(transform.scale(1, -1))  #mirror vertically
        else:
            self.setTransform(transform.scale(1, 1))  #reset

class Wire(QGraphicsLineItem):
    def __init__(self, start_point, end_point, color=Qt.GlobalColor.white):
        super().__init__(QLineF(start_point, end_point))
        self.setPen(QPen(color, 2))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

class CircuitScene(QGraphicsScene): #save selection
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.drawing_wire = False
        self.last_point = None  
        self.selection_rect = None

    def mousePressEvent(self, event):
        if self.parent.drawing_wire and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = event.scenePos()
            if self.last_point is None:
                self.last_point = scene_pos
            else:
                wire = Wire(self.last_point, scene_pos, self.parent.wire_color)  #use color
                self.addItem(wire)
                self.last_point = scene_pos  
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.parent.text_insertion_mode:
                self.parent.place_text(event.scenePos()) #place txt on mouse pos
            else:
                self.origin = event.scenePos()
                if self.selection_rect:
                    self.removeItem(self.selection_rect)
                self.selection_rect = QGraphicsRectItem(QRectF(self.origin, self.origin))
                self.selection_rect.setPen(QPen(QColor("#808080"), 2, Qt.PenStyle.DashLine))
                self.addItem(self.selection_rect)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent.drawing_wire and self.last_point is not None:
            scene_pos = event.scenePos()
            wire = Wire(self.last_point, scene_pos, self.parent.wire_color)  #Use color
            self.addItem(wire)
            self.last_point = scene_pos
        elif self.selection_rect:
            rect = QRectF(self.origin, event.scenePos()).normalized()
            self.selection_rect.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event): #final select
        if self.selection_rect:
            self.parent.selected_area = self.selection_rect.rect()
            self.removeItem(self.selection_rect)
            self.selection_rect = None
        super().mouseReleaseEvent(event)

class CircuitEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("sketch.png")
        self.setGeometry(100, 100, 1200, 800)
        self.wire_color = Qt.GlobalColor.white #standard color
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        self.sidebar.setLayout(sidebar_layout)

        for component in COMPONENTS.keys(): #component buttons
            btn = QPushButton(component.capitalize())
            btn.clicked.connect(lambda checked, c=component: self.add_component(c))
            sidebar_layout.addWidget(btn)

        self.color_picker_button = QPushButton("Pick Wire Color")
        self.color_picker_button.clicked.connect(self.pick_wire_color)
        sidebar_layout.addWidget(self.color_picker_button)

        zoom_layout = QHBoxLayout()
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.zoom_in_button)
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.zoom_out_button)
        sidebar_layout.addLayout(zoom_layout)

        self.reset_button = QPushButton("Reset Circuit")
        self.reset_button.clicked.connect(self.reset_scene)
        sidebar_layout.addWidget(self.reset_button)
        
        layout.addWidget(self.sidebar)
        
        self.scene = CircuitScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.setSceneRect(0, 0, 800, 600)
        layout.addWidget(self.view)

        self.drawing_wire = False
        self.selected_area = None  #select area

        self.text_insertion_mode = False  #text toggle

        self.set_modern_style()

    def set_modern_style(self):
        modern_stylesheet = """
        QWidget {
            background-color: #212121;
            color: #E0E0E0;
            font-size: 14px;
            font-family: 'Segoe UI', Tahoma, Geneva, sans-serif;
        }
        QPushButton {
            background-color: #323232;
            color: #FFFFFF;
            border-radius: 12px;
            padding: 10px;
            font-weight: bold;
            border: none;
        }
        QPushButton:hover {
            background-color: #5e5e5e;
        }
        QPushButton:pressed {
            background-color: #7a7a7a;
        }
        QGraphicsView {
            background-color: #121212;
        }
        QGraphicsRectItem {
            border: 1px dashed #FF4081;
        }
        QGraphicsItem {
            opacity: 0.85;
        }
        """
        self.setStyleSheet(modern_stylesheet)

    def add_component(self, component_type, x=200, y=200):
        component = CircuitComponent(component_type)
        component.setPos(x, y)
        self.scene.addItem(component)

    def enable_wire_drawing(self):
        self.drawing_wire = True

    def pick_wire_color(self):
        color = QColorDialog.getColor(self.wire_color, self, "Pick Wire Color")
        if color.isValid():
            self.wire_color = color

    def zoom_in(self):
        self.view.scale(1.2, 1.2)
    def zoom_out(self):
        self.view.scale(0.8, 0.8)

    def reset_scene(self):
        self.scene.clear()

    def save_as_png(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Circuit", "exports/circuit.png", "Images (*.png)")
        if file_path:
            rect = QRectF(self.selected_area) if self.selected_area else self.scene.sceneRect()

            image = QPixmap(int(rect.width()), int(rect.height()))
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            self.scene.render(painter, QRectF(image.rect()), rect)  # Correct type
            painter.end()
            image.save(file_path, "PNG")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            selected_items = self.scene.selectedItems()
            for item in selected_items:
                self.scene.removeItem(item)
        elif event.key() == Qt.Key.Key_R:
            self.rotate_selected_component()
        elif event.key() == Qt.Key.Key_M:
            self.mirror_selected_components()
        elif event.key() == Qt.Key.Key_E:
            self.save_as_png()
        elif event.key() == Qt.Key.Key_T:
            self.toggle_text_insertion_mode()
        elif event.key() == Qt.Key.Key_W:
            if self.drawing_wire:
                self.drawing_wire = False # Stop drawing, reset the last_point
                self.scene.last_point = None  # Reset the last_point
                print("Wire drawing mode disabled")
            else:
                self.drawing_wire = True #start drawing
                print("Wire drawing mode enabled")
        elif event.key() == Qt.Key.Key_S: #transistor switch
            selected_items = self.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, CircuitComponent):
                    item.switch_transistor_image()

    def toggle_text_insertion_mode(self):
        self.text_insertion_mode = not self.text_insertion_mode
        status = "enabled" if self.text_insertion_mode else "disabled"
        print(f"Text insertion mode {status}")

    def place_text(self, position):
        text, ok = QInputDialog.getText(self, "Enter Text", "Text:")
        if ok and text: 
            text_item = QGraphicsTextItem(text)
            text_item.setPos(position)
            font = QFont("Arial", 14)
            text_item.setFont(font)
            text_item.setDefaultTextColor(Qt.GlobalColor.white)
            text_item.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            self.scene.addItem(text_item)
        self.toggle_text_insertion_mode()

    def rotate_selected_component(self):
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, CircuitComponent):
                item.rotate_component()

    def mirror_selected_components(self):
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, CircuitComponent):
                item.mirror_vertically()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = CircuitEditor()
    editor.show()
    sys.exit(app.exec())