#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sensemble 教学平台知识点同步工具。

功能：
  - 读取本地 Markdown 文件（docs/knowledge/ 目录）
  - 解析 YAML 前置元数据（title, difficulty, tags 等）
  - 调用后端 API 创建或更新知识点
  - 支持批量同步、增量更新、错误恢复

用法：
  python tools/sync_knowledge.py --dir docs/knowledge --course EE101 --api http://localhost:8000
  python tools/sync_knowledge.py --file docs/knowledge/intro.md --course EE101 --dry-run

依赖：pip install httpx pyyaml
"""
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import re

import httpx
import yaml

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ========== Markdown 解析 ==========
class MarkdownKnowledgeParser:
    """解析 Markdown 文件的元数据和内容。

    格式：
      ```yaml
      ---
      title: 热电效应
      difficulty: 中级
      tags: [传感器, 热电, 物理]
      parent: 传感器基础
      ---
      ```
      正文内容（HTML 或 Markdown）...
    """

    @staticmethod
    def parse(file_path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        解析 Markdown 文件。

        Returns:
            (元数据字典, 正文内容)
            若无 YAML frontmatter，元数据为 {filename: 文件名}
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}：{e}")
            return None, None

        # 检测 YAML frontmatter（--- ... ---）
        if content.startswith('---'):
            # 查找第二个 ---
            match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
            if match:
                yaml_str = match.group(1)
                body = match.group(2).strip()

                try:
                    metadata = yaml.safe_load(yaml_str) or {}
                except yaml.YAMLError as e:
                    logger.warning(f"YAML 解析失败 {file_path}：{e}，使用默认元数据")
                    metadata = {}
            else:
                # 有 --- 但格式不对，整个文件作为内容
                metadata = {}
                body = content
        else:
            # 无 YAML frontmatter，整个文件作为内容
            metadata = {}
            body = content

        # 填充默认元数据
        if not isinstance(metadata, dict):
            metadata = {}

        if 'title' not in metadata:
            # 从文件名推断标题
            metadata['title'] = Path(file_path).stem.replace('_', ' ').title()

        if 'content' not in metadata:
            metadata['content'] = body

        return metadata, body


# ========== API 客户端 ==========
class TeachingApiClient:
    """异步 HTTP 客户端，与 Sensemble 后端交互。"""

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {'Authorization': f'Bearer {token}'} if token else {}

    async def list_nodes(self, course_code: Optional[str] = None) -> List[Dict]:
        """获取知识点列表（支持按课程过滤）。"""
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f'{self.base_url}/api/v1/teaching/nodes',
                    params={'course_code': course_code} if course_code else None,
                    headers=self.headers,
                    timeout=10.0
                )
                r.raise_for_status()
                return r.json() or []
            except httpx.HTTPError as e:
                logger.error(f"获取知识点列表失败：{e}")
                raise

    async def find_node_by_title(self, title: str, nodes: List[Dict],
                                  parent_id: Optional[int] = None) -> Optional[Dict]:
        """在节点树中递归查找指定标题的节点。"""
        for node in nodes:
            if node['title'] == title and node.get('parent_id') == parent_id:
                return node
            # 递归子节点
            if node.get('children'):
                child = await self.find_node_by_title(title, node['children'], parent_id)
                if child:
                    return child
        return None

    async def create_node(self, title: str, content: str,
                         parent_id: Optional[int] = None,
                         course_code: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         difficulty: Optional[str] = None) -> Dict:
        """创建知识点。"""
        payload = {
            'title': title,
            'content': content,
            'parent_id': parent_id,
            'course_code': course_code,
            'order_index': 0
        }

        # 扩展 content 加入元数据（作为 HTML 注释保留原始数据）
        if tags or difficulty:
            metadata_comment = '<!-- METADATA '
            meta_dict = {}
            if tags:
                meta_dict['tags'] = tags
            if difficulty:
                meta_dict['difficulty'] = difficulty
            metadata_comment += json.dumps(meta_dict) + ' -->\n'
            payload['content'] = metadata_comment + content

        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    f'{self.base_url}/api/v1/teaching/nodes',
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as e:
                logger.error(f"创建知识点失败 '{title}'：{e}")
                raise

    async def update_node(self, node_id: int, title: Optional[str] = None,
                         content: Optional[str] = None,
                         parent_id: Optional[int] = None) -> Dict:
        """更新知识点。"""
        payload = {}
        if title is not None:
            payload['title'] = title
        if content is not None:
            payload['content'] = content
        if parent_id is not None:
            payload['parent_id'] = parent_id

        if not payload:
            logger.warning(f"更新内容为空，跳过节点 ID={node_id}")
            return {}

        async with httpx.AsyncClient() as client:
            try:
                r = await client.patch(
                    f'{self.base_url}/api/v1/teaching/nodes/{node_id}',
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as e:
                logger.error(f"更新知识点失败 ID={node_id}：{e}")
                raise


# ========== 同步逻辑 ==========
class KnowledgeSyncer:
    """同步本地知识点文件到后端。"""

    def __init__(self, api: TeachingApiClient, course_code: str):
        self.api = api
        self.course_code = course_code

    async def sync_files(self, file_paths: List[str], dry_run: bool = False) -> Tuple[int, int, int]:
        """
        同步多个文件。

        Returns:
            (创建数, 更新数, 失败数)
        """
        created = 0
        updated = 0
        failed = 0

        # 获取现有节点树
        try:
            existing_nodes = await self.api.list_nodes(course_code=self.course_code)
        except Exception:
            logger.error("无法获取现有节点，请检查后端连接")
            return 0, 0, len(file_paths)

        logger.info(f"检测到现有知识点 {len(self._flatten_nodes(existing_nodes))} 个")

        for file_path in file_paths:
            try:
                # 解析文件
                metadata, body = MarkdownKnowledgeParser.parse(file_path)
                if not metadata:
                    logger.error(f"解析失败：{file_path}")
                    failed += 1
                    continue

                title = metadata.get('title', Path(file_path).stem)
                content = metadata.get('content', body)
                parent_title = metadata.get('parent')
                tags = metadata.get('tags', [])
                difficulty = metadata.get('difficulty')

                # 查找父节点
                parent_id = None
                if parent_title:
                    parent_node = await self.api.find_node_by_title(
                        parent_title, existing_nodes
                    )
                    if parent_node:
                        parent_id = parent_node['id']
                    else:
                        logger.warning(f"父节点 '{parent_title}' 不存在，{title} 将作为顶级节点")

                # 检查节点是否已存在
                existing_node = await self.api.find_node_by_title(
                    title, existing_nodes, parent_id
                )

                if existing_node:
                    # 更新
                    if not dry_run:
                        await self.api.update_node(
                            existing_node['id'],
                            content=content
                        )
                        logger.info(f"✓ 更新 '{title}' (ID={existing_node['id']})")
                    else:
                        logger.info(f"→ [模拟] 更新 '{title}'")
                    updated += 1
                else:
                    # 创建
                    if not dry_run:
                        result = await self.api.create_node(
                            title=title,
                            content=content,
                            parent_id=parent_id,
                            course_code=self.course_code,
                            tags=tags,
                            difficulty=difficulty
                        )
                        logger.info(f"✓ 新建 '{title}' (ID={result['id']})")
                    else:
                        logger.info(f"→ [模拟] 新建 '{title}'")
                    created += 1

            except Exception as e:
                logger.error(f"✗ 处理失败 {file_path}：{e}")
                failed += 1

        return created, updated, failed

    @staticmethod
    def _flatten_nodes(nodes: List[Dict]) -> List[Dict]:
        """将树形节点展平。"""
        flat = []
        for n in nodes:
            flat.append(n)
            if n.get('children'):
                flat.extend(KnowledgeSyncer._flatten_nodes(n['children']))
        return flat


# ========== CLI 主程序 ==========
async def main():
    parser = argparse.ArgumentParser(
        description='Sensemble 知识点同步工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 同步整个目录
  python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101

  # 同步单个文件
  python tools/sync_knowledge.py --file docs/knowledge/ch1/intro.md --course EE101

  # 模拟运行（不实际提交）
  python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101 --dry-run

  # 指定后端地址和认证令牌
  python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101 \\
    --api http://192.168.1.100:8000 --token eyJhbGc...
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='单个 Markdown 文件路径')
    group.add_argument('--dir', help='Markdown 文件目录（递归扫描所有子目录）')

    parser.add_argument('--course', required=True, help='课程代码（如 "EE101"）')
    parser.add_argument('--api', default='http://localhost:8000',
                       help='后端 API 地址（默认 http://localhost:8000）')
    parser.add_argument('--token', help='认证 JWT Token（可选）')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟运行，不实际提交')

    args = parser.parse_args()

    # 确定文件列表
    files = []
    if args.file:
        if not Path(args.file).is_file():
            logger.error(f"文件不存在：{args.file}")
            sys.exit(1)
        files = [args.file]
    else:  # args.dir
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            logger.error(f"目录不存在：{args.dir}")
            sys.exit(1)

        # 递归扫描所有 .md 文件（包括子目录）
        files = sorted([str(f) for f in dir_path.glob('**/*.md')])

        if not files:
            logger.error(f"目录中未找到 .md 文件：{args.dir}")
            sys.exit(1)

    logger.info(f"📚 开始同步 {len(files)} 个文件到课程 '{args.course}'")
    logger.info(f"   后端地址：{args.api}")
    if args.dry_run:
        logger.info("   [模拟运行模式，不实际提交]")
    logger.info("")

    # 初始化 API 客户端和同步器
    api = TeachingApiClient(args.api, token=args.token)
    syncer = KnowledgeSyncer(api, course_code=args.course)

    # 执行同步
    try:
        created, updated, failed = await syncer.sync_files(files, dry_run=args.dry_run)

        logger.info("")
        logger.info(f"✓ 同步完成：新建 {created}，更新 {updated}，失败 {failed}")

        if failed > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⊘ 用户中止")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ 同步异常：{e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
