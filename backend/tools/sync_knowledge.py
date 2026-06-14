#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sensemble 教学平台 Markdown 知识点批量导入工具。

功能：读取本地 Markdown 文件，解析元数据和内容，通过 API 同步到数据库。

用法：
  python tools/sync_knowledge.py --file <路径> --course <课程代码>
  python tools/sync_knowledge.py --dir <目录> --course <课程代码> --recursive

依赖：pip install httpx pyyaml markdown
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    import httpx
    import yaml
    import markdown
except ImportError:
    print("❌ 缺失依赖。请运行：pip install httpx pyyaml markdown")
    sys.exit(1)


# ========== Markdown 解析 ==========

def parse_frontmatter(md_text: str) -> Tuple[Dict, str]:
    """
    解析 Markdown 文件头的 YAML 元数据和正文。

    格式：
    ---
    title: 知识点标题
    difficulty: intermediate
    tags: [传感器, 热电]
    ---

    正文内容...
    """
    if not md_text.startswith('---'):
        return {}, md_text

    try:
        parts = md_text.split('---', 2)
        if len(parts) < 3:
            return {}, md_text

        meta_yaml = parts[1].strip()
        body = parts[2].strip()

        meta = yaml.safe_load(meta_yaml) or {}
        return meta, body
    except Exception as e:
        print(f"⚠️  解析 YAML 元数据失败：{e}")
        return {}, md_text


def markdown_to_html(md_text: str) -> str:
    """Markdown → HTML（保留 LaTeX 公式原样）。"""
    try:
        html = markdown.markdown(
            md_text,
            extensions=['tables', 'fenced_code', 'codehilite']
        )
        return html
    except Exception as e:
        print(f"⚠️  Markdown 转换失败：{e}")
        return f"<p>{md_text}</p>"


def parse_markdown_structure(md_text: str) -> List[Dict]:
    """
    解析 Markdown 标题结构，返回知识点列表。

    格式：
      # 一级标题（一级知识点）
      内容...
      ## 二级标题（二级知识点）
      内容...
    """
    nodes = []
    stack = [None]  # 虚拟根节点

    lines = md_text.split('\n')
    current_heading = None
    current_level = 0
    current_content = []

    for line in lines:
        match = re.match(r'^(#+)\s+(.+)$', line)

        if match:
            # 保存前一个标题
            if current_heading:
                html = markdown_to_html('\n'.join(current_content)).strip()
                nodes.append({
                    'title': current_heading,
                    'content': html,
                    'level': current_level,
                    'parent_title': stack[current_level - 1] if current_level > 0 else None
                })

            # 新标题
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            current_content = []

            # 维护栈
            while len(stack) > current_level:
                stack.pop()
            stack.append(current_heading)
        else:
            if current_heading:
                current_content.append(line)

    # 保存最后一个
    if current_heading:
        html = markdown_to_html('\n'.join(current_content)).strip()
        nodes.append({
            'title': current_heading,
            'content': html,
            'level': current_level,
            'parent_title': stack[current_level - 1] if current_level > 0 else None
        })

    return nodes


# ========== API 交互 ==========

