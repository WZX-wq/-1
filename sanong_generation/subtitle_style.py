"""ASS subtitle helpers used by the standalone three-agriculture flow."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path


def _ass_color(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError("颜色代码必须是6位十六进制值")
    return f"&H{value[4:6]}{value[2:4]}{value[0:2]}"


def _format_time(value: str) -> str:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    whole_seconds, fraction = seconds.split(".")
    return f"{hours}:{minutes}:{whole_seconds}.{fraction[:2]}"


def _parse_srt(path: Path) -> list[dict[str, str]]:
    content = path.read_text(encoding="utf-8")
    entries = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start, end = (_format_time(item.strip()) for item in lines[1].split("-->", 1))
        entries.append({"start": start, "end": end, "text": "\n".join(lines[2:])})
    if not entries:
        raise ValueError(f"字幕文件没有有效内容: {path}")
    return entries


def _seconds(ass_time: str) -> float:
    hours, minutes, seconds = ass_time.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def convert_srt_to_ass(srt_path: Path, output_path: Path, style: dict) -> Path:
    entries = _parse_srt(Path(srt_path))
    header = f"""[Script Info]
Title: Default Aegisub file
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['fontFamily']},12,{_ass_color(style['fontColor'])},{_ass_color(style['fontColor'])},{_ass_color(style['borderColor'])},{_ass_color(style['shadowColor'])},{style['fontBold']},{style['fontItalic']},{style['fontUnderline']},0,100,100,0,0,1,{style['fontBorderSize']},{style['shadowDepth']},2,10,10,70,65001

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for entry in entries:
        text = entry["text"].replace("A:", "").replace("B:", "")
        if len(text) > 12:
            text = r"\N".join(text[index:index + 12] for index in range(0, len(text), 12))
        events.append(
            f"Dialogue: 0,{entry['start']},{entry['end']},Default,,0,0,0,,{text}"
        )
    output_path = Path(output_path)
    output_path.write_text(header + "\n".join(events), encoding="utf-8")
    return output_path


def remove_first_dialogue_text(path: Path) -> None:
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    removed = False
    for index, line in enumerate(lines):
        if line.startswith("Dialogue:") and not removed:
            parts = line.rstrip("\r\n").split(",", 9)
            parts[-1] = ""
            lines[index] = ",".join(parts) + "\n"
            removed = True
    with tempfile.NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-8", dir=path.parent
    ) as temporary:
        temporary.writelines(lines)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _title_header(style: dict) -> str:
    return f"""[Script Info]
Title: Default Aegisub file
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['fontFamily']},{style['fontSize']},{_ass_color(style['fontColor'])},{_ass_color(style['fontColor'])},{_ass_color(style['borderColor'])},{_ass_color(style['shadowColor'])},{style['fontBold']},{style['fontItalic']},{style['fontUnderline']},0,100,100,{style['titleLineSpace']},0,1,{style['fontBorderSize']},{style['shadowDepth']},2,10,10,{style['titleSpace']},65001
Style: VerticalPro,@{style['fontFamily']},{style['fontSize']},{_ass_color(style['fontColor'])},{_ass_color(style['fontColor'])},{_ass_color(style['borderColor'])},{_ass_color(style['shadowColor'])},{style['fontBold']},{style['fontItalic']},{style['fontUnderline']},0,100,100,{style['titleLineSpace']},0,1,{style['fontBorderSize']},{style['shadowDepth']},2,10,10,{style['titleSpace']},65001

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _title_effect(text: str, style: dict) -> str:
    alignments = (2, 7, 4, 1, 9, 6, 3)
    prefix = (
        f"{{\\fs{style['fontSize']}"
        f"\\c&H{_ass_color(style['fontColor'])[2:]}&"
        f"\\3c&H{_ass_color(style['borderColor'])[2:]}&"
        f"\\an{alignments[style['align']]}"
        f"\\pos({style['x']},{style['y']})\\Y{style['VSpace']}"
    )
    effect = style["fontScroll"]
    if effect == 0:
        return prefix + r"\fscx20\fscy20\t(0,200,\fscx100\fscy100)}" + text + r"\N"
    if effect == 1:
        return prefix + r"\fr0\t(0,3000,\fr360)}" + text + r"\N"
    if effect == 2:
        return prefix + r"\c&H0000FF&\t(0,2500,\c&HFF0000&)}" + text + r"\N"
    return prefix + r"\blur5\fad(80,0)\t(40,80,\blur0)}" + text + r"\N"


def create_opening_title(
    settings: dict,
    screen: int,
    title: str,
    output_path: Path,
    srt_path: Path,
) -> float:
    del screen  # Existing type-6 title styling is selected by title_type, not screen.
    entries = _parse_srt(Path(srt_path))
    end_time = entries[0]["end"]
    pic_time = max(0.0, _seconds(end_time) - 0.1)
    title_parts = title.split("|")
    vertical = settings.get("title_type", {}).get("type", 0) != 0
    events = []
    x = settings["title_set"]["titleSpace"]
    for index, part in enumerate(title_parts):
        if not part:
            continue
        effect = _title_effect(
            part, settings[f"part_title_part_{index}_set"]
        )
        if vertical:
            effect = f"{{\\frz-90}}{{\\an5\\pos({x + 100},140)}}{effect}"
            style_name = "VerticalPro"
            x += 100
        else:
            style_name = "Default"
        events.append(
            f"Dialogue: 0,0,{end_time},{style_name},,0,0,0,,{effect}"
        )
    output_path = Path(output_path)
    output_path.write_text(
        _title_header(settings["title_set"]) + "\n".join(events), encoding="utf-8"
    )
    return pic_time
