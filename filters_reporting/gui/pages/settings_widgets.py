from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabBar,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


class NoWheelComboBox(QComboBox):
    def wheelEvent(
        self,
        event,
    ) -> None:
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(
        self,
        event,
    ) -> None:
        event.ignore()


class NoWheelTimeEdit(QTimeEdit):
    def wheelEvent(
        self,
        event,
    ) -> None:
        event.ignore()


class NoWheelTabBar(QTabBar):
    def wheelEvent(
        self,
        event,
    ) -> None:
        event.ignore()


class NoWheelTabWidget(QTabWidget):
    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setTabBar(
            NoWheelTabBar(self)
        )


class SettingsTabBase(QWidget):
    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("settingsTab")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName(
            "settingsTabScroll"
        )
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(
            QFrame.NoFrame
        )

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName(
            "settingsTabContent"
        )

        self.content_layout = QVBoxLayout(
            self.scroll_content
        )
        self.content_layout.setContentsMargins(
            2,
            8,
            2,
            8,
        )
        self.content_layout.setSpacing(12)

        self.scroll_area.setWidget(
            self.scroll_content
        )

        outer_layout.addWidget(
            self.scroll_area
        )

    def create_panel(
        self,
    ) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        return panel

    def create_form(
        self,
    ) -> QFormLayout:
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(9)
        form.setLabelAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )
        form.setFieldGrowthPolicy(
            QFormLayout.AllNonFixedFieldsGrow
        )
        return form

    def create_file_row(
        self,
        line_edit,
        file_filter: str,
    ) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(7)

        button = QPushButton("Wybierz")
        button.setObjectName("secondaryButton")
        button.clicked.connect(
            lambda: self.choose_file(
                line_edit,
                file_filter,
            )
        )

        layout.addWidget(line_edit, 1)
        layout.addWidget(button)
        return layout

    def create_directory_row(
        self,
        line_edit,
    ) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(7)

        button = QPushButton("Wybierz folder")
        button.setObjectName("secondaryButton")
        button.clicked.connect(
            lambda: self.choose_directory(
                line_edit
            )
        )

        layout.addWidget(line_edit, 1)
        layout.addWidget(button)
        return layout

    def choose_file(
        self,
        line_edit,
        file_filter: str,
    ) -> None:
        current = line_edit.text().strip()
        start_path = ""

        if current:
            start_path = str(
                Path(current).expanduser()
            )

        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik",
            start_path,
            file_filter,
        )

        if selected:
            line_edit.setText(selected)

    def choose_directory(
        self,
        line_edit,
    ) -> None:
        current = line_edit.text().strip()

        selected = QFileDialog.getExistingDirectory(
            self,
            "Wybierz folder",
            current,
        )

        if selected:
            line_edit.setText(selected)

    def path_from_edit(
        self,
        line_edit,
    ) -> Path | None:
        value = line_edit.text().strip()

        if not value:
            return None

        return Path(value).expanduser()
