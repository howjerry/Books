#!/usr/bin/env python3
"""
深度研究代理人實戰 - 第 7 章：搜尋與檢索引擎
知識圖譜實現

這個模組實現了知識圖譜功能：
1. 實體和關係存儲
2. 路徑查詢
3. 實體關係提取

使用方式：
    python knowledge_graph.py --demo
"""

import asyncio
import json
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


# =============================================================================
# 資料結構
# =============================================================================

@dataclass
class Entity:
    """實體"""
    name: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.name, self.entity_type))

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.name == other.name and self.entity_type == other.entity_type

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.entity_type,
            "properties": self.properties
        }


@dataclass
class Relation:
    """關係"""
    source: Entity
    target: Entity
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source.name,
            "target": self.target.name,
            "relation": self.relation_type,
            "properties": self.properties
        }

    def __str__(self) -> str:
        return f"({self.source.name}) --[{self.relation_type}]--> ({self.target.name})"


# =============================================================================
# 知識圖譜
# =============================================================================

class KnowledgeGraph:
    """
    知識圖譜

    ‹1› 存儲實體和關係
    ‹2› 支援路徑查詢
    ‹3› 提供知識推理
    """

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relations: List[Relation] = []
        self._adjacency: Dict[str, List[Tuple[str, Relation]]] = {}

    def _entity_key(self, entity: Entity) -> str:
        return f"{entity.entity_type}:{entity.name}"

    def add_entity(self, entity: Entity) -> None:
        """添加實體"""
        key = self._entity_key(entity)
        self._entities[key] = entity
        if key not in self._adjacency:
            self._adjacency[key] = []

    def add_relation(self, relation: Relation) -> None:
        """添加關係"""
        source_key = self._entity_key(relation.source)
        target_key = self._entity_key(relation.target)

        if source_key not in self._entities:
            self.add_entity(relation.source)
        if target_key not in self._entities:
            self.add_entity(relation.target)

        self._relations.append(relation)
        self._adjacency[source_key].append((target_key, relation))

    def get_entity(self, name: str, entity_type: str) -> Optional[Entity]:
        """獲取實體"""
        key = f"{entity_type}:{name}"
        return self._entities.get(key)

    def get_relations(
        self,
        source: Optional[Entity] = None,
        target: Optional[Entity] = None,
        relation_type: Optional[str] = None
    ) -> List[Relation]:
        """查詢關係"""
        results = []
        for relation in self._relations:
            if source and relation.source != source:
                continue
            if target and relation.target != target:
                continue
            if relation_type and relation.relation_type != relation_type:
                continue
            results.append(relation)
        return results

    def find_path(
        self,
        source: Entity,
        target: Entity,
        max_depth: int = 3
    ) -> Optional[List[Relation]]:
        """查找兩個實體之間的路徑"""
        source_key = self._entity_key(source)
        target_key = self._entity_key(target)

        if source_key not in self._entities or target_key not in self._entities:
            return None

        # BFS
        queue = deque([(source_key, [])])
        visited = {source_key}

        while queue:
            current, path = queue.popleft()

            if current == target_key:
                return path

            if len(path) >= max_depth:
                continue

            for next_key, relation in self._adjacency.get(current, []):
                if next_key not in visited:
                    visited.add(next_key)
                    queue.append((next_key, path + [relation]))

        return None

    def get_neighbors(
        self,
        entity: Entity,
        relation_type: Optional[str] = None
    ) -> List[Tuple[Entity, Relation]]:
        """獲取相鄰實體"""
        key = self._entity_key(entity)
        neighbors = []

        for next_key, relation in self._adjacency.get(key, []):
            if relation_type and relation.relation_type != relation_type:
                continue
            neighbors.append((self._entities[next_key], relation))

        return neighbors

    def to_prompt(self, max_triples: int = 20) -> str:
        """轉換為 prompt 格式"""
        lines = ["[知識圖譜]"]

        for relation in self._relations[:max_triples]:
            lines.append(str(relation))

        if len(self._relations) > max_triples:
            lines.append(f"... 還有 {len(self._relations) - max_triples} 個關係")

        return "\n".join(lines)

    def to_json(self) -> dict:
        """轉換為 JSON"""
        return {
            "entities": [e.to_dict() for e in self._entities.values()],
            "relations": [r.to_dict() for r in self._relations]
        }

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relation_count(self) -> int:
        return len(self._relations)

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        entity_types = {}
        for entity in self._entities.values():
            entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1

        relation_types = {}
        for relation in self._relations:
            relation_types[relation.relation_type] = relation_types.get(relation.relation_type, 0) + 1

        return {
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "entity_types": entity_types,
            "relation_types": relation_types
        }


# =============================================================================
# 實體關係提取器
# =============================================================================

