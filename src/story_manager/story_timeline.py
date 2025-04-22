# -*- coding: utf-8 -*-
"""
VNova Assistant - 视觉小说制作助手
故事时间线管理模块，包括事件、分支和撤销功能
"""

import json
from datetime import datetime

class StoryEvent:
    """Represents a single event in the story timeline."""
    def __init__(self, timestamp, event_type, data, parent_event_id=None, ollama_request_id=None):
        self.event_id = f"{timestamp}-{event_type}-{hash(json.dumps(data))}" # Simple unique ID
        self.timestamp = timestamp
        self.event_type = event_type # e.g., 'text_node', 'choice', 'ollama_generation'
        self.data = data # Content of the event (text, choices, etc.)
        self.parent_event_id = parent_event_id # ID of the preceding event
        self.child_event_ids = [] # IDs of subsequent events (for branching)
        self.ollama_request_id = ollama_request_id # Link to the Ollama request if generated
        self.emotion = None # Placeholder for emotion analysis result
        self.is_branch_point = False # 标记是否为分支节点
        self.branch_choices = [] # 分支选项列表，格式为 [{"text": "选项1", "target_id": "event_id1"}, ...]

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "data": self.data,
            "parent_event_id": self.parent_event_id,
            "child_event_ids": self.child_event_ids,
            "ollama_request_id": self.ollama_request_id,
            "emotion": self.emotion,
            "is_branch_point": self.is_branch_point,
            "branch_choices": self.branch_choices
        }

    @staticmethod
    def from_dict(data):
        event = StoryEvent(
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_type=data['event_type'],
            data=data['data'],
            parent_event_id=data.get('parent_event_id'),
            ollama_request_id=data.get('ollama_request_id')
        )
        event.event_id = data['event_id']
        event.child_event_ids = data.get('child_event_ids', [])
        event.emotion = data.get('emotion')
        event.is_branch_point = data.get('is_branch_point', False)
        event.branch_choices = data.get('branch_choices', [])
        return event

