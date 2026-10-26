"""Qt-free media operations shared by the GUI and standalone runner."""

from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Optional, Sequence

from ffmpeg_tool.add_music_tool import add_bgm_to_video
from ffmpeg_tool.subtitles_audio_tool import (
    add_audio_and_subtitles_to_part,
    choose_random_audio_voice,
    produce_audio_and_subtitles_to_path,
)
from ffmpeg_tool.video_concat_tool import addCover, concatenate_videos_in_segments

from .errors import (
    MEMORY_EXHAUSTION_MESSAGE,
    MediaGenerationError,
    MemoryExhaustionError,
    is_memory_exhaustion,
)


@dataclass(frozen=True)
class AudioSubtitle:
    audio_path: Path
    srt_path: Path


SegmentResult = tuple[int, str, bool, str]
SegmentProcessor = Callable[[tuple[int, str, str, str, Optional[str]]], SegmentResult]
ProgressCallback = Callable[[int, int, str], None]


def _run_awaitable(value, timeout: float) -> None:
    if not inspect.isawaitable(value):
        return

    async def wait_for_value(awaitable: Awaitable[object]) -> None:
        await asyncio.wait_for(awaitable, timeout=timeout)

    asyncio.run(wait_for_value(value))


def generate_audio_subtitles(
    texts: Sequence[str],
    audio_settings: dict,
    output_dir: Path,
    progress: Callable[[str], None] | None = None,
) -> list[AudioSubtitle]:
    """Generate one narration and subtitle file for every copy segment."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    api_type = audio_settings["api_type"]
    audio_settings = choose_random_audio_voice(audio_settings)
    generated: list[AudioSubtitle] = []

    def cleanup_partial(index: int) -> None:
        paths = [
            item.audio_path for item in generated
        ] + [item.srt_path for item in generated]
        paths.extend(
            (
                output_dir / f"temp_final_audio{index}.mp3",
                output_dir / f"temp_subtitle{index}.srt",
            )
        )
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    for index, text in enumerate(texts):
        try:
            asyncio.run(
                produce_audio_and_subtitles_to_path(
                    api_type,
                    str(output_dir),
                    text,
                    index,
                    audio_settings,
                )
            )
        except Exception as error:
            cleanup_partial(index)
            raise MediaGenerationError(
                f"第 {index + 1} 段音频字幕生成失败: {error}"
            ) from error

        audio_path = output_dir / f"temp_final_audio{index}.mp3"
        srt_path = output_dir / f"temp_subtitle{index}.srt"
        missing = [path for path in (audio_path, srt_path) if not path.is_file()]
        if missing:
            cleanup_partial(index)
            raise MediaGenerationError(
                f"第 {index + 1} 段音频字幕文件未生成: {', '.join(map(str, missing))}"
            )
        generated.append(AudioSubtitle(audio_path, srt_path))
        if progress:
            progress(
                f"正在处理文案中，目前已经处理了{index + 1}片段，生成了音频字幕"
            )

    return generated


def _default_segment_processor(
    args: tuple[int, str, str, str, Optional[str]],
) -> SegmentResult:
    index, video_path, audio_path, ass_path, title_ass_path = args
    try:
        result = asyncio.run(
            asyncio.wait_for(
                add_audio_and_subtitles_to_part(
                    video_path, audio_path, ass_path, title_ass_path
                ),
                timeout=180,
            )
        )
        success = bool(result) and Path(result).is_file()
        error = "" if success else f"片段 {index + 1}: 处理失败"
        return index, str(result or ""), success, error
    except asyncio.TimeoutError:
        return index, "", False, f"片段 {index + 1}: 处理超时"
    except Exception as error:
        if is_memory_exhaustion(error):
            raise MemoryExhaustionError(MEMORY_EXHAUSTION_MESSAGE) from error
        return index, "", False, f"片段 {index + 1}: {error}"


def _remove_generated_files(paths: Sequence[str], source_paths: Sequence[str]) -> None:
    sources = {os.path.abspath(path) for path in source_paths}
    for item in paths:
        path = Path(item)
        if os.path.abspath(str(path)) in sources or not path.exists():
            continue
        try:
            path.unlink()
        except OSError:
            pass


def compose_video_segments(
    video_paths: Sequence[Path],
    audio_paths: Sequence[Path],
    ass_paths: Sequence[Path],
    title_ass_paths: Sequence[Path],
    output_path: Path,
    transition: dict,
    pic_time: float,
    max_workers: int = 4,
    progress: ProgressCallback | None = None,
    *,
    segment_processor: SegmentProcessor | None = None,
    merge_callback: Callable[[list[str], str], object] | None = None,
    cover_callback: Callable[[str, float], object] | None = None,
) -> Path:
    """Compose all segments atomically; incomplete videos are never accepted."""
    videos = [str(path) for path in video_paths]
    audios = [str(path) for path in audio_paths]
    subtitles = [str(path) for path in ass_paths]
    title_subtitles = [str(path) for path in title_ass_paths]
    output_path = Path(output_path)

    if not videos:
        raise MediaGenerationError("没有可合成的视频片段")
    if len(audios) != len(videos) or len(subtitles) != len(videos):
        raise MediaGenerationError("视频、音频和字幕片段数量不一致")

    processor = segment_processor or _default_segment_processor
    process_args = [
        (
            index,
            video_path,
            audios[index],
            subtitles[index],
            title_subtitles[index] if index < len(title_subtitles) else None,
        )
        for index, video_path in enumerate(videos)
    ]
    results: list[SegmentResult] = []
    failed: list[str] = []
    completed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(processor, args): args[0] for args in process_args
        }
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as error:
                if is_memory_exhaustion(error):
                    raise MemoryExhaustionError(MEMORY_EXHAUSTION_MESSAGE) from error
                failed.append(f"片段 {index + 1}: 线程异常 - {error}")
            completed += 1
            if progress:
                progress(completed, len(videos), f"处理进度: {completed}/{len(videos)}")

    results.sort(key=lambda item: item[0])
    processed = [path for _, path, success, _ in results if success]
    failed.extend(error for _, _, success, error in results if not success and error)
    if failed or len(processed) != len(videos):
        _remove_generated_files(processed, videos)
        details = "; ".join(failed) or "处理结果数量不完整"
        raise MediaGenerationError(
            f"视频片段处理不完整（成功 {len(processed)}/{len(videos)}）：{details}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merge_path = output_path.parent / (
        f".{output_path.stem}.{uuid.uuid4().hex}.merge.mp4"
    )

    def default_merge(parts: list[str], destination: str) -> None:
        concatenate_videos_in_segments(
            parts,
            destination,
            str(transition["transitionNum"]),
            transition["transitionTime"],
        )

    def default_cover(source: str, cover_time: float) -> None:
        addCover(source, str(output_path), cover_time)

    try:
        if merge_path.exists():
            merge_path.unlink()
        _run_awaitable(
            (merge_callback or default_merge)(processed, str(merge_path)), 600
        )
        _run_awaitable(
            (cover_callback or default_cover)(str(merge_path), pic_time - 0.8), 300
        )
        if not output_path.is_file():
            raise MediaGenerationError(f"最终视频文件未生成: {output_path}")
        return output_path
    except asyncio.TimeoutError as error:
        raise MediaGenerationError("视频合并超时") from error
    except Exception as error:
        if is_memory_exhaustion(error):
            raise MemoryExhaustionError(MEMORY_EXHAUSTION_MESSAGE) from error
        if isinstance(error, MediaGenerationError):
            raise
        raise MediaGenerationError(f"视频合并失败: {error}") from error
    finally:
        _remove_generated_files(processed, videos)
        try:
            merge_path.unlink(missing_ok=True)
        except OSError:
            pass


def add_background_music(
    video_path: Path,
    music_path: Path,
    video_volume: int,
    music_volume: int,
    output_path: Path,
) -> Path:
    """Mix background music and return the verified output path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        add_bgm_to_video(
            str(video_path),
            str(music_path),
            video_volume,
            music_volume,
            str(output_path),
        )
    except Exception as error:
        if is_memory_exhaustion(error):
            raise MemoryExhaustionError(MEMORY_EXHAUSTION_MESSAGE) from error
        raise MediaGenerationError(f"背景音乐处理失败: {error}") from error
    if not output_path.is_file():
        raise MediaGenerationError(f"背景音乐处理后未生成文件: {output_path}")
    return output_path