class EntityRelationExtractor:
    """
    實體關係提取器

    ‹1› 使用 LLM 提取實體和關係
    ‹2› 支援自訂實體類型
    """

    EXTRACTION_PROMPT = """從以下文本中提取實體和關係。

實體類型：
- COMPANY: 公司、組織
- PERSON: 人物
- PRODUCT: 產品、技術
- LOCATION: 地點
- METRIC: 數據指標

輸出格式（JSON）：
{{
    "entities": [
        {{"name": "實體名稱", "type": "實體類型"}}
    ],
    "relations": [
        {{"source": "來源實體", "target": "目標實體", "relation": "關係類型"}}
    ]
}}

文本：
{text}

JSON："""

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        self.client = client

    async def extract(self, text: str) -> Tuple[List[Entity], List[Relation]]:
        """從文本提取實體和關係"""
        if not self.client:
            # 返回空結果
            return [], []

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": self.EXTRACTION_PROMPT.format(text=text)
            }],
            response_format={"type": "json_object"},
            max_tokens=1000
        )

        try:
            data = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return [], []

        entities = []
        entity_map = {}

        for e in data.get("entities", []):
            entity = Entity(
                name=e.get("name", ""),
                entity_type=e.get("type", "UNKNOWN")
            )
            entities.append(entity)
            entity_map[entity.name] = entity

        relations = []
        for r in data.get("relations", []):
            source_name = r.get("source", "")
            target_name = r.get("target", "")

            if source_name in entity_map and target_name in entity_map:
                relation = Relation(
                    source=entity_map[source_name],
                    target=entity_map[target_name],
                    relation_type=r.get("relation", "RELATED")
                )
                relations.append(relation)

        return entities, relations


# =============================================================================
# 簡單提取器（規則式）
# =============================================================================

class SimpleExtractor:
    """簡單的規則式提取器（不需要 API）"""

    PATTERNS = {
        "COMPANY": ["公司", "集團", "企業", "Corporation", "Inc", "Ltd"],
        "PRODUCT": ["產品", "技術", "系統", "平台", "晶片", "GPU", "CPU"],
        "METRIC": ["%", "億", "萬", "美元", "元"]
    }

    def extract(self, text: str) -> Tuple[List[Entity], List[Relation]]:
        """基於規則提取實體"""
        entities = []
        seen = set()

        # 簡單的實體識別
        words = text.split()
        for i, word in enumerate(words):
            for entity_type, patterns in self.PATTERNS.items():
                for pattern in patterns:
                    if pattern in word and word not in seen:
                        seen.add(word)
                        entities.append(Entity(
                            name=word,
                            entity_type=entity_type
                        ))
                        break

        return entities, []


# =============================================================================
# 示範
# =============================================================================

async def demo():
    """示範知識圖譜功能"""
    print("=" * 60)
    print("🕸️ 知識圖譜示範")
    print("=" * 60)

    # 創建知識圖譜
    kg = KnowledgeGraph()

    # 添加實體
    nvidia = Entity("NVIDIA", "COMPANY", {"market_share": 0.8})
    amd = Entity("AMD", "COMPANY", {"market_share": 0.1})
    intel = Entity("Intel", "COMPANY", {"market_share": 0.05})
    h100 = Entity("H100", "PRODUCT", {"type": "GPU"})
    mi300 = Entity("MI300", "PRODUCT", {"type": "GPU"})
    cuda = Entity("CUDA", "PRODUCT", {"type": "Platform"})

    kg.add_entity(nvidia)
    kg.add_entity(amd)
    kg.add_entity(intel)
    kg.add_entity(h100)
    kg.add_entity(mi300)
    kg.add_entity(cuda)

    # 添加關係
    kg.add_relation(Relation(nvidia, h100, "PRODUCES"))
    kg.add_relation(Relation(nvidia, cuda, "DEVELOPS"))
    kg.add_relation(Relation(amd, mi300, "PRODUCES"))
    kg.add_relation(Relation(amd, nvidia, "COMPETES_WITH"))
    kg.add_relation(Relation(intel, nvidia, "COMPETES_WITH"))
    kg.add_relation(Relation(h100, cuda, "RUNS_ON"))

    print("\n📊 統計資訊:")
    stats = kg.get_statistics()
    print(f"   實體數: {stats['entity_count']}")
    print(f"   關係數: {stats['relation_count']}")
    print(f"   實體類型: {stats['entity_types']}")
    print(f"   關係類型: {stats['relation_types']}")

    # 知識圖譜視圖
    print("\n📝 知識圖譜:")
    print(kg.to_prompt())

    # 查詢相鄰實體
    print("\n🔍 NVIDIA 的相鄰實體:")
    neighbors = kg.get_neighbors(nvidia)
    for entity, relation in neighbors:
        print(f"   {relation}")

    # 路徑查詢
    print("\n🛤️ AMD 到 CUDA 的路徑:")
    path = kg.find_path(amd, cuda, max_depth=3)
    if path:
        for relation in path:
            print(f"   {relation}")
    else:
        print("   未找到路徑")

    # 關係查詢
    print("\n🔗 所有競爭關係:")
    competitions = kg.get_relations(relation_type="COMPETES_WITH")
    for relation in competitions:
        print(f"   {relation}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="知識圖譜")
    parser.add_argument("--demo", action="store_true", help="執行示範")

    args = parser.parse_args()
    asyncio.run(demo())


if __name__ == "__main__":
    main()
