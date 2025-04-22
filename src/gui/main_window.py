# -*- coding: utf-8 -*-
"""
VNova Assistant - 视觉小说制作助手
主应用程序窗口实现
"""

import sys
import json
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QSplitter, QListWidget,
    QMenuBar, QStatusBar, QMessageBox, QFileDialog, QListWidgetItem, QAction, QDockWidget, QDialog, QComboBox
)
from PyQt5.QtGui import QIcon # Assuming you might add icons later
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject, QSettings, QTimer

# Import Fluent Widgets
from qfluentwidgets import (
    PushButton, TextEdit, LineEdit, TitleLabel, BodyLabel, CaptionLabel, 
    SplitFluentWindow, NavigationBar, NavigationPanel, FluentIcon, MessageBox,
    InfoBar, InfoBarPosition, setTheme, Theme, SubtitleLabel, ListWidget, Action,
    SearchLineEdit, SplitTitleBar
)

# Import from other modules
from src.story_manager.story_timeline import StoryTimeline, StoryEvent
from src.ollama_interface.ollama_client import OllamaClient
from src.emotion_analyzer.analyzer import EmotionAnalyzer
# Import the settings dialog
from .settings_dialog import SettingsDialog
# Import the advanced timeline widget
from .story_timeline_widget import StoryTimelineWidget

# Check if snownlp is available for the analyzer
try:
    from snownlp import SnowNLP
except ImportError:
    SnowNLP = None # Set SnowNLP to None if import fails

# --- Worker Class for Ollama --- 
class OllamaWorker(QObject):
    """Worker object to handle Ollama generation in a separate thread."""
    finished = pyqtSignal(str, dict) # request_id, result_dict
    error = pyqtSignal(str, str)    # request_id, error_message

    def __init__(self, client, prompt, char_info, world_info):
        super().__init__()
        self.client = client
        self.prompt = prompt
        self.char_info = char_info
        self.world_info = world_info
        self.request_id = "unknown" # Placeholder

    @pyqtSlot()
    def run(self):
        """Execute the Ollama generation task."""
        if not self.client:
            self.error.emit("init_failed", "Ollama client is not initialized.")
            return
        try:
            # The client method returns request_id and result dictionary
            self.request_id, result = self.client.generate_story_segment(
                self.prompt, self.char_info, self.world_info
            )

            if 'error' in result:
                error_msg = f"{result['error']}\nRaw: {result.get('raw_content', '')}"
                self.error.emit(self.request_id, error_msg)
            else:
                self.finished.emit(self.request_id, result)

        except ConnectionError as ce:
            self.error.emit(self.request_id, f"无法连接到 Ollama: {ce}")
        except Exception as e:
            self.error.emit(self.request_id, f"生成过程中发生意外错误: {e}")