class TeachingApiClient:
    """与后端 API 交互。"""

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """关闭客户端。"""
        await self.client.aclose()

    def _headers(self) -> Dict:
        """构建请求头。"""
        h = {'Content-Type': 'application/json'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        return h

    async def list_nodes(self, course_code: Optional[str] = None) -> List[Dict]:
        """获取现有知识点。"""
        params = {}
        if course_code:
            params['course_code'] = course_code

        r = await self.client.get(
            f'{self.base_url}/api/v1/teaching/nodes',
            params=params,
            headers=self._headers()
        )
        r.raise_for_status()
        return r.json() or []

    async def create_node(
        self,
        title: str,
        content: str,
        parent_id: Optional[int] = None,
        course_code: Optional[str] = None,
        order_index: int = 0
    ) -> Dict:
        """创建知识点。"""
        payload = {
            'title': title,
            'content': content,
            'parent_id': parent_id,
            'course_code': course_code,
            'order_index': order_index
        }
        r = await self.client.post(
            f'{self.base_url}/api/v1/teaching/nodes',
            json=payload,
            headers=self._headers()
        )
        r.raise_for_status()
        return r.json()

    async def update_node(self, node_id: int, updates: Dict) -> Dict:
        """更新知识点。"""
        r = await self.client.patch(
            f'{self.base_url}/api/v1/teaching/nodes/{node_id}',
            json=updates,
            headers=self._headers()
        )
        r.raise_for_status()
        return r.json()

    def find_by_title_and_parent(
        self,
        nodes: List[Dict],
        title: str,
        parent_id: Optional[int] = None
    ) -> Optional[Dict]:
        """递归查找节点（按标题和父节点）。"""
        for n in nodes:
            if n['title'] == title and n.get('parent_id') == parent_id:
                return n
            child = self.find_by_title_and_parent(
                n.get('children', []), title, parent_id
            )
            if child:
                return child
        return None


# ========== 同步逻辑 ==========

async def sync_markdown_files(
    file_paths: List[str],
    api: TeachingApiClient,
    course_code: str,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    同步 Markdown 文件。

    返回：(创建数, 跳过数)
    """
    created = 0
    skipped = 0

    # 获取现有知识点
    existing = await api.list_nodes(course_code=course_code)

    for file_path in file_paths:
        if not file_path.endswith('.md'):
            print(f"  ⊘ 跳过非 Markdown：{file_path}")
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ✗ 读取失败 {file_path}：{e}")
            continue

        # 解析元数据和正文
        meta, body = parse_frontmatter(content)

        # 从元数据或文件名获取标题
        title = meta.get('title') or Path(file_path).stem

        # 解析知识点树
        nodes = parse_markdown_structure(body)

        # 构建并创建知识点
        node_id_map = {}

        for node in nodes:
            parent_id = None

            # 找父节点 ID
            if node['parent_title']:
                parent_id = node_id_map.get(node['parent_title'])

            # 检查是否已存在
            existing_node = api.find_by_title_and_parent(
                existing, node['title'], parent_id
            )

            if existing_node:
                print(f"  · {node['title']} (已存在，跳过)")
                node_id_map[node['title']] = existing_node['id']
                skipped += 1
            else:
                try:
                    if not dry_run:
                        result = await api.create_node(
                            title=node['title'],
                            content=node['content'],
                            parent_id=parent_id,
                            course_code=course_code,
                            order_index=nodes.index(node)
                        )
                        node_id_map[node['title']] = result['id']
                        print(f"  ✓ {node['title']} (新建，ID={result['id']})")
                    else:
                        print(f"  → {node['title']} (模拟新建，未实际提交)")
                        node_id_map[node['title']] = -1
                    created += 1
                except Exception as e:
                    print(f"  ✗ {node['title']} 创建失败：{e}")

    return created, skipped


# ========== CLI ==========

async def main():
    parser = argparse.ArgumentParser(description='Sensemble Markdown 知识点批量导入')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='单个 Markdown 文件')
    group.add_argument('--dir', help='Markdown 文件目录')

    parser.add_argument('--recursive', action='store_true', help='递归扫描目录')
    parser.add_argument('--api', default='http://localhost:8000', help='后端 URL')
    parser.add_argument('--course', required=True, help='课程代码')
    parser.add_argument('--token', help='认证 Token')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行')

    args = parser.parse_args()

    # 确定文件列表
    files = []
    if args.file:
        if not os.path.isfile(args.file):
            print(f"✗ 文件不存在：{args.file}")
            sys.exit(1)
        files = [args.file]
    else:
        if not os.path.isdir(args.dir):
            print(f"✗ 目录不存在：{args.dir}")
            sys.exit(1)

        if args.recursive:
            files = [str(f) for f in Path(args.dir).rglob('*.md')]
        else:
            files = [str(f) for f in Path(args.dir).glob('*.md')]

        if not files:
            print(f"✗ 未找到 Markdown 文件：{args.dir}")
            sys.exit(1)

    print(f"\n📚 同步 {len(files)} 个文件到课程 '{args.course}'")
    print(f"   API：{args.api}")
    if args.dry_run:
        print("   [模拟运行模式]")
    print()

    # 初始化 API
    api = TeachingApiClient(args.api, token=args.token)

    try:
        # 测试连接
        await api.list_nodes()
    except Exception as e:
        print(f"✗ 无法连接：{e}")
        sys.exit(1)

    # 执行同步
    try:
        created, skipped = await sync_markdown_files(
            files, api, args.course, dry_run=args.dry_run
        )
        print(f"\n✓ 完成：新建 {created}，跳过 {skipped}")
    except KeyboardInterrupt:
        print("\n⊘ 用户中止")
        sys.exit(1)
    finally:
        await api.close()


if __name__ == '__main__':
    asyncio.run(main())
