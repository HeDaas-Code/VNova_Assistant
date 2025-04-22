# -*- coding: utf-8 -*-
"""
VNova Assistant - 视觉小说制作助手
设置对话框模块
"""

import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFileDialog, QLabel, QComboBox, QGroupBox, QGridLayout
)

from qfluentwidgets import (
    TitleLabel, LineEdit, PushButton, BodyLabel, MessageBox,
    FluentIcon, InfoBar, InfoBarPosition, Action,
    ComboBox, Theme, setTheme, CheckBox
)

# Determine the project root directory (assuming this script is in src/gui)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, 'config.json')

class SettingsDialog(QDialog):
    """A dialog to configure application settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VNova Assistant - 设置")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)

        self.settings = self._load_settings()

        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 创建各个标签页
        self.ollama_tab = QWidget()
        self.appearance_tab = QWidget()
        self.paths_tab = QWidget()
        self.renpy_tab = QWidget()
        self.timeline_tab = QWidget()  # 新增时间轴标签页
        
        # 创建各标签页布局
        self._create_ollama_tab()
        self._create_appearance_tab()
        self._create_paths_tab()
        self._create_renpy_tab()
        self._create_timeline_tab()  # 新增时间轴标签页布局创建
        
        # 添加标签页到标签组件
        self.tab_widget.addTab(self.ollama_tab, "Ollama 设置")
        self.tab_widget.addTab(self.appearance_tab, "外观")
        self.tab_widget.addTab(self.paths_tab, "路径")
        self.tab_widget.addTab(self.renpy_tab, "Ren'Py")
        self.tab_widget.addTab(self.timeline_tab, "时间轴")  # 新增时间轴标签页
        
        layout.addWidget(self.tab_widget)

        # 底部按钮
        button_layout = QHBoxLayout()
        self.save_button = PushButton("保存", self)
        self.save_button.setIcon(FluentIcon.SAVE)
        self.save_button.clicked.connect(self.save_and_accept)
        
        self.cancel_button = PushButton("取消", self)
        self.cancel_button.setIcon(FluentIcon.CANCEL)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

        self._populate_fields()

    def _create_ollama_tab(self):
        """创建Ollama设置标签页"""
        layout = QVBoxLayout(self.ollama_tab)
        
        # Ollama Host
        host_layout = QHBoxLayout()
        host_layout.addWidget(BodyLabel("Ollama 主机地址:"))
        self.host_input = LineEdit()
        host_layout.addWidget(self.host_input)
        layout.addLayout(host_layout)

        # Default Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("默认 Ollama 模型:"))
        self.model_input = LineEdit()
        model_layout.addWidget(self.model_input)
        layout.addLayout(model_layout)
        
        # 高级选项组
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QGridLayout(advanced_group)
        
        # 温度参数
        advanced_layout.addWidget(BodyLabel("生成温度:"), 0, 0)
        self.temperature_input = LineEdit()
        self.temperature_input.setPlaceholderText("默认: 0.7")
        advanced_layout.addWidget(self.temperature_input, 0, 1)
        
        # 最大Token数
        advanced_layout.addWidget(BodyLabel("最大Token数:"), 1, 0)
        self.max_tokens_input = LineEdit()
        self.max_tokens_input.setPlaceholderText("默认: 2048")
        advanced_layout.addWidget(self.max_tokens_input, 1, 1)
        
        # 上下文窗口大小
        advanced_layout.addWidget(BodyLabel("上下文窗口大小:"), 2, 0)
        self.context_window_input = LineEdit()
        self.context_window_input.setPlaceholderText("默认: 4096")
        advanced_layout.addWidget(self.context_window_input, 2, 1)
        
        layout.addWidget(advanced_group)
        layout.addStretch(1)  # 添加弹性空间
        
    def _create_appearance_tab(self):
        """创建外观设置标签页"""
        layout = QVBoxLayout(self.appearance_tab)
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(BodyLabel("界面主题:"))
        self.theme_combobox = ComboBox()
        self.theme_combobox.addItems(["亮色", "暗色", "跟随系统"])
        theme_layout.addWidget(self.theme_combobox)
        layout.addLayout(theme_layout)
        
        # 字体大小
        font_layout = QHBoxLayout()
        font_layout.addWidget(BodyLabel("界面字体大小:"))
        self.font_size_combobox = ComboBox()
        self.font_size_combobox.addItems(["小", "中", "大"])
        font_layout.addWidget(self.font_size_combobox)
        layout.addLayout(font_layout)
        
        # 界面语言
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("界面语言:"))
        self.language_combobox = ComboBox()
        self.language_combobox.addItems(["简体中文", "English"])
        lang_layout.addWidget(self.language_combobox)
        layout.addLayout(lang_layout)
        
        # 启动设置
        startup_group = QGroupBox("启动设置")
        startup_layout = QVBoxLayout(startup_group)
        
        self.restore_layout_checkbox = CheckBox("启动时恢复上次窗口布局")
        startup_layout.addWidget(self.restore_layout_checkbox)
        
        self.auto_connect_checkbox = CheckBox("启动时自动连接Ollama")
        startup_layout.addWidget(self.auto_connect_checkbox)
        
        layout.addWidget(startup_group)
        layout.addStretch(1)  # 添加弹性空间
        
    def _create_paths_tab(self):
        """创建路径设置标签页"""
        layout = QVBoxLayout(self.paths_tab)
        
        # 素材库默认路径
        assets_path_layout = QHBoxLayout()
        assets_path_layout.addWidget(BodyLabel("素材库默认路径:"))
        self.assets_path_input = LineEdit()
        assets_path_input_default = os.path.join(PROJECT_ROOT, "assets")
        self.assets_path_input.setPlaceholderText(assets_path_input_default)
        assets_path_layout.addWidget(self.assets_path_input)
        
        self.browse_assets_path_button = PushButton("浏览...", self)
        self.browse_assets_path_button.clicked.connect(lambda: self._browse_directory(self.assets_path_input))
        assets_path_layout.addWidget(self.browse_assets_path_button)
        layout.addLayout(assets_path_layout)
        
        # 项目保存默认路径
        projects_path_layout = QHBoxLayout()
        projects_path_layout.addWidget(BodyLabel("项目保存默认路径:"))
        self.projects_path_input = LineEdit()
        projects_path_input_default = os.path.join(PROJECT_ROOT, "projects")
        self.projects_path_input.setPlaceholderText(projects_path_input_default)
        projects_path_layout.addWidget(self.projects_path_input)
        
        self.browse_projects_path_button = PushButton("浏览...", self)
        self.browse_projects_path_button.clicked.connect(lambda: self._browse_directory(self.projects_path_input))
        projects_path_layout.addWidget(self.browse_projects_path_button)
        layout.addLayout(projects_path_layout)
        
        # 导出默认路径
        export_path_layout = QHBoxLayout()
        export_path_layout.addWidget(BodyLabel("导出默认路径:"))
        self.export_path_input = LineEdit()
        export_path_input_default = os.path.join(PROJECT_ROOT, "exports")
        self.export_path_input.setPlaceholderText(export_path_input_default)
        export_path_layout.addWidget(self.export_path_input)
        
        self.browse_export_path_button = PushButton("浏览...", self)
        self.browse_export_path_button.clicked.connect(lambda: self._browse_directory(self.export_path_input))
        export_path_layout.addWidget(self.browse_export_path_button)
        layout.addLayout(export_path_layout)
        
        layout.addStretch(1)  # 添加弹性空间
        
    def _create_renpy_tab(self):
        """创建Ren'Py设置标签页"""
        layout = QVBoxLayout(self.renpy_tab)
        
        # Ren'Py可执行文件路径
        renpy_path_layout = QHBoxLayout()
        renpy_path_layout.addWidget(BodyLabel("Ren'Py 可执行文件路径:"))
        self.renpy_path_input = LineEdit()
        renpy_path_layout.addWidget(self.renpy_path_input)
        
        self.browse_renpy_path_button = PushButton("浏览...", self)
        self.browse_renpy_path_button.clicked.connect(lambda: self._browse_file(self.renpy_path_input))
        renpy_path_layout.addWidget(self.browse_renpy_path_button)
        layout.addLayout(renpy_path_layout)
        
        # 默认分辨率
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(BodyLabel("默认游戏分辨率:"))
        self.resolution_combobox = ComboBox()
        self.resolution_combobox.addItems(["1280x720", "1920x1080", "800x600", "640x480"])
        resolution_layout.addWidget(self.resolution_combobox)
        layout.addLayout(resolution_layout)
        
        # 项目创建设置
        project_group = QGroupBox("项目创建设置")
        project_layout = QVBoxLayout(project_group)
        
        self.create_directories_checkbox = CheckBox("自动创建标准目录结构")
        project_layout.addWidget(self.create_directories_checkbox)
        
        self.use_templates_checkbox = CheckBox("使用模板文件")
        project_layout.addWidget(self.use_templates_checkbox)
        
        layout.addWidget(project_group)
        
        # Ren'Py运行设置
        run_group = QGroupBox("Ren'Py运行设置")
        run_layout = QVBoxLayout(run_group)
        
        self.skip_splashscreen_checkbox = CheckBox("跳过启动画面")
        run_layout.addWidget(self.skip_splashscreen_checkbox)
        
        self.debug_mode_checkbox = CheckBox("开发者调试模式")
        run_layout.addWidget(self.debug_mode_checkbox)
        
        layout.addWidget(run_group)
        layout.addStretch(1)  # 添加弹性空间
        
    def _create_timeline_tab(self):
        """创建时间轴设置标签页"""
        layout = QVBoxLayout(self.timeline_tab)
        
        # 时间轴节点显示组
        node_display_group = QGroupBox("节点显示设置")
        node_display_layout = QGridLayout(node_display_group)
        
        # 默认显示模式
        node_display_layout.addWidget(QLabel("默认显示模式:"), 0, 0)
        self.default_view_mode_combobox = ComboBox()
        self.default_view_mode_combobox.addItems(["线性视图", "图形视图"])
        node_display_layout.addWidget(self.default_view_mode_combobox, 0, 1)
        
        # 节点颜色设置
        node_display_layout.addWidget(QLabel("分支节点颜色:"), 1, 0)
        self.branch_node_color_combobox = ComboBox()
        self.branch_node_color_combobox.addItems(["蓝色", "绿色", "紫色", "红色"])
        node_display_layout.addWidget(self.branch_node_color_combobox, 1, 1)
        
        # 节点展开设置
        node_display_layout.addWidget(QLabel("显示节点内容:"), 2, 0)
        self.node_content_display_combobox = ComboBox()
        self.node_content_display_combobox.addItems(["简洁（仅标题）", "详细（显示部分内容）", "完整（全部内容）"])
        node_display_layout.addWidget(self.node_content_display_combobox, 2, 1)
        
        # 节点布局设置
        layout_settings_group = QGroupBox("布局设置")
        layout_settings_layout = QGridLayout(layout_settings_group)
        
        layout_settings_layout.addWidget(QLabel("节点间距:"), 0, 0)
        self.node_spacing_combobox = ComboBox()
        self.node_spacing_combobox.addItems(["紧凑", "标准", "宽松"])
        layout_settings_layout.addWidget(self.node_spacing_combobox, 0, 1)
        
        layout_settings_layout.addWidget(QLabel("图形视图方向:"), 1, 0)
        self.graph_direction_combobox = ComboBox()
        self.graph_direction_combobox.addItems(["自上而下", "自左向右"])
        layout_settings_layout.addWidget(self.graph_direction_combobox, 1, 1)
        
        # 自动保存设置
        autosave_group = QGroupBox("自动保存设置")
        autosave_layout = QGridLayout(autosave_group)
        
        self.autosave_enabled_checkbox = CheckBox("启用自动保存")
        autosave_layout.addWidget(self.autosave_enabled_checkbox, 0, 0, 1, 2)
        
        autosave_layout.addWidget(QLabel("自动保存间隔 (分钟):"), 1, 0)
        self.autosave_interval_combobox = ComboBox()
        self.autosave_interval_combobox.addItems(["1", "5", "10", "15", "30"])
        autosave_layout.addWidget(self.autosave_interval_combobox, 1, 1)
        
        # 添加组到主布局
        layout.addWidget(node_display_group)
        layout.addWidget(layout_settings_group)
        layout.addWidget(autosave_group)
        layout.addStretch()

    def _browse_directory(self, line_edit):
        """打开目录选择对话框并更新输入框"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录")
        if dir_path:
            line_edit.setText(dir_path)
            
    def _browse_file(self, line_edit):
        """打开文件选择对话框并更新输入框"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            line_edit.setText(file_path)

    def _load_settings(self):
        """Loads settings from the config file."""
        default_settings = {
            "ollama_host": "http://localhost:11434",
            "default_model": "llama3",
            "temperature": "0.7",
            "max_tokens": "2048",
            "context_window": "4096",
            "theme": "亮色",
            "font_size": "中",
            "language": "简体中文",
            "restore_layout": True,
            "auto_connect": True,
            "assets_path": "",
            "projects_path": "",
            "export_path": "",
            "renpy_path": "",
            "default_resolution": "1280x720",
            "create_directories": True,
            "use_templates": True,
            "skip_splashscreen": False,
            "debug_mode": False,
            # 时间轴默认设置
            "default_view_mode": "线性视图",
            "branch_node_color": "蓝色",
            "node_content_display": "简洁（仅标题）",
            "node_spacing": "标准",
            "graph_direction": "自上而下",
            "autosave_enabled": True,
            "autosave_interval": "5"
        }
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Ensure essential keys exist, merge with defaults
                    for key, value in default_settings.items():
                        if key not in loaded_settings:
                            loaded_settings[key] = value
                    return loaded_settings
            except json.JSONDecodeError:
                MessageBox("加载错误", f"无法解析配置文件 {CONFIG_FILE_PATH}。将使用默认设置。", 
                           self).exec()
            except Exception as e:
                MessageBox("加载错误", f"加载配置文件时出错: {e}。将使用默认设置。", 
                           self).exec()
        else:
            InfoBar.success(
                title="信息",
                content=f"未找到配置文件，将创建并使用默认设置。",
                orient=InfoBarPosition.TOP,
                parent=self
            )
        return default_settings

    def _populate_fields(self):
        """Populates the input fields with loaded settings."""
        # Ollama设置
        self.host_input.setText(self.settings.get("ollama_host", ""))
        self.model_input.setText(self.settings.get("default_model", ""))
        self.temperature_input.setText(str(self.settings.get("temperature", "")))
        self.max_tokens_input.setText(str(self.settings.get("max_tokens", "")))
        self.context_window_input.setText(str(self.settings.get("context_window", "")))
        
        # 外观设置
        self.theme_combobox.setCurrentText(self.settings.get("theme", "亮色"))
        self.font_size_combobox.setCurrentText(self.settings.get("font_size", "中"))
        self.language_combobox.setCurrentText(self.settings.get("language", "简体中文"))
        self.restore_layout_checkbox.setChecked(self.settings.get("restore_layout", True))
        self.auto_connect_checkbox.setChecked(self.settings.get("auto_connect", True))
        
        # 路径设置
        self.assets_path_input.setText(self.settings.get("assets_path", ""))
        self.projects_path_input.setText(self.settings.get("projects_path", ""))
        self.export_path_input.setText(self.settings.get("export_path", ""))
        
        # Ren'Py设置
        self.renpy_path_input.setText(self.settings.get("renpy_path", ""))
        self.resolution_combobox.setCurrentText(self.settings.get("default_resolution", "1280x720"))
        self.create_directories_checkbox.setChecked(self.settings.get("create_directories", True))
        self.use_templates_checkbox.setChecked(self.settings.get("use_templates", True))
        self.skip_splashscreen_checkbox.setChecked(self.settings.get("skip_splashscreen", False))
        self.debug_mode_checkbox.setChecked(self.settings.get("debug_mode", False))
        
        # 时间轴设置
        self.default_view_mode_combobox.setCurrentText(self.settings.get("default_view_mode", "线性视图"))
        self.branch_node_color_combobox.setCurrentText(self.settings.get("branch_node_color", "蓝色"))
        self.node_content_display_combobox.setCurrentText(self.settings.get("node_content_display", "简洁（仅标题）"))
        self.node_spacing_combobox.setCurrentText(self.settings.get("node_spacing", "标准"))
        self.graph_direction_combobox.setCurrentText(self.settings.get("graph_direction", "自上而下"))
        self.autosave_enabled_checkbox.setChecked(self.settings.get("autosave_enabled", True))
        self.autosave_interval_combobox.setCurrentText(self.settings.get("autosave_interval", "5"))

    def _save_settings(self):
        """Saves the current settings to the config file."""
        updated_settings = {
            # Ollama设置
            "ollama_host": self.host_input.text().strip(),
            "default_model": self.model_input.text().strip(),
            "temperature": self.temperature_input.text().strip(),
            "max_tokens": self.max_tokens_input.text().strip(),
            "context_window": self.context_window_input.text().strip(),
            
            # 外观设置
            "theme": self.theme_combobox.currentText(),
            "font_size": self.font_size_combobox.currentText(),
            "language": self.language_combobox.currentText(),
            "restore_layout": self.restore_layout_checkbox.isChecked(),
            "auto_connect": self.auto_connect_checkbox.isChecked(),
            
            # 路径设置
            "assets_path": self.assets_path_input.text().strip(),
            "projects_path": self.projects_path_input.text().strip(),
            "export_path": self.export_path_input.text().strip(),
            
            # Ren'Py设置
            "renpy_path": self.renpy_path_input.text().strip(),
            "default_resolution": self.resolution_combobox.currentText(),
            "create_directories": self.create_directories_checkbox.isChecked(),
            "use_templates": self.use_templates_checkbox.isChecked(),
            "skip_splashscreen": self.skip_splashscreen_checkbox.isChecked(),
            "debug_mode": self.debug_mode_checkbox.isChecked(),
            
            # 时间轴设置
            "default_view_mode": self.default_view_mode_combobox.currentText(),
            "branch_node_color": self.branch_node_color_combobox.currentText(),
            "node_content_display": self.node_content_display_combobox.currentText(),
            "node_spacing": self.node_spacing_combobox.currentText(),
            "graph_direction": self.graph_direction_combobox.currentText(),
            "autosave_enabled": self.autosave_enabled_checkbox.isChecked(),
            "autosave_interval": self.autosave_interval_combobox.currentText()
        }
        try:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(updated_settings, f, indent=2, ensure_ascii=False)
            self.settings = updated_settings # Update internal state
            
            # 应用主题设置
            if updated_settings["theme"] == "亮色":
                setTheme(Theme.LIGHT)
            elif updated_settings["theme"] == "暗色":
                setTheme(Theme.DARK)
            # 跟随系统的情况交由QFluentWidgets自动处理
            
            return True
        except Exception as e:
            MessageBox("保存错误", f"无法保存设置到 {CONFIG_FILE_PATH}: {e}", 
                       self).exec()
            return False

    def save_and_accept(self):
        """Saves settings and closes the dialog if successful."""
        if self._save_settings():
            InfoBar.success(
                title="成功",
                content="设置已保存",
                orient=InfoBarPosition.TOP,
                parent=self.parent()
            )
            self.accept() # Close dialog with accept status

# Example Usage (for testing the dialog itself)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    if dialog.exec_():
        print("Settings saved:", dialog.settings)
    else:
        print("Settings dialog cancelled.")
    sys.exit(app.exec_())