class MainWindow(QMainWindow):
    """Main application window class."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VNova Assistant - 视觉小说制作助手")
        self.setGeometry(100, 100, 1400, 900) # 扩大默认窗口尺寸
        self.current_project_path = None # To store the path of the current project file

        # Initialize core components
        self.timeline = StoryTimeline()
        self.config_path = 'config.json' # Path to the config file
        self.ollama_client = None # Initialize lazily or on first use
        self.emotion_analyzer = EmotionAnalyzer()
        self.ollama_thread = None # Thread for Ollama calls
        self.ollama_worker = None # Worker for Ollama calls
        
        # 自动保存计时器
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.auto_save_project)

        # 创建核心组件
        self._create_central_widget()
        self._create_dock_widgets()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        
        self._connect_signals()
        self.refresh_timeline_view() # Initial refresh for empty timeline
        self.update_emotion_button_state() # Initial state
        self.refresh_asset_list('backgrounds') # 初始加载素材列表

        # 读取保存的布局(如果有)
        self._load_window_layout()

        # 启动自动保存
        self._setup_autosave()

    def _create_central_widget(self):
        """创建中央预览区域"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        central_layout = QVBoxLayout(self.central_widget)
        
        # 预览标题
        preview_header = QHBoxLayout()
        preview_title = SubtitleLabel("预览区域")
        preview_header.addWidget(preview_title)
        
        # 添加临时运行按钮
        self.run_preview_button = PushButton("临时运行", self)
        self.run_preview_button.setIcon(FluentIcon.PLAY)
        self.run_preview_button.clicked.connect(self.run_preview)
        preview_header.addStretch()
        preview_header.addWidget(self.run_preview_button)
        
        central_layout.addLayout(preview_header)
        
        # 预览区域
        self.preview_area = QWidget()
        self.preview_area.setMinimumSize(800, 600)
        self.preview_area.setStyleSheet("background-color: #f0f0f0; border: 1px solid #cccccc;")
        
        # 创建预览区域的布局
        preview_layout = QVBoxLayout(self.preview_area)
        preview_layout.setAlignment(Qt.AlignCenter)
        preview_message = BodyLabel("此处将显示Ren'Py项目预览")
        preview_message.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_message)
        
        central_layout.addWidget(self.preview_area)

    def _create_dock_widgets(self):
        """创建所有可停靠窗口"""
        # 1. 创建时间线/故事节点窗口
        self.timeline_dock = QDockWidget("故事时间线/节点", self)
        self.timeline_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.timeline_dock.setFeatures(QDockWidget.DockWidgetMovable | 
                                     QDockWidget.DockWidgetFloatable)
        
        # 时间线内容
        timeline_content = QWidget()
        timeline_layout = QVBoxLayout(timeline_content)
        
        # 使用高级时间线组件替代简单列表
        self.timeline_widget = StoryTimelineWidget()
        self.timeline_widget.nodeSelected.connect(self.display_node_content)
        timeline_layout.addWidget(self.timeline_widget)
        
        # 添加撤销按钮
        self.undo_button = PushButton("撤销上次Ollama生成")
        self.undo_button.setIcon(FluentIcon.RETURN)
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self.undo_last_ollama)
        timeline_layout.addWidget(self.undo_button)
        
        # 不再需要单独的添加分支按钮，因为新组件已包含此功能
        # self.add_branch_button = PushButton("添加分支节点", self)
        # self.add_branch_button.setIcon(FluentIcon.CARE_RIGHT_SOLID)
        # self.add_branch_button.clicked.connect(self.add_branch_node)
        # timeline_layout.addWidget(self.add_branch_button)
        
        self.timeline_dock.setWidget(timeline_content)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.timeline_dock)
        
        # 2. 创建编辑器窗口
        self.editor_dock = QDockWidget("剧情编辑器", self)
        self.editor_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.editor_dock.setFeatures(QDockWidget.DockWidgetMovable | 
                                   QDockWidget.DockWidgetFloatable)
        
        # 编辑器内容
        editor_content = QWidget()
        editor_layout = QVBoxLayout(editor_content)
        
        self.editor_area = TextEdit()
        self.editor_area.setPlaceholderText("在此处编辑或查看剧情节点内容...")
        self.editor_area.setReadOnly(True)
        editor_layout.addWidget(self.editor_area)
        
        self.editor_dock.setWidget(editor_content)
        self.addDockWidget(Qt.RightDockWidgetArea, self.editor_dock)
        
        # 3. 创建Ollama交互窗口
        self.ollama_dock = QDockWidget("Ollama 生成交互", self)
        self.ollama_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.ollama_dock.setFeatures(QDockWidget.DockWidgetMovable | 
                                   QDockWidget.DockWidgetFloatable)
        
        # Ollama内容
        ollama_content = QWidget()
        ollama_layout = QVBoxLayout(ollama_content)
        
        # Ollama提示输入
        ollama_layout.addWidget(SubtitleLabel("Ollama 生成提示"))
        self.ollama_prompt_input = TextEdit()
        self.ollama_prompt_input.setFixedHeight(100)
        self.ollama_prompt_input.setPlaceholderText("输入生成剧情的提示 (将附加到选中节点后)...")
        ollama_layout.addWidget(self.ollama_prompt_input)
        
        self.generate_button = PushButton("生成剧情", self)
        self.generate_button.setIcon(FluentIcon.ROBOT)
        ollama_layout.addWidget(self.generate_button)
        
        # Ollama输出区域
        ollama_layout.addWidget(SubtitleLabel("Ollama 输出/建议"))
        self.ollama_output_area = TextEdit()
        self.ollama_output_area.setReadOnly(True)
        self.ollama_output_area.setFixedHeight(150)
        ollama_layout.addWidget(self.ollama_output_area)
        
        # 情感分析区域
        ollama_layout.addWidget(SubtitleLabel("情绪分析"))
        self.emotion_display = BodyLabel("情绪: -")
        ollama_layout.addWidget(self.emotion_display)
        
        self.analyze_emotion_button = PushButton("分析情绪", self)
        self.analyze_emotion_button.setIcon(FluentIcon.HEART)
        ollama_layout.addWidget(self.analyze_emotion_button)
        
        self.ollama_dock.setWidget(ollama_content)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ollama_dock)
        
        # 4. 创建角色管理窗口
        self.character_dock = QDockWidget("角色管理", self)
        self.character_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.character_dock.setFeatures(QDockWidget.DockWidgetMovable | 
                                      QDockWidget.DockWidgetFloatable)
        
        # 角色管理内容
        character_content = QWidget()
        character_layout = QVBoxLayout(character_content)
        
        self.manage_characters_button = PushButton("管理角色", self)
        self.manage_characters_button.setIcon(FluentIcon.PEOPLE)
        character_layout.addWidget(self.manage_characters_button)
        
        # 世界观设定
        character_layout.addWidget(SubtitleLabel("世界观设定"))
        self.worldview_info_area = TextEdit()
        self.worldview_info_area.setPlaceholderText("输入世界观信息 (将包含在发送给Ollama的提示中)...")
        character_layout.addWidget(self.worldview_info_area)
        
        self.character_dock.setWidget(character_content)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.character_dock)
        
        # 5. 创建素材库窗口
        self.asset_dock = QDockWidget("素材库", self)
        self.asset_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.asset_dock.setFeatures(QDockWidget.DockWidgetMovable | 
                                  QDockWidget.DockWidgetFloatable)
        
        # 素材库内容
        asset_content = QWidget()
        asset_layout = QVBoxLayout(asset_content)
        
        # 素材类别标签
        asset_layout.addWidget(SubtitleLabel("素材类别"))
        
        # 素材类别选择 - 使用更美观的布局
        asset_type_layout = QHBoxLayout()
        asset_type_layout.setSpacing(10)  # 增加按钮之间的间距
        
        # 使用自定义样式使按钮更加清晰
        button_style = """
        QPushButton {
            padding: 8px 12px;
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: #f5f5f5;
        }
        QPushButton:checked {
            background-color: #ddeeff;
            border: 2px solid #3399ff;
            font-weight: bold;
        }
        """
        
        self.asset_type_button_bg = PushButton("背景", self)
        self.asset_type_button_bg.setCheckable(True)
        self.asset_type_button_bg.setChecked(True)  # 默认选中背景
        self.asset_type_button_bg.setMinimumWidth(70)
        self.asset_type_button_bg.setStyleSheet(button_style)
        
        self.asset_type_button_char = PushButton("角色", self)
        self.asset_type_button_char.setCheckable(True)
        self.asset_type_button_char.setMinimumWidth(70)
        self.asset_type_button_char.setStyleSheet(button_style)
        
        self.asset_type_button_sound = PushButton("音效", self)
        self.asset_type_button_sound.setCheckable(True)
        self.asset_type_button_sound.setMinimumWidth(70)
        self.asset_type_button_sound.setStyleSheet(button_style)
        
        self.asset_type_button_music = PushButton("音乐", self)
        self.asset_type_button_music.setCheckable(True)
        self.asset_type_button_music.setMinimumWidth(70)
        self.asset_type_button_music.setStyleSheet(button_style)
        
        asset_type_layout.addWidget(self.asset_type_button_bg)
        asset_type_layout.addWidget(self.asset_type_button_char)
        asset_type_layout.addWidget(self.asset_type_button_sound)
        asset_type_layout.addWidget(self.asset_type_button_music)
        asset_type_layout.addStretch(1)  # 添加弹性空间
        
        asset_layout.addLayout(asset_type_layout)
        
        # 添加当前选择标签
        self.asset_category_label = BodyLabel("当前类别: 背景")
        asset_layout.addWidget(self.asset_category_label)
        
        # 素材列表
        asset_layout.addWidget(SubtitleLabel("素材列表"))
        self.asset_list = ListWidget()
        asset_layout.addWidget(self.asset_list)
        
        # 素材操作按钮
        asset_buttons_layout = QHBoxLayout()
        self.asset_add_button = PushButton("添加素材", self)
        self.asset_add_button.setIcon(FluentIcon.ADD)
        self.asset_add_button.clicked.connect(self.add_asset)
        
        self.asset_remove_button = PushButton("删除素材", self)
        self.asset_remove_button.setIcon(FluentIcon.DELETE)
        self.asset_remove_button.clicked.connect(self.remove_asset)
        
        asset_buttons_layout.addWidget(self.asset_add_button)
        asset_buttons_layout.addWidget(self.asset_remove_button)
        
        asset_layout.addLayout(asset_buttons_layout)
        
        self.asset_dock.setWidget(asset_content)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.asset_dock)
        
        # 6. 创建Ren'Py编辑器窗口
        self.renpy_dock = QDockWidget("Ren'Py 编辑器", self)
        self.renpy_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.renpy_dock.setFeatures(QDockWidget.DockWidgetMovable | 
                                  QDockWidget.DockWidgetFloatable)
        
        # Ren'Py编辑器内容
        renpy_content = QWidget()
        renpy_layout = QVBoxLayout(renpy_content)
        
        # Ren'Py项目操作
        renpy_buttons_layout = QHBoxLayout()
        self.renpy_new_button = PushButton("新建Ren'Py项目", self)
        self.renpy_new_button.setIcon(FluentIcon.DOCUMENT)
        self.renpy_new_button.clicked.connect(self.create_renpy_project)
        
        self.renpy_import_button = PushButton("导入剧情", self)
        self.renpy_import_button.setIcon(FluentIcon.DOWNLOAD)
        self.renpy_import_button.clicked.connect(self.import_to_renpy)
        
        renpy_buttons_layout.addWidget(self.renpy_new_button)
        renpy_buttons_layout.addWidget(self.renpy_import_button)
        
        renpy_layout.addLayout(renpy_buttons_layout)
        
        # Ren'Py代码编辑区
        self.renpy_editor = TextEdit()
        self.renpy_editor.setPlaceholderText("这里将显示生成的Ren'Py代码")
        renpy_layout.addWidget(self.renpy_editor)
        
        # Ren'Py操作按钮
        renpy_action_layout = QHBoxLayout()
        self.renpy_update_button = PushButton("更新预览", self)
        self.renpy_update_button.setIcon(FluentIcon.SYNC)
        self.renpy_update_button.clicked.connect(self.update_renpy_preview)
        
        self.renpy_save_button = PushButton("保存代码", self)
        self.renpy_save_button.setIcon(FluentIcon.SAVE)
        self.renpy_save_button.clicked.connect(self.save_renpy_code)
        
        renpy_action_layout.addWidget(self.renpy_update_button)
        renpy_action_layout.addWidget(self.renpy_save_button)
        
        renpy_layout.addLayout(renpy_action_layout)
        
        self.renpy_dock.setWidget(renpy_content)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.renpy_dock)
        
        # 设置标签栏，允许标签模式停靠
        self.tabifyDockWidget(self.ollama_dock, self.editor_dock)
        self.tabifyDockWidget(self.character_dock, self.asset_dock)

    def _create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("&文件")

        new_action = Action(FluentIcon.DOCUMENT, "新建", self)
        new_action.triggered.connect(self.new_project)
        
        open_action = Action(FluentIcon.FOLDER, "打开", self)
        open_action.triggered.connect(self.open_project)
        
        save_action = Action(FluentIcon.SAVE, "保存", self)
        save_action.triggered.connect(self.save_project)
        
        save_as_action = Action(FluentIcon.SAVE_AS, "另存为...", self)
        save_as_action.triggered.connect(self.save_project_as)
        
        exit_action = Action(FluentIcon.CLOSE, "退出", self)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menu_bar.addMenu("&编辑")
        
        settings_action = Action(FluentIcon.SETTING, "设置...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        
        edit_menu.addAction(settings_action)

        # 窗口菜单
        window_menu = menu_bar.addMenu("&窗口")
        
        save_layout_action = Action(FluentIcon.EMBED, "保存当前布局", self)
        save_layout_action.triggered.connect(self.save_window_layout)
        
        reset_layout_action = Action(FluentIcon.RETURN, "重置默认布局", self)
        reset_layout_action.triggered.connect(self.reset_window_layout)
        
        window_menu.addAction(save_layout_action)
        window_menu.addAction(reset_layout_action)
        
        # Ren'Py菜单
        renpy_menu = menu_bar.addMenu("&Ren'Py")
        
        init_renpy_action = Action(FluentIcon.DOCUMENT, "初始化项目", self)
        init_renpy_action.triggered.connect(self.create_renpy_project)
        
        build_renpy_action = Action(FluentIcon.PLAY, "构建项目", self)
        build_renpy_action.triggered.connect(self.build_renpy_project)
        
        export_renpy_action = Action(FluentIcon.DOWNLOAD, "导出项目", self)
        export_renpy_action.triggered.connect(self.export_renpy_project)
        
        renpy_menu.addAction(init_renpy_action)
        renpy_menu.addAction(build_renpy_action)
        renpy_menu.addAction(export_renpy_action)

    def _create_toolbars(self):
        """创建工具栏"""
        main_toolbar = self.addToolBar("主工具栏")
        main_toolbar.setMovable(True)
        
        # 添加工具栏按钮
        new_project_action = Action(FluentIcon.DOCUMENT, "新建项目", self)
        new_project_action.triggered.connect(self.new_project)
        main_toolbar.addAction(new_project_action)
        
        open_project_action = Action(FluentIcon.FOLDER, "打开项目", self)
        open_project_action.triggered.connect(self.open_project)
        main_toolbar.addAction(open_project_action)
        
        save_project_action = Action(FluentIcon.SAVE, "保存项目", self)
        save_project_action.triggered.connect(self.save_project)
        main_toolbar.addAction(save_project_action)
        
        main_toolbar.addSeparator()
        
        # Ren'Py相关
        renpy_init_action = Action(FluentIcon.DOCUMENT, "初始化Ren'Py项目", self)
        renpy_init_action.triggered.connect(self.create_renpy_project)
        main_toolbar.addAction(renpy_init_action)
        
        run_preview_action = Action(FluentIcon.PLAY, "运行预览", self)
        run_preview_action.triggered.connect(self.run_preview)
        main_toolbar.addAction(run_preview_action)

    def _create_status_bar(self):
        """创建状态栏"""
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")

    def _save_window_layout(self):
        """保存当前窗口布局"""
        settings = QSettings("Galgame", "StoryAssistant")
        settings.setValue("windowGeometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        InfoBar.success(
            title="成功",
            content="窗口布局已保存",
            orient=InfoBarPosition.TOP,
            parent=self
        )

    def _load_window_layout(self):
        """加载保存的窗口布局"""
        settings = QSettings("Galgame", "StoryAssistant")
        if settings.contains("windowGeometry"):
            self.restoreGeometry(settings.value("windowGeometry"))
        if settings.contains("windowState"):
            self.restoreState(settings.value("windowState"))

    def save_window_layout(self):
        """保存窗口布局动作"""
        self._save_window_layout()

    def reset_window_layout(self):
        """重置窗口布局到默认状态"""
        # 恢复默认布局
        for dock in [self.timeline_dock, self.editor_dock, self.ollama_dock, 
                    self.character_dock, self.asset_dock, self.renpy_dock]:
            self.removeDockWidget(dock)
        
        # 重新添加所有dock widgets到默认位置
        self.addDockWidget(Qt.LeftDockWidgetArea, self.timeline_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.character_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.editor_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ollama_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.asset_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.renpy_dock)
        
        # 设置标签栏
        self.tabifyDockWidget(self.ollama_dock, self.editor_dock)
        self.tabifyDockWidget(self.character_dock, self.asset_dock)
        
        # 显示所有dock widgets
        for dock in [self.timeline_dock, self.editor_dock, self.ollama_dock, 
                    self.character_dock, self.asset_dock, self.renpy_dock]:
            dock.show()
        
        InfoBar.success(
            title="成功",
            content="窗口布局已重置为默认",
            orient=InfoBarPosition.TOP,
            parent=self
        )

    # ---- 新增功能相关方法 ----
    
    def add_branch_node(self):
        """添加分支节点"""
        # 获取当前选中的节点
        current_node_id = self.get_selected_timeline_node_id()
        if not current_node_id:
            MessageBox("提示", "请先选择一个节点作为分支的起点", self).exec()
            return
            
        # 创建分支节点对话框
        self.create_branch_dialog(current_node_id)
    
    def create_branch_dialog(self, parent_node_id):
        """创建分支对话框"""
        # 在此实现分支对话框的创建逻辑
        # TODO: 实现完整的分支创建逻辑
        InfoBar.info(
            title="开发中",
            content="分支节点功能开发中",
            orient=InfoBarPosition.TOP,
            parent=self
        )
    
    def add_asset(self):
        """添加新素材"""
        # 获取当前选择的素材类别
        category = self._get_current_asset_category()
        if not category:
            MessageBox("错误", "请选择素材类别", self).exec()
            return
            
        # 根据不同类别选择不同的文件类型
        file_filter = ""
        if category == 'backgrounds' or category == 'characters':
            file_filter = "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        elif category == 'sounds':
            file_filter = "音效文件 (*.wav *.mp3 *.ogg);;所有文件 (*)"
        elif category == 'music':
            file_filter = "音乐文件 (*.mp3 *.ogg *.wav);;所有文件 (*)"
            
        # 打开文件选择对话框
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择素材文件", "", file_filter, options=options
        )
        
        if not files:
            return  # 用户取消选择
            
        # 创建素材目录(如果不存在)
        if hasattr(self, 'renpy_project_path') and self.renpy_project_path:
            asset_dir = os.path.join(self.renpy_project_path, 'game')
            
            # 不同类型素材存放在不同目录
            if category == 'backgrounds':
                asset_dir = os.path.join(asset_dir, 'images', 'bg')
            elif category == 'characters':
                asset_dir = os.path.join(asset_dir, 'images', 'chara')
            elif category == 'sounds':
                asset_dir = os.path.join(asset_dir, 'audio', 'sfx')
            elif category == 'music':
                asset_dir = os.path.join(asset_dir, 'audio', 'music')
                
            # 创建目录
            os.makedirs(asset_dir, exist_ok=True)
        else:
            # 没有Ren'Py项目时，创建临时素材目录
            asset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', category)
            os.makedirs(asset_dir, exist_ok=True)
        
        # 导入素材文件
        imported_count = 0
        for file_path in files:
            try:
                # 获取文件名
                file_name = os.path.basename(file_path)
                
                # 复制文件
                dest_path = os.path.join(asset_dir, file_name)
                import shutil
                shutil.copy2(file_path, dest_path)
                
                # 获取基本描述信息
                import mimetypes
                mime_type = mimetypes.guess_type(file_path)[0] or "unknown"
                file_size = os.path.getsize(file_path)
                
                # 添加素材信息到时间线
                asset_data = {
                    'path': dest_path,
                    'filename': file_name,
                    'type': mime_type,
                    'size': file_size,
                    'date_added': datetime.datetime.now().isoformat()
                }
                
                # 对于图片，尝试获取尺寸
                if mime_type and mime_type.startswith('image/'):
                    try:
                        from PIL import Image
                        with Image.open(file_path) as img:
                            asset_data['width'], asset_data['height'] = img.size
                    except (ImportError, Exception) as e:
                        print(f"无法获取图片尺寸: {e}")
                
                self.timeline.add_asset(category, file_name, asset_data)
                imported_count += 1
                
            except Exception as e:
                MessageBox("导入错误", f"导入 {file_path} 时出错:\n{e}", self).exec()
        
        if imported_count > 0:
            self.timeline.dirty = True
            self.refresh_asset_list(category)
            InfoBar.success(
                title="导入成功",
                content=f"已成功导入 {imported_count} 个素材",
                orient=InfoBarPosition.TOP,
                parent=self
            )
    
    def _get_current_asset_category(self):
        """获取当前选中的素材类别"""
        if self.asset_type_button_bg.isChecked():
            return 'backgrounds'
        elif self.asset_type_button_char.isChecked():
            return 'characters'
        elif self.asset_type_button_sound.isChecked():
            return 'sounds'
        elif self.asset_type_button_music.isChecked():
            return 'music'
        return None
        
    def refresh_asset_list(self, category=None):
        """刷新素材列表显示"""
        # 清空列表
        self.asset_list.clear()
        
        # 如果未指定类别，使用当前选中的类别
        if category is None:
            category = self._get_current_asset_category()
            
        if not category:
            return
            
        # 获取素材列表
        assets = self.timeline.get_assets(category)
        
        # 如果没有素材，显示提示
        if not assets or len(assets) == 0:
            empty_item = QListWidgetItem("(此类别暂无素材，点击'添加素材'按钮导入)")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEnabled)  # 禁用项目
            empty_item.setTextAlignment(Qt.AlignCenter)  # 居中对齐
            self.asset_list.addItem(empty_item)
            return
            
        # 添加到列表
        for asset_id, asset_data in assets.items():
            item = QListWidgetItem(asset_id)
            if isinstance(asset_data, dict):
                # 设置工具提示
                tooltip = f"文件名: {asset_id}"
                if 'type' in asset_data:
                    tooltip += f"\n类型: {asset_data['type']}"
                if 'width' in asset_data and 'height' in asset_data:
                    tooltip += f"\n尺寸: {asset_data['width']}x{asset_data['height']}"
                if 'size' in asset_data:
                    tooltip += f"\n大小: {self._format_file_size(asset_data['size'])}"
                    
                item.setToolTip(tooltip)
                
                # 存储完整数据
                item.setData(Qt.UserRole, asset_data)
                
            self.asset_list.addItem(item)
        
        # 设置状态更新
        self.statusBar.showMessage(f"已加载 {len(assets)} 个{self.asset_category_label.text().split(':')[1].strip()}素材")
    
    def _format_file_size(self, size_in_bytes):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"
    
    def remove_asset(self):
        """删除选中的素材"""
        # 获取当前选中的素材
        current_item = self.asset_list.currentItem()
        if not current_item:
            MessageBox("提示", "请先选择要删除的素材", self).exec()
            return
            
        # 获取素材ID和类别
        asset_id = current_item.text()
        category = self._get_current_asset_category()
        
        if not category:
            MessageBox("错误", "无法确定素材类别", self).exec()
            return
            
        # 确认删除
        dialog = MessageBox(
            "确认删除",
            f"确定要删除素材 {asset_id} 吗？\n此操作将同时删除素材文件。",
            self
        )
        
        if not dialog.exec():
            return  # 用户取消删除
            
        # 获取素材数据
        asset_data = current_item.data(Qt.UserRole)
        
        try:
            # 删除文件(如果存在)
            if isinstance(asset_data, dict) and 'path' in asset_data:
                file_path = asset_data['path']
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"删除文件失败: {e}")
            
            # 从时间线中删除素材数据
            result = self.timeline.remove_asset(category, asset_id)
            
            if result:
                # 刷新列表
                self.refresh_asset_list(category)
                InfoBar.success(
                    title="删除成功",
                    content=f"素材 {asset_id} 已删除",
                    orient=InfoBarPosition.TOP,
                    parent=self
                )
            else:
                MessageBox("错误", f"删除素材 {asset_id} 失败", self).exec()
                
        except Exception as e:
            MessageBox("错误", f"删除素材时出错:\n{e}", self).exec()
    
    def create_renpy_project(self):
        """创建新的Ren'Py项目"""
        # 创建项目配置对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("创建Ren'Py项目")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # 项目名称
        layout.addWidget(QLabel("项目名称:"))
        project_name = QLineEdit()
        project_name.setPlaceholderText("例如: my_visual_novel")
        layout.addWidget(project_name)
        
        # 游戏标题
        layout.addWidget(QLabel("游戏标题:"))
        game_title = QLineEdit()
        game_title.setPlaceholderText("例如: 我的视觉小说")
        layout.addWidget(game_title)
        
        # 项目路径
        path_layout = QHBoxLayout()
        layout.addWidget(QLabel("项目位置:"))
        project_path = QLineEdit()
        project_path.setReadOnly(True)
        browse_button = PushButton("浏览...")
        
        def select_directory():
            dir_path = QFileDialog.getExistingDirectory(dialog, "选择项目目录")
            if dir_path:
                project_path.setText(dir_path)
        
        browse_button.clicked.connect(select_directory)
        path_layout.addWidget(project_path)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        
        # 分辨率选择
        layout.addWidget(QLabel("游戏分辨率:"))
        resolution_layout = QHBoxLayout()
        resolution_combo = QComboBox()
        resolution_combo.addItems(["1280x720", "1920x1080", "800x600"])
        resolution_layout.addWidget(resolution_combo)
        layout.addLayout(resolution_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        create_button = PushButton("创建项目")
        create_button.clicked.connect(dialog.accept)
        cancel_button = PushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(create_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # 获取输入值
            name = project_name.text().strip()
            title = game_title.text().strip()
            path = project_path.text().strip()
            resolution = resolution_combo.currentText()
            
            if not name or not path:
                MessageBox("错误", "项目名称和路径不能为空", self).exec()
                return
            
            try:
                # 创建项目目录结构
                project_dir = os.path.join(path, name)
                if not os.path.exists(project_dir):
                    os.makedirs(project_dir)
                
                # 创建子目录
                for subdir in ['game', 'game/images', 'game/gui', 'game/audio']:
                    os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)
                
                # 创建script.rpy文件
                width, height = resolution.split('x')
                script_content = f"""# Ren'Py自动生成的脚本文件
# 游戏: {title}
# 生成于: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

define config.screen_width = {width}
define config.screen_height = {height}

# 定义角色
define narrator = Character(None)

# 游戏开始
label start:
    # 初始场景
    scene bg black
    
    narrator "欢迎来到 {title}！"
    
    narrator "这是由Galgame剧情辅助制作工具生成的初始脚本。"
    
    narrator "您可以在此处添加更多剧情内容。"
    
    return
"""
                with open(os.path.join(project_dir, 'game', 'script.rpy'), 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                # 创建基本配置文件options.rpy
                options_content = f"""# Ren'Py自动生成的配置文件
# 游戏: {title}
# 生成于: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 基本配置

# 游戏名称
define config.name = "{title}"

# 游戏版本
define config.version = "1.0"

# 窗口图标
# define config.window_icon = "gui/window_icon.png"

## 尺寸和分辨率

# 窗口尺寸
define gui.init(int({width}), int({height}))
"""
                with open(os.path.join(project_dir, 'game', 'options.rpy'), 'w', encoding='utf-8') as f:
                    f.write(options_content)
                
                # 保存项目路径以供导入使用
                self.renpy_project_path = project_dir
                
                # 更新编辑器显示
                with open(os.path.join(project_dir, 'game', 'script.rpy'), 'r', encoding='utf-8') as f:
                    self.renpy_editor.setText(f.read())
                
                InfoBar.success(
                    title="成功",
                    content=f"Ren'Py项目已创建于 {project_dir}",
                    orient=InfoBarPosition.TOP,
                    parent=self
                )
                
            except Exception as e:
                MessageBox("错误", f"创建Ren'Py项目时出错: {e}", self).exec()
                return
    
    def import_to_renpy(self):
        """将当前剧情导入到Ren'Py项目"""
        if not hasattr(self, 'renpy_project_path') or not self.renpy_project_path:
            MessageBox("错误", "请先创建或打开一个Ren'Py项目", self).exec()
            return
        
        if not self.timeline.events:
            MessageBox("错误", "当前时间线为空，没有内容可导入", self).exec()
            return
        
        try:
            # 获取所有角色信息
            characters = self.timeline.characters
            
            # 获取时间线事件，包括分支信息
            timeline_data = self.timeline.get_timeline_data(include_branches=True)
            
            # 创建角色定义脚本
            characters_script = "# 自动生成的角色定义\n\n"
            characters_script += "define narrator = Character(None)\n"
            
            for char_id, char_info in characters.items():
                name = char_info.get('name', char_id)
                color = char_info.get('color', '#ffffff')
                characters_script += f"define {char_id} = Character(\"{name}\", color=\"{color}\")\n"
            
            # 创建素材定义脚本
            assets_script = "\n# 自动生成的素材定义\n\n"
            
            # 处理背景素材
            backgrounds = self.timeline.get_assets('backgrounds')
            for bg_id, bg_data in backgrounds.items():
                if isinstance(bg_data, dict) and 'path' in bg_data:
                    # 添加背景定义
                    asset_var_name = "bg_" + os.path.splitext(bg_id)[0].replace(' ', '_').lower()
                    assets_script += f"image bg {asset_var_name} = \"{os.path.join('images', 'bg', bg_id)}\"\n"
            
            # 处理角色素材
            char_assets = self.timeline.get_assets('characters')
            for char_id, char_data in char_assets.items():
                if isinstance(char_data, dict) and 'path' in char_data:
                    # 添加角色图像定义
                    asset_var_name = os.path.splitext(char_id)[0].replace(' ', '_').lower()
                    assets_script += f"image {asset_var_name} = \"{os.path.join('images', 'chara', char_id)}\"\n"
            
            # 处理音效素材
            sounds = self.timeline.get_assets('sounds')
            for sound_id, sound_data in sounds.items():
                if isinstance(sound_data, dict) and 'path' in sound_data:
                    # 添加音效定义注释
                    sound_var_name = os.path.splitext(sound_id)[0].replace(' ', '_').lower()
                    assets_script += f"# Sound effect: {sound_id} - 使用方法: play sound \"{os.path.join('audio', 'sfx', sound_id)}\"\n"
            
            # 处理音乐素材
            music = self.timeline.get_assets('music')
            for music_id, music_data in music.items():
                if isinstance(music_data, dict) and 'path' in music_data:
                    # 添加音乐定义注释
                    music_var_name = os.path.splitext(music_id)[0].replace(' ', '_').lower()
                    assets_script += f"# Music track: {music_id} - 使用方法: play music \"{os.path.join('audio', 'music', music_id)}\"\n"
            
            # 创建故事脚本
            story_script = "\n# 自动生成的故事脚本\n\n"
            story_script += "label start:\n"
            
            # 添加初始场景背景
            if backgrounds:
                first_bg = next(iter(backgrounds.items()))[0]
                bg_var_name = "bg_" + os.path.splitext(first_bg)[0].replace(' ', '_').lower()
                story_script += f"    scene bg {bg_var_name}\n\n"
            else:
                story_script += "    scene bg black\n\n"
            
            # 简单的故事转换逻辑 - 可以根据需要增强
            for event in timeline_data:
                event_type = event.get('event_type')
                data = event.get('data', {})
                
                if event_type == 'text_node':
                    text = data.get('text', '')
                    # 简单处理：将文本转为对话
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            if line.strip():
                                story_script += f"    narrator \"{line.strip()}\"\n"
                
                elif event_type == 'ollama_generation':
                    response = data.get('response', '')
                    if response:
                        lines = response.split('\n')
                        for line in lines:
                            if line.strip():
                                # 简单尝试识别对话
                                if ':' in line and line.split(':', 1)[0].strip() in characters:
                                    char, text = line.split(':', 1)
                                    char = char.strip()
                                    text = text.strip()
                                    story_script += f"    {char} \"{text}\"\n"
                                else:
                                    story_script += f"    narrator \"{line.strip()}\"\n"
                
                # 分支点处理
                if event.get('is_branch_point', False) and 'branch_details' in event:
                    story_script += "\n    # 分支选择\n"
                    story_script += "    menu:\n"
                    
                    for branch in event['branch_details']:
                        label_name = f"branch_{branch['target_id']}"
                        story_script += f"        \"{branch['text']}\":\n"
                        story_script += f"            jump {label_name}\n"
                    
                    # 添加分支标签
                    for branch in event['branch_details']:
                        label_name = f"branch_{branch['target_id']}"
                        story_script += f"\nlabel {label_name}:\n"
                        if 'content' in branch and isinstance(branch['content'], dict):
                            content = branch['content'].get('content', '')
                            if content:
                                lines = content.split('\n')
                                for line in lines:
                                    if line.strip():
                                        story_script += f"    narrator \"{line.strip()}\"\n"
                        story_script += "    jump continue_main\n"
                    
                    story_script += "\nlabel continue_main:\n"
            
            # 结束标记
            story_script += "\n    # 故事结束\n"
            story_script += "    return\n"
            
            # 写入文件
            script_path = os.path.join(self.renpy_project_path, 'game', 'script.rpy')
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(characters_script + assets_script + story_script)
            
            # 更新编辑器显示
            self.renpy_editor.setText(characters_script + assets_script + story_script)
            
            # 复制素材文件到Ren'Py项目
            self._copy_assets_to_renpy_project()
            
            InfoBar.success(
                title="成功",
                content=f"剧情及素材已成功导入到Ren'Py项目",
                orient=InfoBarPosition.TOP,
                parent=self
            )
            
        except Exception as e:
            MessageBox("错误", f"导入剧情时出错: {e}", self).exec()
            
    def _copy_assets_to_renpy_project(self):
        """将素材复制到Ren'Py项目目录"""
        if not hasattr(self, 'renpy_project_path') or not self.renpy_project_path:
            return
            
        try:
            # 创建必要的目录
            bg_dir = os.path.join(self.renpy_project_path, 'game', 'images', 'bg')
            os.makedirs(bg_dir, exist_ok=True)
            
            chara_dir = os.path.join(self.renpy_project_path, 'game', 'images', 'chara')
            os.makedirs(chara_dir, exist_ok=True)
            
            sfx_dir = os.path.join(self.renpy_project_path, 'game', 'audio', 'sfx')
            os.makedirs(sfx_dir, exist_ok=True)
            
            music_dir = os.path.join(self.renpy_project_path, 'game', 'audio', 'music')
            os.makedirs(music_dir, exist_ok=True)
            
            import shutil
            
            # 复制背景
            for bg_id, bg_data in self.timeline.get_assets('backgrounds').items():
                if isinstance(bg_data, dict) and 'path' in bg_data:
                    src = bg_data['path']
                    dst = os.path.join(bg_dir, bg_id)
                    if os.path.exists(src) and src != dst:
                        shutil.copy2(src, dst)
            
            # 复制角色图像
            for char_id, char_data in self.timeline.get_assets('characters').items():
                if isinstance(char_data, dict) and 'path' in char_data:
                    src = char_data['path']
                    dst = os.path.join(chara_dir, char_id)
                    if os.path.exists(src) and src != dst:
                        shutil.copy2(src, dst)
            
            # 复制音效
            for sound_id, sound_data in self.timeline.get_assets('sounds').items():
                if isinstance(sound_data, dict) and 'path' in sound_data:
                    src = sound_data['path']
                    dst = os.path.join(sfx_dir, sound_id)
                    if os.path.exists(src) and src != dst:
                        shutil.copy2(src, dst)
            
            # 复制音乐
            for music_id, music_data in self.timeline.get_assets('music').items():
                if isinstance(music_data, dict) and 'path' in music_data:
                    src = music_data['path']
                    dst = os.path.join(music_dir, music_id)
                    if os.path.exists(src) and src != dst:
                        shutil.copy2(src, dst)
                        
        except Exception as e:
            print(f"复制素材文件时出错: {e}")
    
    def update_renpy_preview(self):
        """更新Ren'Py预览"""
        if not hasattr(self, 'renpy_project_path') or not self.renpy_project_path:
            MessageBox("错误", "请先创建或打开一个Ren'Py项目", self).exec()
            return
        
        # 获取当前编辑区的代码
        code = self.renpy_editor.toPlainText()
        if not code:
            MessageBox("错误", "没有代码可以预览", self).exec()
            return
            
        try:
            # 保存代码到脚本文件
            script_path = os.path.join(self.renpy_project_path, 'game', 'script.rpy')
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(code)
                
            # 显示预览信息
            preview_message = BodyLabel(f"脚本已更新，可以运行Ren'Py查看效果")
            preview_message.setAlignment(Qt.AlignCenter)
            
            # 清除现有预览区域内容
            layout = self.preview_area.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            layout.addWidget(preview_message)
            
            InfoBar.success(
                title="更新成功",
                content="Ren'Py代码已更新，可以运行外部Ren'Py程序查看效果",
                orient=InfoBarPosition.TOP,
                parent=self
            )
            
        except Exception as e:
            MessageBox("错误", f"更新预览时出错: {e}", self).exec()
    
    def save_renpy_code(self):
        """保存Ren'Py代码"""
        if not hasattr(self, 'renpy_project_path') or not self.renpy_project_path:
            # 如果没有指定项目路径，使用另存为
            options = QFileDialog.Options()
            filePath, _ = QFileDialog.getSaveFileName(
                self, "保存Ren'Py脚本", "", 
                "Ren'Py脚本文件 (*.rpy);;所有文件 (*)", 
                options=options
            )
            
            if not filePath:
                return  # 用户取消
                
            if not filePath.lower().endswith('.rpy'):
                filePath += '.rpy'
        else:
            # 使用项目路径
            filePath = os.path.join(self.renpy_project_path, 'game', 'script.rpy')
            
        try:
            # 获取当前编辑区的代码
            code = self.renpy_editor.toPlainText()
            
            # 保存到文件
            with open(filePath, 'w', encoding='utf-8') as f:
                f.write(code)
                
            InfoBar.success(
                title="保存成功",
                content=f"Ren'Py代码已保存到 {filePath}",
                orient=InfoBarPosition.TOP,
                parent=self
            )
            
        except Exception as e:
            MessageBox("错误", f"保存代码时出错: {e}", self).exec()
    
    def run_preview(self):
        """运行Ren'Py预览"""
        if not hasattr(self, 'renpy_project_path') or not self.renpy_project_path:
            MessageBox("错误", "请先创建或打开一个Ren'Py项目", self).exec()
            return
            
        # 首先保存当前编辑器的代码
        self.save_renpy_code()
        
        # 检查是否设置了Ren'Py可执行文件路径
        renpy_executable = self._get_renpy_executable()
        if not renpy_executable:
            MessageBox(
                "错误", 
                "未找到Ren'Py可执行文件。请在设置中配置Ren'Py路径，或确保renpy.exe在PATH环境变量中。", 
                self
            ).exec()
            return
            
        try:
            # 准备运行命令
            import subprocess
            import platform
            
            # 根据操作系统执行不同的命令
            if platform.system() == "Windows":
                # Windows上直接使用subprocess调用
                process = subprocess.Popen(
                    [renpy_executable, self.renpy_project_path],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # 显示启动信息
                InfoBar.success(
                    title="启动成功",
                    content=f"Ren'Py预览已启动，项目路径: {self.renpy_project_path}",
                    orient=InfoBarPosition.TOP,
                    parent=self
                )
                
            else:
                # Linux/Mac
                cmd = f"{renpy_executable} \"{self.renpy_project_path}\""
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                InfoBar.success(
                    title="启动成功",
                    content=f"Ren'Py预览已启动，项目路径: {self.renpy_project_path}",
                    orient=InfoBarPosition.TOP,
                    parent=self
                )
                
        except Exception as e:
            MessageBox("错误", f"启动Ren'Py预览时出错: {e}", self).exec()
    
    def _get_renpy_executable(self):
        """获取Ren'Py可执行文件路径"""
        # 尝试从设置获取
        settings = QSettings("Galgame", "StoryAssistant")
        renpy_path = settings.value("renpy_path")
        
        if renpy_path and os.path.exists(renpy_path):
            return renpy_path
            
        # 尝试在标准位置查找
        import platform
        if platform.system() == "Windows":
            # Windows常见安装位置
            common_paths = [
                "C:\\Program Files\\RenPy\\renpy.exe",
                "C:\\Program Files (x86)\\RenPy\\renpy.exe",
                os.path.join(os.environ.get("APPDATA", ""), "RenPy", "renpy.exe")
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
                    
            # 检查PATH环境变量
            import shutil
            return shutil.which("renpy.exe")
        else:
            # Linux/Mac常见安装位置
            common_paths = [
                "/usr/bin/renpy",
                "/usr/local/bin/renpy",
                os.path.expanduser("~/renpy/renpy.sh")
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
                    
            # 检查PATH环境变量
            import shutil
            return shutil.which("renpy")

    def _connect_signals(self):
        """Connects UI element signals to methods."""
        # Connect menu actions (already done in _init_ui)
        # Connect buttons
        self.generate_button.clicked.connect(self.generate_story)
        self.analyze_emotion_button.clicked.connect(self.analyze_selected_emotion)
        self.undo_button.clicked.connect(self.undo_last_ollama)
        self.manage_characters_button.clicked.connect(self.open_character_manager)

        # Connect timeline widget signals
        # 注意: timeline_widget.nodeSelected已直接在创建时连接到display_node_content

        # Connect editor area signals for emotion analysis
        self.editor_area.selectionChanged.connect(self.update_emotion_button_state)
        
        # 连接素材库按钮点击事件
        self.asset_type_button_bg.clicked.connect(lambda: self._on_asset_type_clicked('backgrounds'))
        self.asset_type_button_char.clicked.connect(lambda: self._on_asset_type_clicked('characters'))
        self.asset_type_button_sound.clicked.connect(lambda: self._on_asset_type_clicked('sounds'))
        self.asset_type_button_music.clicked.connect(lambda: self._on_asset_type_clicked('music'))
        
        # 连接素材列表双击事件
        self.asset_list.itemDoubleClicked.connect(self._preview_asset)

    def _on_asset_type_clicked(self, category):
        """素材类别按钮点击处理"""
        # 取消选中其他按钮
        self.asset_type_button_bg.setChecked(category == 'backgrounds')
        self.asset_type_button_char.setChecked(category == 'characters')
        self.asset_type_button_sound.setChecked(category == 'sounds')
        self.asset_type_button_music.setChecked(category == 'music')
        
        # 更新类别标签
        category_display_names = {
            'backgrounds': '背景',
            'characters': '角色',
            'sounds': '音效',
            'music': '音乐'
        }
        display_name = category_display_names.get(category, '未知')
        self.asset_category_label.setText(f"当前类别: {display_name}")
        
        # 刷新素材列表
        self.refresh_asset_list(category)

    # --- Slots for Ollama Worker ---
    @pyqtSlot(str, dict)
    def _handle_ollama_result(self, request_id, result):
        """Handles the successful result from the Ollama worker."""
        story_text = result.get('story_text', '')
        suggestions = result.get('suggestions', [])
        output_display = f"生成成功 (ID: {request_id}):\n{story_text}\n\n建议:\n- {'\n- '.join(suggestions)}"
        self.ollama_output_area.setText(output_display)

        # Add to timeline (attach to selected node or head)
        parent_node_id = self.get_selected_timeline_node_id() or self.timeline.head_event_id
        prompt_used = self.ollama_prompt_input.toPlainText().strip() # Get prompt used for this generation

        new_event_id = self.timeline.add_event(
            event_type='ollama_generation',
            data={'prompt': prompt_used, 'response': story_text, 'suggestions': suggestions},
            parent_event_id=parent_node_id,
            ollama_request_id=request_id
        )
        self.timeline.dirty = True # Mark changes
        self.refresh_timeline_view()
        self.select_timeline_node(new_event_id) # Select the new node
        self.statusBar.showMessage("剧情已生成并添加到时间线")
        self.undo_button.setEnabled(True) # Enable undo after successful generation
        self.ollama_prompt_input.clear() # Clear prompt after use

    @pyqtSlot(str, str)
    def _handle_ollama_error(self, request_id, error_message):
        """Handles errors reported by the Ollama worker."""
        self.ollama_output_area.setText(f"错误 (ID: {request_id}):\n{error_message}")
        MessageBox("错误", f"Ollama 操作失败: {error_message}", self).exec()
        self.statusBar.showMessage(f"Ollama 操作失败 (ID: {request_id})")

    @pyqtSlot()
    def _ollama_finished(self):
        """Cleans up and re-enables UI after Ollama thread finishes."""
        self.generate_button.setEnabled(True)
        self.ollama_prompt_input.setEnabled(True)
        # Re-enable other controls if needed
        self.timeline_widget.setEnabled(True)
        self.manage_characters_button.setEnabled(True)
        self.worldview_info_area.setEnabled(True)
        self.menuBar().setEnabled(True) # Re-enable menu bar

        if self.ollama_thread:
            self.ollama_thread.quit()
            self.ollama_thread.wait()
        self.ollama_thread = None
        self.ollama_worker = None
        print("Ollama thread finished and cleaned up.")
        QApplication.processEvents() # Process any pending events

    # --- Core Functionality Methods ---

    def _init_ollama_client(self, force_reinit=False):
        """Initializes or re-initializes the Ollama client."""
        if self.ollama_client is None or force_reinit:
            try:
                # Pass the config path to the client
                self.ollama_client = OllamaClient(config_path=self.config_path)
                self.statusBar.showMessage(f"Ollama 客户端已连接 (模型: {self.ollama_client.model})")
                print(f"Ollama client initialized/reinitialized with config: {self.config_path}")
                return True
            except ConnectionError as ce:
                MessageBox("连接错误", f"无法连接到 Ollama 服务: {ce}\n请检查配置文件 ({self.config_path}) 中的主机地址以及 Ollama 服务是否正在运行。", 
                        self).exec()
                self.statusBar.showMessage("Ollama 连接失败")
                self.ollama_client = None # Ensure client is None on failure
                return False
            except Exception as e:
                MessageBox("初始化错误", f"初始化 Ollama 客户端时出错: {e}", 
                        self).exec()
                self.statusBar.showMessage("Ollama 初始化失败")
                self.ollama_client = None # Ensure client is None on failure
                return False
        return True # Already initialized

    def new_project(self):
        # Check for unsaved changes before proceeding
        if self._check_unsaved_changes():
            self.timeline = StoryTimeline()
            self.current_project_path = None
            self.editor_area.clear()
            self.ollama_prompt_input.clear()
            self.ollama_output_area.clear()
            # 重置时间线组件
            self.refresh_timeline_view()
            # Clear worldview info area (character info handled by timeline now)
            # self.character_info_area.clear() # Removed
            self.worldview_info_area.clear()
            self.setWindowTitle("VNova Assistant - 视觉小说制作助手 - 新建项目")
            self.statusBar.showMessage("新项目已创建")

    def open_settings_dialog(self):
        """Opens the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec(): # exec() returns true if accepted (Save clicked)
            # 获取更新后的设置
            settings = dialog.settings
            
            # 应用Ollama设置
            print("Settings saved, re-initializing Ollama client...")
            self._init_ollama_client(force_reinit=True)
            
            # 应用Ren'Py相关设置
            # 可以在创建Ren'Py项目时使用，所以不需要马上应用
            
            # 应用时间轴设置，刷新时间线视图
            self.refresh_timeline_view()
            
            # 更新自动保存设置
            self._setup_autosave()
            
            # 更新状态栏
            self.statusBar.showMessage("设置已更新")
            
            # 如果有素材库路径设置，刷新素材库显示
            if settings.get("assets_path") and os.path.exists(settings.get("assets_path")):
                # 重新加载素材库
                self.refresh_asset_list()
        else:
            print("Settings dialog cancelled.")

    def open_project(self):
        if not self._check_unsaved_changes():
            return

        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "打开时间线文件", "",
                                                  "JSON Files (*.json);;All Files (*)", options=options)
        if fileName:
            try:
                self.timeline.load_timeline(fileName)
                self.current_project_path = fileName
                self.refresh_timeline_view()
                # Select the head event after loading
                if self.timeline.head_event_id:
                    self.select_timeline_node(self.timeline.head_event_id)
                else:
                    self.editor_area.clear()
                self.setWindowTitle(f"VNova Assistant - 视觉小说制作助手 - {fileName}")
                self.statusBar.showMessage(f"项目已从 {fileName} 加载")
            except Exception as e:
                MessageBox("打开失败", f"无法加载文件 {fileName}:\n{e}", self).exec()
                self.statusBar.showMessage("项目加载失败")

    def save_project(self):
        if self.current_project_path:
            try:
                self.timeline.save_timeline(self.current_project_path)
                self.statusBar.showMessage(f"项目已保存到 {self.current_project_path}")
                self.timeline.dirty = False # Mark as saved
            except Exception as e:
                MessageBox("保存失败", f"无法保存文件 {self.current_project_path}:\n{e}", self).exec()
                self.statusBar.showMessage("项目保存失败")
        else:
            self.save_project_as()

    def save_project_as(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "保存时间线文件", self.current_project_path or "untitled.json",
                                                  "JSON Files (*.json);;All Files (*)", options=options)
        if fileName:
            # Ensure .json extension if not present
            if not fileName.lower().endswith('.json'):
                fileName += '.json'
            try:
                self.timeline.save_timeline(fileName)
                self.current_project_path = fileName
                self.setWindowTitle(f"VNova Assistant - 视觉小说制作助手 - {fileName}")
                self.statusBar.showMessage(f"项目已保存到 {fileName}")
                self.timeline.dirty = False # Mark as saved
            except Exception as e:
                MessageBox("保存失败", f"无法保存文件 {fileName}:\n{e}", self).exec()
                self.statusBar.showMessage("项目另存为失败")

    def generate_story(self):
        if not self._init_ollama_client(): # Ensure client is ready
            return

        prompt = self.ollama_prompt_input.toPlainText().strip()
        if not prompt:
            MessageBox("警告", "请输入生成提示！", self).exec()
            return

        # --- Get context --- 
        # --- Get context --- 
        # Pass all character profiles for now. Ollama client might need adjustment.
        # TODO: Add UI to select specific characters for context
        char_info = self.timeline.characters if hasattr(self.timeline, 'characters') else None
        world_info_text = self.worldview_info_area.toPlainText().strip()
        world_info = {"worldview_setting": world_info_text} if world_info_text else None

        self.statusBar.showMessage("正在调用 Ollama 生成剧情...")
        # Disable UI elements during generation
        self.generate_button.setEnabled(False)
        self.ollama_prompt_input.setEnabled(False)
        self.timeline_widget.setEnabled(False) # Prevent timeline changes during generation
        self.manage_characters_button.setEnabled(False)
        self.worldview_info_area.setEnabled(False)
        self.menuBar().setEnabled(False) # Disable menu bar to prevent file operations etc.

        QApplication.processEvents() # Keep UI responsive

        # --- Setup and run worker thread --- 
        self.ollama_thread = QThread()
        self.ollama_worker = OllamaWorker(self.ollama_client, prompt, char_info, world_info)
        self.ollama_worker.moveToThread(self.ollama_thread)

        # Connect signals and slots
        self.ollama_thread.started.connect(self.ollama_worker.run)
        self.ollama_worker.finished.connect(self._handle_ollama_result)
        self.ollama_worker.error.connect(self._handle_ollama_error)
        # Connect finished signal for cleanup
        self.ollama_worker.finished.connect(self._ollama_finished)
        self.ollama_worker.error.connect(self._ollama_finished) # Also cleanup on error
        # self.ollama_thread.finished.connect(self.ollama_thread.deleteLater) # Let _ollama_finished handle thread cleanup
        # self.ollama_thread.finished.connect(self.ollama_worker.deleteLater)

        self.ollama_thread.start()

    def analyze_selected_emotion(self):
        if SnowNLP is None:
            MessageBox("警告", "snownlp 库未安装或加载失败，无法进行情绪分析。\n请运行 'pip install snownlp' 并重启应用。", 
                    self).exec()
            self.emotion_display.setText("情绪: (不可用)")
            return

        selected_text = self.editor_area.textCursor().selectedText().strip()
        if not selected_text:
            self.emotion_display.setText("情绪: (未选中文本)")
            return

        sentiment_score = self.emotion_analyzer.analyze_emotion(selected_text)
        if sentiment_score is not None:
            # Simple display, could be more nuanced
            emotion_label = "积极" if sentiment_score > 0.6 else ("消极" if sentiment_score < 0.4 else "中性")
            self.emotion_display.setText(f"情绪: {emotion_label} ({sentiment_score:.3f})")
            # Optionally, store this on the event if needed
            # current_id = self.get_selected_timeline_node_id()
            # if current_id and current_id in self.timeline.events:
            #     self.timeline.events[current_id].emotion = sentiment_score # Or store the label
        else:
            self.emotion_display.setText("情绪: 分析失败")

    def open_character_manager(self):
        """Opens the character management dialog."""
        try:
            from .character_manager_dialog import CharacterManagerDialog # Lazy import
            # Create a new dialog instance each time:
            dialog = CharacterManagerDialog(self.timeline, self)
            dialog.exec() # Show the dialog modally
            print("Character Manager Dialog closed.")
            # Changes are saved directly to self.timeline.characters by the dialog
        except ImportError as e:
            MessageBox("错误", f"无法加载角色管理器: {e}", self).exec()
        except Exception as e:
            MessageBox("错误", f"打开角色管理器时出错: {e}", self).exec()

    def undo_last_ollama(self):
        # Find the most recent ollama_generation event linked to the head path
        last_ollama_event = None
        current_id = self.timeline.head_event_id
        path_ids = set()
        while current_id:
            event = self.timeline.get_event(current_id)
            if not event: break
            path_ids.add(current_id)
            if event.event_type == 'ollama_generation' and event.ollama_request_id:
                last_ollama_event = event
                break # Found the most recent one on the main path
            current_id = event.parent_event_id

        if last_ollama_event and last_ollama_event.ollama_request_id:
            request_id_to_undo = last_ollama_event.ollama_request_id
            dialog = MessageBox(
                "确认撤销",
                                         f"确定要撤销与 Ollama 请求 ID 相关的所有事件吗？\nID: {request_id_to_undo}",
                self
            )
            
            if dialog.exec():  # 返回True表示确认，False表示取消
                success = self.timeline.undo_ollama_generation(request_id_to_undo)
                if success:
                    self.timeline.dirty = True
                    self.refresh_timeline_view()
                    # Select the new head node after undo
                    if self.timeline.head_event_id:
                        self.select_timeline_node(self.timeline.head_event_id)
                    else:
                        self.editor_area.clear()
                    self.statusBar.showMessage(f"Ollama 生成 (ID: {request_id_to_undo}) 已撤销")
                    # Disable undo if no more ollama events are obvious candidates
                    # (This logic might need refinement for complex branches)
                    self.undo_button.setEnabled(False) # Simple disabling for now
                else:
                    MessageBox("撤销失败", f"未能找到或撤销与 ID {request_id_to_undo} 相关的事件。", self).exec()
                    self.statusBar.showMessage("撤销操作失败")
        else:
            MessageBox("无法撤销", "在当前主时间线上未找到可撤销的 Ollama 生成事件。", self).exec()
            self.undo_button.setEnabled(False)

    def refresh_timeline_view(self):
        """刷新时间线视图"""
        print("Action: Refresh Timeline View")
        
        # 设置时间线数据
        self.timeline_widget.set_story_timeline(self.timeline)
        
        # 如果时间线为空，自动创建一个根节点
        if not self.timeline.events and not self.timeline.head_event_id:
            root_id = self.timeline.add_event('text_node', {'text': '故事起点'}, parent_event_id=None)
            self.timeline.dirty = False # 初始节点不应标记为已修改
        
        # 更新撤销按钮状态
        self.update_undo_button_state()
        
        # 如果有头节点，选中它
        if self.timeline.head_event_id:
            self.timeline_widget.select_node(self.timeline.head_event_id)

    def update_undo_button_state(self):
        """更新撤销按钮的启用状态"""
        # 检查头路径上是否有ollama事件
        has_ollama_on_path = False
        current_id = self.timeline.head_event_id
        while current_id:
            event = self.timeline.get_event(current_id)
            if event and event.event_type == 'ollama_generation':
                has_ollama_on_path = True
                break
            current_id = event.parent_event_id if event else None
        self.undo_button.setEnabled(has_ollama_on_path)

    def display_node_content(self, event_id):
        """显示节点内容"""
        if not event_id:
            self.editor_area.clear()
            self.editor_area.setPlaceholderText("请在左侧选择一个时间线节点以查看内容...")
            return

        print(f"Action: Display Node Content for ID: {event_id}")
        event = self.timeline.get_event(event_id)
        if event:
            # Format data nicely for the editor
            display_text = f"节点 ID: {event.event_id}\n"
            display_text += f"类型: {event.event_type}\n"
            display_text += f"时间戳: {event.timestamp.isoformat()}\n"
            if event.parent_event_id:
                display_text += f"父节点 ID: {event.parent_event_id}\n"
            if event.child_event_ids:
                display_text += f"子节点 ID(s): {', '.join(event.child_event_ids)}\n"
            if event.ollama_request_id:
                display_text += f"Ollama请求 ID: {event.ollama_request_id}\n"
            if event.emotion is not None:
                display_text += f"情绪得分 (上次分析): {event.emotion:.3f}\n"
            if event.is_branch_point:
                display_text += f"分支节点: 是 (有{len(event.branch_choices)}个选项)\n"

            display_text += f"\n--- 节点数据 ---\n"
            try:
                # Pretty print JSON data
                display_text += json.dumps(event.data, indent=2, ensure_ascii=False)
            except TypeError:
                display_text += str(event.data) # Fallback for non-serializable data

            self.editor_area.setText(display_text)
        else:
            self.editor_area.setText(f"错误：在时间线中找不到节点 {event_id}")
            MessageBox("错误", f"无法加载节点 {event_id} 的数据。时间线可能已损坏。", self).exec()

    def get_selected_timeline_node_id(self):
        """获取当前选中的时间线节点ID"""
        # 委托给timeline_widget处理
        return self.timeline_widget.selected_node_id

    def select_timeline_node(self, event_id):
        """选择指定ID的时间线节点"""
        if event_id:
            self.timeline_widget.select_node(event_id)

    def update_emotion_button_state(self):
        has_selection = self.editor_area.textCursor().hasSelection()
        # Also check if SnowNLP is available
        self.analyze_emotion_button.setEnabled(has_selection and (SnowNLP is not None))

    def _check_unsaved_changes(self):
        """Checks for unsaved changes and prompts the user if necessary. Returns True if safe to proceed."""
        if hasattr(self.timeline, 'dirty') and self.timeline.dirty:
            dialog = MessageBox(
                "未保存的更改",
                "当前项目有未保存的更改。您想先保存吗？\n[确定]保存 [取消]不保存",
                self
            )
            
            if dialog.exec():  # 用户点击确定，保存更改
                self.save_project()
                # Check if save was successful (e.g., user didn't cancel save_as)
                return not self.timeline.dirty
            else:  # 用户点击取消，不保存
                return True
        return True # No unsaved changes

    def closeEvent(self, event):
        print("Action: Close Event Triggered")
        if self._check_unsaved_changes():
            event.accept() # Proceed with closing
        else:
            event.ignore() # Abort closing

    def build_renpy_project(self):
        """构建Ren'Py项目"""
        if not hasattr(self, 'renpy_project_path') or not self.renpy_project_path:
            MessageBox("错误", "请先创建或打开一个Ren'Py项目", self).exec()
            return
            
        # 首先保存当前编辑器的代码
        self.save_renpy_code()
        
        # 检查是否设置了Ren'Py可执行文件路径
        renpy_executable = self._get_renpy_executable()
        if not renpy_executable:
            MessageBox(
                "错误", 
                "未找到Ren'Py可执行文件。请在设置中配置Ren'Py路径，或确保renpy.exe在PATH环境变量中。", 
                self
            ).exec()
            return
            
        try:
            # 准备构建命令
            import subprocess
            import platform
            
            build_message = MessageBox(
                "构建中", 
                "正在构建项目，这可能需要一些时间...", 
                self
            )
            build_message.show()
            QApplication.processEvents()  # 确保对话框显示
            
            # 根据操作系统执行不同的命令
            if platform.system() == "Windows":
                # Windows上运行构建命令
                process = subprocess.Popen(
                    [renpy_executable, self.renpy_project_path, "build"],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac
                cmd = f"{renpy_executable} \"{self.renpy_project_path}\" build"
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
            # 等待构建完成
            stdout, stderr = process.communicate()
            
            build_message.close()
            
            if process.returncode == 0:
                InfoBar.success(
                    title="构建成功",
                    content=f"Ren'Py项目已构建完成，输出目录位于项目的build目录中",
                    orient=InfoBarPosition.TOP,
                    parent=self
                )
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')
                MessageBox("构建失败", f"Ren'Py项目构建失败:\n{error_msg}", self).exec()
                
        except Exception as e:
            MessageBox("错误", f"构建Ren'Py项目时出错: {e}", self).exec()
    
    def export_renpy_project(self):
        """导出Ren'Py项目"""
        if not hasattr(self, 'renpy_project_path') or not self.renpy_project_path:
            MessageBox("错误", "请先创建或打开一个Ren'Py项目", self).exec()
            return
            
        # 首先保存当前编辑器的代码
        self.save_renpy_code()
        
        try:
            # 选择导出目标目录
            options = QFileDialog.Options()
            export_dir = QFileDialog.getExistingDirectory(
                self, "选择导出目录", "", options=options
            )
            
            if not export_dir:
                return  # 用户取消
                
            # 准备导出
            import shutil
            import platform
            
            # 创建导出目录
            project_name = os.path.basename(self.renpy_project_path)
            export_path = os.path.join(export_dir, f"{project_name}_export")
            os.makedirs(export_path, exist_ok=True)
            
            # 复制项目文件
            shutil.copytree(
                os.path.join(self.renpy_project_path, 'game'), 
                os.path.join(export_path, 'game'),
                dirs_exist_ok=True
            )
            
            # 复制必要的配置文件
            for file in ['options.rpy', 'launcher']:
                src = os.path.join(self.renpy_project_path, file)
                dst = os.path.join(export_path, file)
                if os.path.exists(src):
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
            
            InfoBar.success(
                title="导出成功",
                content=f"Ren'Py项目已导出到 {export_path}",
                orient=InfoBarPosition.TOP,
                parent=self
            )
            
        except Exception as e:
            MessageBox("错误", f"导出Ren'Py项目时出错: {e}", self).exec()

    def _preview_asset(self, item):
        """处理素材列表双击事件"""
        asset_id = item.text()
        category = self._get_current_asset_category()
        
        if not category:
            MessageBox("错误", "无法确定素材类别", self).exec()
            return
            
        asset_data = item.data(Qt.UserRole)
        
        if isinstance(asset_data, dict) and 'path' in asset_data:
            file_path = asset_data['path']
            if os.path.exists(file_path):
                try:
                    # 打开文件
                    import subprocess
                    import platform
                    
                    if platform.system() == "Windows":
                        subprocess.Popen(['start', file_path], shell=True)
                    else:
                        subprocess.Popen(['open', file_path])
                except Exception as e:
                    MessageBox("错误", f"无法打开文件: {e}", self).exec()
            else:
                MessageBox("错误", f"文件 {file_path} 不存在", self).exec()
        else:
            MessageBox("错误", "无法获取有效的文件路径", self).exec()

    def _setup_autosave(self):
        """设置自动保存功能"""
        try:
            # 加载配置
            settings = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            # 检查是否启用自动保存
            autosave_enabled = settings.get("autosave_enabled", True)
            if autosave_enabled:
                # 获取自动保存间隔（分钟）
                autosave_interval = int(settings.get("autosave_interval", "5"))
                # 转换为毫秒
                interval_ms = autosave_interval * 60 * 1000
                
                # 设置并启动计时器
                self.autosave_timer.setInterval(interval_ms)
                self.autosave_timer.start()
                print(f"自动保存已启用，间隔: {autosave_interval} 分钟")
            else:
                # 停止计时器
                self.autosave_timer.stop()
                print("自动保存已禁用")
        except Exception as e:
            print(f"设置自动保存时出错: {e}")
            # 禁用自动保存以防出错
            self.autosave_timer.stop()

    def auto_save_project(self):
        """自动保存项目"""
        if not self.current_project_path or not hasattr(self.timeline, 'dirty') or not self.timeline.dirty:
            return  # 没有需要保存的内容或没有设置保存路径
        
        try:
            # 创建自动保存目录
            autosave_dir = os.path.join(os.path.dirname(self.current_project_path), "autosave")
            os.makedirs(autosave_dir, exist_ok=True)
            
            # 创建带时间戳的文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(self.current_project_path)
            base_name, ext = os.path.splitext(filename)
            autosave_path = os.path.join(autosave_dir, f"{base_name}_autosave_{timestamp}{ext}")
            
            # 保存项目
            self.timeline.save_timeline(autosave_path)
            
            # 同时保存到主项目文件
            self.timeline.save_timeline(self.current_project_path)
            self.timeline.dirty = False
            
            self.statusBar.showMessage(f"已自动保存项目到 {self.current_project_path} 和 {autosave_path}")
            print(f"自动保存完成: {autosave_path}")
        except Exception as e:
            print(f"自动保存时出错: {e}")
            self.statusBar.showMessage(f"自动保存失败: {e}")

# Application Entry Point (usually in a separate main.py)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # You might want to load stylesheets here for styling
    # app.setStyleSheet(""" QMainWindow {...} """)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())