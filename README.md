# VNova_Assistant

## 项目简介

VNova_Assistant 是一款基于人工智能技术的 Ren'Py Galgame 剧情制作助手，旨在帮助开发者更高效地创建视觉小说和文字冒险游戏。通过集成本地 AI 模型和直观的图形界面，让游戏剧本创作变得轻松自如。

## 主要功能

- **AI 辅助剧情生成**：利用本地 LLM 模型辅助创建对话和剧情分支
- **剧情树可视化**：直观的图形界面展示故事分支和结构
- **情感分析**：基于剧情内容进行情感标注，辅助配置角色表情和语气
- **Ren'Py 导出**：一键导出为标准 Ren'Py 项目文件
- **素材管理**：集成的素材管理系统，方便组织和使用游戏资源
- **多主题支持**：提供亮色和暗色主题切换
- **中文友好**：完全支持中文界面和内容处理

## 安装要求

- Python 3.8 或更高版本
- [Ollama](https://ollama.ai/) 用于本地 AI 模型
- 支持的操作系统：Windows、macOS、Linux

## 依赖项

```
ollama>=0.1.0
PyQt5>=5.15.0
snownlp>=0.12.3
PyQt-Fluent-Widgets>=1.7.0
```

## 快速开始

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/HeDass-Code/VNova_Assistant.git
cd VNova_Assistant
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 安装并启动 Ollama
- 前往 [Ollama 官网](https://ollama.ai/) 下载并安装
- 拉取推荐模型
```bash
ollama pull llama3:8b
```

4. 运行应用
```bash
python main.py
```

## 配置说明

应用配置通过 `config.json` 文件管理，主要配置项包括：

- `ollama_host`: Ollama 服务地址，默认为 `http://localhost:11434`
- `default_model`: 默认使用的 AI 模型，如 `llama3:8b`
- `language`: 界面语言，默认为 `简体中文`
- `theme`: 界面主题，可选 `亮色` 或 `暗色`
- `projects_path`: 项目保存路径
- `export_path`: 导出文件路径
- `renpy_path`: Ren'Py SDK 路径（可选）

## 使用流程

1. 创建新项目或打开已有项目
2. 在剧情编辑器中编写或使用 AI 辅助生成剧情内容
3. 使用可视化剧情树管理故事分支
4. 通过素材管理器导入和组织游戏资源
5. 预览剧情效果
6. 导出为 Ren'Py 项目

## 许可证

本项目基于 [MIT 许可证](LICENSE) 发布。

## 贡献指南

欢迎提交 Issues 和 Pull Requests 来改进项目。在提交代码前，请确保：

1. 代码符合项目的编码规范
2. 新功能包含适当的测试
3. 所有测试都能通过
4. 更新相关文档

## 联系方式

如有问题或建议，请通过 GitHub Issues 与我们联系。

---

**VNova_Assistant** - 让 Galgame 剧情创作更简单