class StoryTimeline:
    """Manages the overall story structure as a timeline of events."""
    def __init__(self):
        self.events = {} # Dictionary to store events by event_id
        self.head_event_id = None # ID of the latest event in the main timeline
        self.characters = {} # Dictionary to store character profiles by character_id
        self.active_branch_id = None # 当前活动分支ID
        # 素材库
        self.assets = {
            'backgrounds': {},  # 背景素材
            'characters': {},   # 角色素材
            'sounds': {},       # 音效素材
            'music': {}         # 音乐素材
        }
        # Potentially add more structure for branches later
        self.dirty = False # Flag to track unsaved changes

    def add_event(self, event_type, data, parent_event_id=None, ollama_request_id=None):
        """Adds a new event to the timeline."""
        timestamp = datetime.now()
        if parent_event_id is None:
            parent_event_id = self.head_event_id

        new_event = StoryEvent(timestamp, event_type, data, parent_event_id, ollama_request_id)
        self.events[new_event.event_id] = new_event

        if parent_event_id and parent_event_id in self.events:
            self.events[parent_event_id].child_event_ids.append(new_event.event_id)

        # For simplicity now, always update head to the new event.
        # Branching logic will require more complex head management.
        self.head_event_id = new_event.event_id
        print(f"Added event: {new_event.event_id}, Parent: {parent_event_id}")
        self.dirty = True # Mark timeline as modified
        return new_event.event_id

    def create_branch_point(self, event_id, branch_choices):
        """将指定事件设为分支点，并添加分支选项
        
        Args:
            event_id: 要设为分支点的事件ID
            branch_choices: 分支选项列表，格式为 [{"text": "选项文本", "data": {分支内容数据}}]
        
        Returns:
            bool: 操作是否成功
            list: 创建的分支事件ID列表
        """
        if event_id not in self.events:
            print(f"Event {event_id} not found")
            return False, []
            
        event = self.events[event_id]
        event.is_branch_point = True
        
        # 保存现有子节点列表（如果有的话）
        existing_children = event.child_event_ids.copy()
        
        # 清除现有子节点关系（将在分支选项中重建）
        event.child_event_ids = []
        event.branch_choices = []
        
        created_branch_ids = []
        
        # 为每个分支选项创建事件节点
        for choice in branch_choices:
            # 创建分支事件
            branch_event_id = self.add_event('branch_option', 
                                           {'text': choice['text'], 'content': choice.get('data', {})}, 
                                           parent_event_id=event_id)
            
            # 将已存在的子节点连接到第一个分支（如果存在且这是第一个分支）
            if existing_children and not created_branch_ids:
                branch_event = self.events[branch_event_id]
                for child_id in existing_children:
                    child = self.events.get(child_id)
                    if child:
                        child.parent_event_id = branch_event_id
                        branch_event.child_event_ids.append(child_id)
            
            # 添加到分支点的选项中
            event.branch_choices.append({
                "text": choice['text'],
                "target_id": branch_event_id
            })
            
            created_branch_ids.append(branch_event_id)
        
        self.dirty = True
        return True, created_branch_ids
    
    def get_branch_options(self, event_id):
        """获取分支节点的所有选项
        
        Args:
            event_id: 分支节点ID
        
        Returns:
            list: 分支选项列表
        """
        if event_id not in self.events:
            return []
            
        event = self.events[event_id]
        if not event.is_branch_point:
            return []
            
        return event.branch_choices
        
    def select_branch(self, branch_id):
        """选择指定的分支
        
        Args:
            branch_id: 要选择的分支事件ID
        
        Returns:
            bool: 操作是否成功
        """
        if branch_id not in self.events:
            print(f"Branch {branch_id} not found")
            return False
            
        self.active_branch_id = branch_id
        self.head_event_id = branch_id
        return True
        
    def is_branch_point(self, event_id):
        """检查事件是否为分支点
        
        Args:
            event_id: 事件ID
            
        Returns:
            bool: 是否为分支点
        """
        if event_id not in self.events:
            return False
        return self.events[event_id].is_branch_point

    def get_event(self, event_id):
        """Retrieves an event by its ID."""
        return self.events.get(event_id)

    def get_timeline_data(self, start_event_id=None, include_branches=False):
        """Returns a list of events representing a path in the timeline.
        
        Args:
            start_event_id: 开始点的事件ID，如果为None则从头节点开始
            include_branches: 是否包含分支信息
            
        Returns:
            list: 事件列表
        """
        # Basic implementation: returns the main path from the start or head
        # Needs enhancement for proper branch traversal
        path = []
        current_id = self.active_branch_id if self.active_branch_id else self.head_event_id
        while current_id:
            event = self.get_event(current_id)
            if event:
                event_data = event.to_dict()
                # 如果需要包含分支信息
                if include_branches and event.is_branch_point:
                    # 为每个分支添加详细信息
                    branch_details = []
                    for choice in event.branch_choices:
                        branch_event = self.get_event(choice["target_id"])
                        if branch_event:
                            branch_details.append({
                                "text": choice["text"],
                                "target_id": choice["target_id"],
                                "content": branch_event.data
                            })
                    event_data["branch_details"] = branch_details
                
                path.append(event_data)
                current_id = event.parent_event_id
                if start_event_id and current_id == start_event_id:
                    # Include the start event if specified and break
                    start_event = self.get_event(start_event_id)
                    if start_event:
                        path.append(start_event.to_dict())
                    break
            else:
                break
        return path[::-1] # Reverse to get chronological order
        
    def get_all_branches(self):
        """获取故事中所有分支点及其选项
        
        Returns:
            list: 分支点列表，每个分支点包含其选项信息
        """
        branches = []
        for event_id, event in self.events.items():
            if event.is_branch_point:
                branch_info = {
                    "event_id": event_id,
                    "timestamp": event.timestamp.isoformat(),
                    "content": event.data,
                    "choices": event.branch_choices
                }
                branches.append(branch_info)
        return branches

    def undo_ollama_generation(self, ollama_request_id):
        """Removes events associated with a specific Ollama generation."""
        events_to_remove = [
            event_id for event_id, event in self.events.items()
            if event.ollama_request_id == ollama_request_id
        ]

        if not events_to_remove:
            print(f"No events found for Ollama request ID: {ollama_request_id}")
            return False

        # This is a simplified undo. A robust implementation needs to handle
        # re-linking parent/child relationships correctly, especially with branches.
        for event_id in events_to_remove:
            event = self.events.pop(event_id, None)
            if event and event.parent_event_id:
                parent = self.get_event(event.parent_event_id)
                if parent:
                    try:
                        parent.child_event_ids.remove(event_id)
                    except ValueError:
                        pass # Child already removed or not present
            # If the removed event was the head, reset head to its parent
            if self.head_event_id == event_id:
                self.head_event_id = event.parent_event_id if event else None

        print(f"Removed {len(events_to_remove)} events for Ollama request ID: {ollama_request_id}")
        # Need to potentially update self.head_event_id more carefully
        # if the removed event wasn't the absolute last one.
        if events_to_remove:
            self.dirty = True # Mark timeline as modified
        return True

    def save_timeline(self, filepath):
        """Saves the current timeline state to a file."""
        data_to_save = {
            "events": {eid: event.to_dict() for eid, event in self.events.items()},
            "head_event_id": self.head_event_id,
            "active_branch_id": self.active_branch_id,
            "characters": self.characters, # Include character data
            "assets": self.assets # Include assets
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            print(f"Timeline saved to {filepath}")
            self.dirty = False # Mark as saved
        except IOError as e:
            print(f"Error saving timeline: {e}")

    def load_timeline(self, filepath):
        """Loads a timeline state from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data_loaded = json.load(f)
            self.events = {
                eid: StoryEvent.from_dict(edata)
                for eid, edata in data_loaded.get("events", {}).items()
            }
            self.head_event_id = data_loaded.get("head_event_id")
            self.active_branch_id = data_loaded.get("active_branch_id")
            self.characters = data_loaded.get("characters", {}) # Load character data
            self.assets = data_loaded.get("assets", {}) # Load assets
            print(f"Timeline loaded from {filepath}")
            self.dirty = False # Reset dirty flag after loading
        except FileNotFoundError:
            print(f"Timeline file not found: {filepath}. Starting fresh.")
            self.__init__() # Reset to empty state
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading timeline: {e}. Starting fresh.")
            self.__init__() # Reset to empty state
        # Ensure characters attribute exists even if file load fails partially
        if not hasattr(self, 'characters'):
            self.characters = {}

    # 添加素材库相关方法
    def add_asset(self, category, asset_id, asset_data):
        """添加素材到素材库
        
        Args:
            category: 素材类别('backgrounds', 'characters', 'sounds', 'music')
            asset_id: 素材ID，通常是文件名
            asset_data: 素材数据，包含路径、描述等
            
        Returns:
            bool: 操作是否成功
        """
        if category not in self.assets:
            print(f"无效的素材类别: {category}")
            return False
            
        # 确保数据格式正确
        if not isinstance(asset_data, dict):
            asset_data = {'path': str(asset_data)}
        
        self.assets[category][asset_id] = asset_data
        self.dirty = True
        return True
    
    def remove_asset(self, category, asset_id):
        """从素材库中删除素材
        
        Args:
            category: 素材类别
            asset_id: 素材ID
            
        Returns:
            bool: 操作是否成功
        """
        if category not in self.assets or asset_id not in self.assets[category]:
            return False
            
        del self.assets[category][asset_id]
        self.dirty = True
        return True
    
    def get_assets(self, category=None):
        """获取素材列表
        
        Args:
            category: 指定类别，如果为None则返回所有素材
            
        Returns:
            dict: 素材字典
        """
        if category is None:
            return self.assets
        
        if category not in self.assets:
            return {}
            
        return self.assets[category]

# Example Usage (for testing)
if __name__ == '__main__':
    timeline = StoryTimeline()
    event1_id = timeline.add_event('text_node', {'text': '故事开始了。'})
    event2_id = timeline.add_event('text_node', {'text': '主角醒来。'}, parent_event_id=event1_id)
    ollama_id = "ollama-gen-123"
    event3_id = timeline.add_event('ollama_generation', {'prompt': '描述房间', 'response': '房间很暗。'}, parent_event_id=event2_id, ollama_request_id=ollama_id)
    event4_id = timeline.add_event('text_node', {'text': '他看到了什么？'}, parent_event_id=event3_id)

    print("\nFull Timeline:")
    print(json.dumps(timeline.get_timeline_data(), indent=2, ensure_ascii=False))

    # Save
    timeline.save_timeline('test_timeline.json')

    # Load
    new_timeline = StoryTimeline()
    new_timeline.load_timeline('test_timeline.json')
    print("\nLoaded Timeline:")
    print(json.dumps(new_timeline.get_timeline_data(), indent=2, ensure_ascii=False))

    # Undo
    print("\nUndoing Ollama Generation...")
    undone = new_timeline.undo_ollama_generation(ollama_id)
    if undone:
        print("\nTimeline after Undo:")
        print(json.dumps(new_timeline.get_timeline_data(), indent=2, ensure_ascii=False))
        new_timeline.save_timeline('test_timeline_after_undo.json')

    # Clean up test files
    import os
    try:
        os.remove('test_timeline.json')
        os.remove('test_timeline_after_undo.json')
    except OSError:
        pass