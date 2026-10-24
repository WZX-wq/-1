"""Parse structured AI pages without converting their nested objects to text."""

import json
import re


def normalize_json_records(value):
    """Accept JSON objects, arrays and double-encoded objects; ignore scalars."""
    def visit(current, depth=0):
        if depth > 8:
            return []
        if isinstance(current, dict):
            return [current] if current else []
        if isinstance(current, (list, tuple)):
            return [record for item in current for record in visit(item, depth + 1)]
        if not isinstance(current, str) or not current.strip():
            return []
        text = current.strip()
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text).strip()
        try:
            parsed = json.loads(text)
        except ValueError:
            # Support explanatory text around a JSON array using a real JSON
            # decoder, so nested arrays and brackets inside strings stay intact.
            parsed = None
            for index, char in enumerate(text):
                if char != '[':
                    continue
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(text[index:])
                    break
                except ValueError:
                    continue
        return visit(parsed, depth + 1)

    return visit(value)


def normalize_guide_pages(value, kind):
    """Validate the renderer's schema and preserve valid pages in input order."""
    fields = {
        'itinerary': ('行程安排', '玩点亮点', '特色美食', '注意事项'),
        'food': ('名称', '简介/特色', '价格信息'),
        'customs': ('风俗名称', '简介寓意', '具体做法', '时间地域'),
    }[kind]

    def text_fields(data):
        if not isinstance(data, dict):
            return None
        if not all(isinstance(data.get(field), str) for field in fields):
            return None
        result = {field: data[field].strip() for field in fields}
        return result if any(result.values()) else None

    pages = []
    for record in normalize_json_records(value):
        for title, content in record.items():
            if not isinstance(title, str) or not title.strip():
                continue
            if kind == 'itinerary':
                normalized = text_fields(content)
            elif isinstance(content, dict):
                normalized = {}
                for key, item in content.items():
                    if isinstance(key, str) and key.startswith('项目'):
                        fields_data = text_fields(item)
                        if fields_data:
                            normalized[f'项目{len(normalized) + 1}'] = fields_data
            else:
                normalized = None
            if normalized:
                pages.append({title.strip(): normalized})
    return pages


def cached_guide_is_valid(content, kind):
    """Reject cached copywriting flattened by older versions so AI regenerates it."""
    if not isinstance(content, str):
        return False
    pages = content.split('&&')[2:]
    return bool(pages) and all(normalize_guide_pages(page, kind) for page in pages)
