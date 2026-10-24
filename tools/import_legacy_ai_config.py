"""Migrate the owner's legacy PyInstaller credential without printing its value.

This development helper reads bytecode constants, never executes the old EXE,
and requires PyInstaller only on the build machine.
"""
from __future__ import annotations

import argparse
import dis
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_tool.runtime_config import save_ai_config


def import_config(executable: Path, destination: Path, provider: str) -> Path:
    from PyInstaller.archive.readers import CArchiveReader

    if destination.exists():
        raise RuntimeError(f"配置已存在，已保留原配置：{destination}")
    archive = CArchiveReader(str(executable))
    pyz = archive.open_embedded_archive(next(name for name in archive.toc if name.lower().endswith('.pyz')))
    if provider == 'doubao':
        module, variable = 'ai_tool.doubao_ai_production', 'ARK_API_KEY'
        base_url, model = 'https://ark.cn-beijing.volces.com/api/v3', 'doubao-seed-2-1-lite-260915'
    else:
        module, variable = 'ai_tool.ai_text_production', 'code'
        base_url, model = 'https://api.deepseek.com', 'deepseek-flash'
    instructions = list(dis.get_instructions(pyz.extract(module)))
    candidates = [
        op.argval for index, op in enumerate(instructions[:-1])
        if op.opname == 'LOAD_CONST' and isinstance(op.argval, str)
        and len(op.argval) >= 20
        and instructions[index + 1].opname in ('STORE_NAME', 'STORE_GLOBAL')
        and instructions[index + 1].argval == variable
    ]
    if not candidates:
        raise RuntimeError('旧版中没有找到对应服务商的密钥')
    return save_ai_config({'api_key': candidates[-1], 'base_url': base_url, 'model': model}, path=destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--provider', choices=('doubao', 'deepseek'), default='doubao')
    args = parser.parse_args()
    try:
        path = import_config(args.legacy_exe, args.output, args.provider)
    except Exception as error:
        # Never dump bytecode, request headers, or credential-bearing values.
        print(f'导入失败：{type(error).__name__}')
        raise SystemExit(1)
    print(f'已导入 {args.provider} 配置：{path}（密钥不显示）')


if __name__ == '__main__':
    main()
