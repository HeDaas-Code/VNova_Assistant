from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QScrollArea, QFrame,
                             QMenu, QSplitter, QDialog, QLineEdit, 
                             QTextEdit, QListWidget, QComboBox, QSizePolicy,
                             QGridLayout, QToolButton, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QFont, QIcon

import json
import os
from datetime import datetime

# 导入配置文件相关
# VNova Assistant - 视觉小说制作助手
CONFIG_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.json'))

class NodeWidget(QFrame):
    """表示故事中的节点，可以是文本节点、分支点等"""
    
    clicked = pyqtSignal(str)  # 发送节点ID
    branchRequested = pyqtSignal(str)  # 请求创建分支
    editRequested = pyqtSignal(str)  # 请求编辑节点
    
    def __init__(self, event_id, data, is_branch=False, parent=None, node_color="蓝色"):
        super().__init__(parent)
        self.event_id = event_id
        self.data = data
        self.is_branch = is_branch
        self.is_selected = False
        self.node_color = node_color  # 新增节点颜色配置
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setMinimumHeight(80)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        # 节点类型标签
        if self.is_branch:
            type_label = QLabel("🔀 分支点")
            # 根据配置选择颜色
            if self.node_color == "蓝色":
                self.setStyleSheet("background-color: #FFF4E0; border: 1px solid #FFD8A9;")
            elif self.node_color == "绿色":
                self.setStyleSheet("background-color: #E8F5E9; border: 1px solid #81C784;")
            elif self.node_color == "紫色":
                self.setStyleSheet("background-color: #F3E5F5; border: 1px solid #CE93D8;")
            elif self.node_color == "红色":
                self.setStyleSheet("background-color: #FFEBEE; border: 1px solid #EF9A9A;")
            else:
                # 默认蓝色
                self.setStyleSheet("background-color: #FFF4E0; border: 1px solid #FFD8A9;")
        else:
            type_label = QLabel("📝 文本节点")
            self.setStyleSheet("background-color: #F1F7E7; border: 1px solid #A2C579;")
        
        title_layout.addWidget(type_label)
        title_layout.addStretch()
        
        # 操作按钮
        edit_btn = QToolButton()
        edit_btn.setText("✏️")
        edit_btn.setToolTip("编辑节点")
        edit_btn.clicked.connect(lambda: self.editRequested.emit(self.event_id))
        
        branch_btn = QToolButton()
        branch_btn.setText("🔀")
        branch_btn.setToolTip("添加分支")
        branch_btn.clicked.connect(lambda: self.branchRequested.emit(self.event_id))
        
        title_layout.addWidget(edit_btn)
        title_layout.addWidget(branch_btn)
        
        layout.addLayout(title_layout)
        
        # 内容区域
        content_text = ""
        if isinstance(self.data, dict):
            content_text = self.data.get('text', str(self.data))
        else:
            content_text = str(self.data)
            
        # 限制显示的文本长度
        if len(content_text) > 100:
            content_text = content_text[:97] + "..."
            
        content = QLabel(content_text)
        content.setWordWrap(True)
        content.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(content)
        
        # 如果是分支点，显示分支选项
        if self.is_branch and isinstance(self.data, dict) and 'branch_details' in self.data:
            branches_label = QLabel("分支选项:")
            layout.addWidget(branches_label)
            
            for branch in self.data['branch_details']:
                option_text = branch.get('text', 'Unknown option')
                branch_label = QLabel(f"• {option_text}")
                layout.addWidget(branch_label)
        
    def mousePressEvent(self, event):
        self.clicked.emit(self.event_id)
        super().mousePressEvent(event)
    
    def setSelected(self, selected):
        self.is_selected = selected
        if selected:
            self.setStyleSheet(self.styleSheet() + "border-width: 2px;")
        else:
            # 恢复默认样式
            if self.is_branch:
                # 根据配置选择颜色
                if self.node_color == "蓝色":
                    self.setStyleSheet("background-color: #FFF4E0; border: 1px solid #FFD8A9;")
                elif self.node_color == "绿色":
                    self.setStyleSheet("background-color: #E8F5E9; border: 1px solid #81C784;")
                elif self.node_color == "紫色":
                    self.setStyleSheet("background-color: #F3E5F5; border: 1px solid #CE93D8;")
                elif self.node_color == "红色":
                    self.setStyleSheet("background-color: #FFEBEE; border: 1px solid #EF9A9A;")
                else:
                    # 默认蓝色
                    self.setStyleSheet("background-color: #FFF4E0; border: 1px solid #FFD8A9;")
            else:
                self.setStyleSheet("background-color: #F1F7E7; border: 1px solid #A2C579;")
        self.update()

