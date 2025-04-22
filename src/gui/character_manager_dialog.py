# -*- coding: utf-8 -*-
"""
VNova Assistant - 视觉小说制作助手
角色管理对话框模块
"""

import sys
import uuid
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidgetItem, QWidget
)
from PyQt5.QtCore import Qt

from qfluentwidgets import (
    PushButton, TextEdit, LineEdit, ListWidget, SubtitleLabel, 
    TitleLabel, BodyLabel, FluentIcon, MessageBox,
    InfoBar, InfoBarPosition, Action
)

# Assuming character data will be stored in the timeline object
# from src.story_manager.story_timeline import StoryTimeline # Import if needed later

class CharacterManagerDialog(QDialog):
    """Dialog to create, view, edit, and delete character profiles."""
    def __init__(self, timeline, parent=None):
        super().__init__(parent)
        self.timeline = timeline # Reference to the main timeline object
        # Ensure timeline has a characters attribute (will be added in story_timeline.py later)
        if not hasattr(self.timeline, 'characters'):
            self.timeline.characters = {} # Initialize if missing

        self.setWindowTitle("VNova Assistant - 角色档案管理")
        self.setMinimumSize(600, 400)

        self._init_ui()
        self._connect_signals()
        self._load_character_list()

    def _init_ui(self):
        """Initializes the UI elements."""
        main_layout = QHBoxLayout(self)

        # Left Panel: Character List
        left_panel = QVBoxLayout()
        left_panel.addWidget(SubtitleLabel("角色列表"))
        self.character_list = ListWidget()
        left_panel.addWidget(self.character_list)

        list_button_layout = QHBoxLayout()
        self.add_button = PushButton("添加新角色", self)
        self.add_button.setIcon(FluentIcon.ADD)
        self.delete_button = PushButton("删除选中角色", self)
        self.delete_button.setIcon(FluentIcon.DELETE)
        self.delete_button.setEnabled(False) # Disable initially
        list_button_layout.addWidget(self.add_button)
        list_button_layout.addWidget(self.delete_button)
        left_panel.addLayout(list_button_layout)

        # Right Panel: Character Editor
        right_panel = QVBoxLayout()
        right_panel.addWidget(TitleLabel("角色详情"))

        self.name_label = BodyLabel("姓名:")
        self.name_input = LineEdit()
        self.name_input.setPlaceholderText("输入角色姓名...")
        right_panel.addWidget(self.name_label)
        right_panel.addWidget(self.name_input)

        self.desc_label = BodyLabel("描述/设定:")
        self.desc_input = TextEdit()
        self.desc_input.setPlaceholderText("输入角色的详细描述、背景故事、性格特点等...")
        right_panel.addWidget(self.desc_label)
        right_panel.addWidget(self.desc_input)

        self.save_button = PushButton("保存当前角色", self)
        self.save_button.setIcon(FluentIcon.SAVE)
        self.save_button.setEnabled(False) # Disable initially
        right_panel.addWidget(self.save_button)

        # Add panels to main layout
        main_layout.addLayout(left_panel, 1) # Weight 1
        main_layout.addLayout(right_panel, 2) # Weight 2

    def _connect_signals(self):
        """Connects UI signals to methods."""
        self.character_list.currentItemChanged.connect(self.display_character_details)
        self.add_button.clicked.connect(self.add_new_character)
        self.save_button.clicked.connect(self.save_current_character)
        self.delete_button.clicked.connect(self.delete_selected_character)

        # Enable save button when details are edited
        self.name_input.textChanged.connect(lambda: self.save_button.setEnabled(True))
        self.desc_input.textChanged.connect(lambda: self.save_button.setEnabled(True))

    def _load_character_list(self):
        """Populates the list widget with character names from the timeline."""
        self.character_list.clear()
        # Sort characters by name for consistency
        sorted_char_ids = sorted(self.timeline.characters.keys(), key=lambda cid: self.timeline.characters[cid].get('name', '未命名'))
        for char_id in sorted_char_ids:
            char_data = self.timeline.characters[char_id]
            name = char_data.get('name', f'未命名 ({char_id[:6]}...)')
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, char_id) # Store character ID
            self.character_list.addItem(item)
        print(f"Loaded {len(self.timeline.characters)} characters into list.")

    def display_character_details(self, current_item, previous_item):
        """Shows the details of the selected character in the right panel."""
        if current_item:
            char_id = current_item.data(Qt.ItemDataRole.UserRole)
            if char_id in self.timeline.characters:
                char_data = self.timeline.characters[char_id]
                self.name_input.setText(char_data.get('name', ''))
                self.desc_input.setPlainText(char_data.get('description', ''))
                self.delete_button.setEnabled(True)
                self.save_button.setEnabled(False) # Disable save until edits are made
                self.name_input.setEnabled(True)
                self.desc_input.setEnabled(True)
            else:
                self._clear_details()
                self.delete_button.setEnabled(False)
        else:
            self._clear_details()
            self.delete_button.setEnabled(False)

    def _clear_details(self):
        """Clears the character detail fields."""
        self.name_input.clear()
        self.desc_input.clear()
        self.name_input.setEnabled(False)
        self.desc_input.setEnabled(False)
        self.save_button.setEnabled(False)

    def add_new_character(self):
        """Adds a new, empty character entry."""
        # Create a unique ID (simple approach)
        new_char_id = str(uuid.uuid4())
        new_char_data = {'name': '新角色', 'description': ''}
        self.timeline.characters[new_char_id] = new_char_data
        self.timeline.dirty = True # Mark project as modified

        # Add to list and select it
        item = QListWidgetItem(new_char_data['name'])
        item.setData(Qt.ItemDataRole.UserRole, new_char_id)
        self.character_list.addItem(item)
        self.character_list.setCurrentItem(item)
        self.name_input.setFocus() # Focus name field for editing
        self.name_input.selectAll()
        self.save_button.setEnabled(True) # Enable save immediately for new char
        print(f"Added new character with ID: {new_char_id}")

    def save_current_character(self):
        """Saves the details of the currently selected character."""
        current_item = self.character_list.currentItem()
        if not current_item:
            return

        char_id = current_item.data(Qt.ItemDataRole.UserRole)
        if char_id in self.timeline.characters:
            name = self.name_input.text().strip()
            description = self.desc_input.toPlainText().strip()

            if not name:
                InfoBar.warning(
                    title="保存失败",
                    content="角色姓名不能为空！",
                    orient=InfoBarPosition.TOP,
                    parent=self
                )
                return

            self.timeline.characters[char_id]['name'] = name
            self.timeline.characters[char_id]['description'] = description
            self.timeline.dirty = True # Mark project as modified

            # Update list item text
            current_item.setText(name)
            self.save_button.setEnabled(False) # Disable save after successful save
            
            # Show success message
            InfoBar.success(
                title="保存成功",
                content=f"角色 '{name}' 已保存",
                orient=InfoBarPosition.TOP,
                parent=self
            )
            print(f"Saved character: {char_id} ({name})")
        else:
            MessageBox("错误", "无法找到要保存的角色数据！", self).exec()

    def delete_selected_character(self):
        """Deletes the currently selected character."""
        current_item = self.character_list.currentItem()
        if not current_item:
            return

        char_id = current_item.data(Qt.ItemDataRole.UserRole)
        name = self.timeline.characters.get(char_id, {}).get('name', '未知角色')

        dialog = MessageBox(
            "确认删除", 
            f"确定要删除角色 '{name}' 吗？\n此操作无法撤销。",
            self
        )
        
        if dialog.exec():  # 用户点击确定
            if char_id in self.timeline.characters:
                del self.timeline.characters[char_id]
                self.timeline.dirty = True # Mark project as modified
                row = self.character_list.row(current_item)
                self.character_list.takeItem(row)
                
                InfoBar.success(
                    title="删除成功",
                    content=f"角色 '{name}' 已删除",
                    orient=InfoBarPosition.TOP,
                    parent=self
                )
                print(f"Deleted character: {char_id} ({name})")
                # Optionally select the next/previous item or clear details
                self._clear_details()
            else:
                MessageBox("错误", "无法找到要删除的角色数据！", self).exec()


class MockTimeline:
    """Mock timeline for testing."""
    def __init__(self):
        self.characters = {
            'char1': {'name': '雨宫优子', 'description': '女主角，高中二年级学生，喜欢阅读。'},
            'char2': {'name': '佐藤隆', 'description': '男主角，高中二年级学生，篮球部成员。'}
        }
        self.dirty = False

# Example Usage (for testing the dialog itself)
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    mock = MockTimeline()
    dialog = CharacterManagerDialog(mock)
    if dialog.exec_():
        print("Character data after dialog:", mock.characters)
        print("Timeline marked dirty:", mock.dirty)
    else:
        print("Character manager dialog cancelled.")
    sys.exit(app.exec_())