class BranchDialog(QDialog):
    """创建分支选项的对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建分支选项")
        self.setMinimumWidth(400)
        self.choices = []
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 说明标签
        layout.addWidget(QLabel("请添加分支选项:"))
        
        # 选项列表
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # 添加选项区域
        add_layout = QHBoxLayout()
        self.option_text = QLineEdit()
        self.option_text.setPlaceholderText("选项文本...")
        add_layout.addWidget(self.option_text)
        
        add_btn = QPushButton("添加选项")
        add_btn.clicked.connect(self.add_choice)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        # 选项内容编辑区
        layout.addWidget(QLabel("选项内容:"))
        self.content_edit = QTextEdit()
        layout.addWidget(self.content_edit)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def add_choice(self):
        text = self.option_text.text().strip()
        content = self.content_edit.toPlainText().strip()
        
        if not text:
            QMessageBox.warning(self, "输入错误", "请输入选项文本")
            return
            
        # 添加到列表和数据
        self.choices.append({
            "text": text,
            "data": {"content": content}
        })
        
        self.list_widget.addItem(text)
        self.option_text.clear()
        self.content_edit.clear()
        
    def get_choices(self):
        return self.choices

class StoryTimelineWidget(QWidget):
    """故事时间线可视化组件"""
    
    nodeSelected = pyqtSignal(str)  # 节点被选中时发出信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.story_timeline = None  # StoryTimeline实例
        self.nodes = {}  # 节点字典，键为event_id
        self.selected_node_id = None  # 当前选中的节点ID
        
        # 加载配置
        self.settings = self._load_settings()
        
        self.initUI()
        
    def _load_settings(self):
        """从配置文件加载设置"""
        default_settings = {
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
                    # 确保关键设置存在
                    for key, value in default_settings.items():
                        if key not in loaded_settings:
                            loaded_settings[key] = value
                    return loaded_settings
            except Exception as e:
                print(f"加载配置文件时出错: {e}")
        
        return default_settings
    
    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # 工具栏
        tools_layout = QHBoxLayout()
        
        self.add_node_btn = QPushButton("添加节点")
        self.add_node_btn.clicked.connect(self.add_new_node)
        tools_layout.addWidget(self.add_node_btn)
        
        self.add_branch_btn = QPushButton("创建分支")
        self.add_branch_btn.clicked.connect(self.create_branch)
        self.add_branch_btn.setEnabled(False)  # 初始禁用
        tools_layout.addWidget(self.add_branch_btn)
        
        tools_layout.addStretch()
        
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["线性视图", "图形视图"])
        # 设置默认视图模式
        self.view_mode_combo.setCurrentText(self.settings.get("default_view_mode", "线性视图"))
        self.view_mode_combo.currentTextChanged.connect(self.change_view_mode)
        tools_layout.addWidget(QLabel("显示方式:"))
        tools_layout.addWidget(self.view_mode_combo)
        
        main_layout.addLayout(tools_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 线性视图（默认）
        self.linear_container = QWidget()
        self.linear_layout = QVBoxLayout(self.linear_container)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.linear_container)
        
        # 图形视图（节点网络图）
        self.graph_view = QWidget()
        self.graph_view.setMinimumHeight(200)
        self.graph_view.paintEvent = self.paint_graph
        
        # 添加两种视图到分割器
        splitter.addWidget(self.scroll_area)
        splitter.addWidget(self.graph_view)
        
        # 应用默认视图模式
        if self.settings.get("default_view_mode") == "图形视图":
            splitter.setSizes([200, 600])  # 图形视图占主要空间
        else:
            splitter.setSizes([600, 200])  # 线性视图占主要空间
        
        main_layout.addWidget(splitter)
        
        # 应用设置
        self.change_view_mode(self.settings.get("default_view_mode", "线性视图"))
    
    def set_story_timeline(self, timeline):
        """设置要显示的故事时间线"""
        self.story_timeline = timeline
        self.refresh_timeline()
    
    def refresh_timeline(self):
        """刷新时间线显示"""
        if not self.story_timeline:
            return
            
        # 清除现有节点
        self.clear_nodes()
            
        # 获取时间线数据，包括分支信息
        timeline_data = self.story_timeline.get_timeline_data(include_branches=True)
        
        # 应用节点间距设置
        spacing = 5  # 默认间距
        if self.settings.get("node_spacing") == "紧凑":
            spacing = 2
        elif self.settings.get("node_spacing") == "宽松":
            spacing = 10
        
        # 设置布局间距
        self.linear_layout.setSpacing(spacing)
        
        # 在线性布局中添加节点
        for event_data in timeline_data:
            event_id = event_data.get('event_id')
            is_branch = event_data.get('is_branch_point', False)
            
            # 应用节点颜色设置
            node_color = self.settings.get("branch_node_color", "蓝色")
            
            node = NodeWidget(event_id, event_data, is_branch, node_color=node_color)
            node.clicked.connect(self.select_node)
            node.branchRequested.connect(self.create_branch)
            node.editRequested.connect(self.edit_node)
            
            self.linear_layout.addWidget(node)
            self.nodes[event_id] = node
            
        # 更新图形视图
        self.graph_view.update()
    
    def clear_nodes(self):
        """清除所有节点"""
        # 清除线性布局中的节点
        while self.linear_layout.count():
            item = self.linear_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # 清除节点字典
        self.nodes.clear()
        self.selected_node_id = None
        self.add_branch_btn.setEnabled(False)
    
    def select_node(self, event_id):
        """选择节点"""
        # 取消之前选中的节点
        if self.selected_node_id and self.selected_node_id in self.nodes:
            self.nodes[self.selected_node_id].setSelected(False)
            
        # 选中新节点
        self.selected_node_id = event_id
        if event_id in self.nodes:
            self.nodes[event_id].setSelected(True)
            self.add_branch_btn.setEnabled(True)
        else:
            self.add_branch_btn.setEnabled(False)
            
        # 发送节点选中信号
        self.nodeSelected.emit(event_id)
    
    def add_new_node(self):
        """添加新节点"""
        if not self.story_timeline:
            return
            
        # 创建简单的文本输入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("添加新节点")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("节点内容:"))
        text_edit = QTextEdit()
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            content = text_edit.toPlainText()
            if content:
                # 添加到故事时间线
                new_event_id = self.story_timeline.add_event(
                    'text_node', 
                    {'text': content}, 
                    parent_event_id=self.selected_node_id
                )
                
                # 刷新显示
                self.refresh_timeline()
                
                # 选中新节点
                if new_event_id in self.nodes:
                    self.select_node(new_event_id)
    
    def create_branch(self, event_id=None):
        """创建分支点"""
        if not self.story_timeline:
            return
            
        # 如果没有指定event_id，使用当前选中的节点
        if not event_id and self.selected_node_id:
            event_id = self.selected_node_id
            
        if not event_id:
            QMessageBox.warning(self, "错误", "请先选择一个节点")
            return
            
        # 创建分支对话框
        dialog = BranchDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            choices = dialog.get_choices()
            if choices:
                # 创建分支点
                success, _ = self.story_timeline.create_branch_point(event_id, choices)
                
                if success:
                    # 刷新显示
                    self.refresh_timeline()
                else:
                    QMessageBox.warning(self, "错误", "创建分支失败")
    
    def edit_node(self, event_id):
        """编辑节点内容"""
        if not self.story_timeline or not event_id:
            return
            
        event = self.story_timeline.get_event(event_id)
        if not event:
            return
            
        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑节点")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("节点内容:"))
        text_edit = QTextEdit()
        
        # 设置当前内容
        if isinstance(event.data, dict) and 'text' in event.data:
            text_edit.setText(event.data['text'])
        elif isinstance(event.data, str):
            text_edit.setText(event.data)
        else:
            text_edit.setText(str(event.data))
            
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            content = text_edit.toPlainText()
            if content:
                # 更新节点内容
                if isinstance(event.data, dict):
                    event.data['text'] = content
                else:
                    event.data = {'text': content}
                    
                # 标记故事时间线为已修改
                self.story_timeline.dirty = True
                
                # 刷新显示
                self.refresh_timeline()
    
    def change_view_mode(self, mode):
        """切换视图模式"""
        if mode == "线性视图":
            self.scroll_area.setVisible(True)
            self.graph_view.setVisible(False)
        else:  # 图形视图
            self.scroll_area.setVisible(False)
            self.graph_view.setVisible(True)
            self.graph_view.update()
    
    def paint_graph(self, event):
        """绘制图形视图"""
        if not self.story_timeline or not self.story_timeline.events:
            return
            
        painter = QPainter(self.graph_view)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制区域尺寸
        width = self.graph_view.width()
        height = self.graph_view.height()
        
        # 节点尺寸和间距
        node_width = 80
        node_height = 40
        
        # 根据设置调整节点间距
        if self.settings.get("node_spacing") == "紧凑":
            h_spacing = 100
            v_spacing = 50
        elif self.settings.get("node_spacing") == "宽松":
            h_spacing = 180
            v_spacing = 100
        else:  # 标准
            h_spacing = 140
            v_spacing = 70
        
        # 确定是横向还是纵向排列
        is_vertical = self.settings.get("graph_direction", "自上而下") == "自上而下"
        
        # 图形绘制逻辑
        # 这里是简化的图形绘制实现，根据节点数量和分支关系绘制
        timeline_data = self.story_timeline.get_timeline_data(include_branches=True)
        
        # 创建节点位置字典
        nodes_pos = {}
        
        # 临时简化：线性排列所有节点
        for i, event_data in enumerate(timeline_data):
            event_id = event_data.get('event_id')
            is_branch = event_data.get('is_branch_point', False)
            is_selected = (event_id == self.selected_node_id)
            
            # 确定节点位置（简化计算）
            if is_vertical:
                x = int(width / 2 - node_width / 2)
                y = int(40 + i * v_spacing)
            else:
                x = int(40 + i * h_spacing)
                y = int(height / 2 - node_height / 2)
            
            nodes_pos[event_id] = (x, y)
            
            # 根据节点类型设置颜色
            if is_branch:
                # 应用分支节点颜色设置
                if self.settings.get("branch_node_color") == "蓝色":
                    node_color = QColor(255, 244, 224)  # 淡黄色
                    border_color = QColor(255, 216, 169)
                elif self.settings.get("branch_node_color") == "绿色":
                    node_color = QColor(232, 245, 233)  # 淡绿色
                    border_color = QColor(129, 199, 132)
                elif self.settings.get("branch_node_color") == "紫色":
                    node_color = QColor(243, 229, 245)  # 淡紫色
                    border_color = QColor(206, 147, 216)
                elif self.settings.get("branch_node_color") == "红色":
                    node_color = QColor(255, 235, 238)  # 淡红色
                    border_color = QColor(239, 154, 154)
                else:
                    # 默认蓝色
                    node_color = QColor(255, 244, 224)  # 淡黄色
                    border_color = QColor(255, 216, 169)
            else:
                node_color = QColor(241, 247, 231)  # 淡绿色
                border_color = QColor(162, 197, 121)
            
            # 绘制节点矩形
            painter.setPen(QPen(border_color, 1 if not is_selected else 2))
            painter.setBrush(QBrush(node_color))
            painter.drawRoundedRect(x, y, node_width, node_height, 5, 5)
            
            # 绘制节点文本
            painter.setPen(Qt.black)
            text = ""
            data = event_data.get('data', {})
            
            if isinstance(data, dict) and 'text' in data:
                text = data['text']
            elif isinstance(data, str):
                text = data
            else:
                text = str(data)
                
            # 裁剪文本
            if len(text) > 15:
                text = text[:12] + "..."
                
            # 绘制文本 - 使用矩形区域方式绘制，确保居中
            text_rect = painter.boundingRect(x, y, node_width, node_height, 
                                          Qt.AlignCenter | Qt.TextWordWrap, text)
            painter.drawText(text_rect, Qt.AlignCenter, text)
        
        # 绘制连接线
        painter.setPen(QPen(Qt.gray, 1, Qt.SolidLine))
        for event_data in timeline_data:
            event_id = event_data.get('event_id')
            parent_id = event_data.get('parent_event_id')
            
            if parent_id and parent_id in nodes_pos and event_id in nodes_pos:
                x1, y1 = nodes_pos[parent_id]
                x2, y2 = nodes_pos[event_id]
                
                # 调整连接点位置
                if is_vertical:
                    x1 += node_width / 2
                    y1 += node_height
                    x2 += node_width / 2
                else:
                    x1 += node_width
                    y1 += node_height / 2
                    y2 += node_height / 2
                
                # 确保使用整数坐标值
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        painter.end() 