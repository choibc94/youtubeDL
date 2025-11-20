#!/usr/bin/env python3
import os
import sys
import queue
import threading
from yt_dlp import YoutubeDL

# ------------------------------------------------------------
# 기본 환경 설정
# ------------------------------------------------------------
FFMPEG_PATH = "/opt/homebrew/bin"  # Homebrew ffmpeg 경로(macOS 기준)

# ydl_base_opts
# ffmpeg 경로 강제 지정
# macOS <-> VSCode 환경 차이 무시
# 최신 component 사용
# SSL 검증 우회
# 로그 최소화
ydl_base_opts = {
    "quiet": True,                      # 로그 최소화
    "no_warnings": True,                # 경고 제거
    "ffmpeg_location": FFMPEG_PATH,     # ffmpeg/ffprobe가 단일 경로 또는 디렉토리여도 정상 인식
    "prefer_ffmpeg": True,              # ffmpeg이 여러 위치에 있어도 지정한 경로를 우선 사용하도록 강제함.
    "nocheckcertificate": True,         # SSL 검증 비활성화
    "remote_components": "ejs:github",  # 최신 extractor component를 GitHub에서 가져오도록 지정
    "merge_output_format": "mp4",       # ffmpeg 병합의 명시적 포맷 지정
}

# ------------------------------------------------------------
# 유틸 함수
# ------------------------------------------------------------

def print_header(title):
    print("\n" + "=" * 70)
    print(f"[ {title} ]")
    print("=" * 70)

# ------------------------------------------------------------
#  유튜브 정보 조회
# ------------------------------------------------------------

def fetch_video_info(url):
    opts = {
        **ydl_base_opts,
        "dump_single_json": True,
        "extract_flat": False,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return info

def list_formats(info):
    RESET = "\033[0m"
    GREEN = "\033[92m"     # audio
    CYAN = "\033[96m"      # video
    YELLOW = "\033[93m"    # storyboard or other

    formats = info.get("formats", [])
    if not formats:
        print("포맷 정보를 찾을 수 없습니다.")
        return []

    print("\n=== 사용 가능한 포맷 목록 ===")

    # 컬럼 정의 (고정폭 정렬)
    header = (
        f"{'ID':>6} | {'EXT':<5} | {'RESOLUTION':<12} | {'FPS':>5} | {'CH':>3} | "
        f"{'FILESIZE(MiB)':>14} | {'TBR(k)':>8} | {'PROTO':<6} | "
        f"{'VCODEC':<12} | {'VBR(k)':>8} | {'ACODEC':<10} | {'ABR(k)':>6} | "
        f"{'ASR(k)':>6} | {'MORE':<10} | {'INFO'}"
    )
    print(header)
    print("-" * len(header))

    def to_k(val):
        if val is None:
            return "-"
        return f"{round(val)}k"

    # ASR 전용 변환
    def asr_to_k(val):
        if val is None:
            return "-"
        return f"{round(val / 1000)}k"
    
    for f in formats:
        # Resolution
        width = f.get("width")
        height = f.get("height")
        resolution = f"{width}x{height}" if width and height else "audio only"

        # FPS (정수 반올림)
        fps = f.get("fps")
        if fps is not None:
            fps = int(round(fps))
        else:
            fps = "-"

        # Channels
        ch = f.get("audio_channels") or "-"

        # File Size → MiB
        size = f.get("filesize") or f.get("filesize_approx")
        if size:
            filesize_mib = f"{round(size / (1024 * 1024), 2)} MiB"
        else:
            filesize_mib = "-"

        # Bitrates
        tbr = to_k(f.get("tbr"))
        vbr = to_k(f.get("vbr"))
        abr = to_k(f.get("abr"))
        asr = asr_to_k(f.get("asr")) or "-"

        # Protocol & Codec 정보
        proto = f.get("protocol") or "-"
        vcodec = f.get("vcodec") or "-"
        acodec = f.get("acodec") or "-"

        # More / Info
        more = f.get("format_note") or "-"
        info_text = f.get("format") or "-"

        # ===== 색상 결정 로직 =====
        if "storyboard" in more or (f.get("ext") == "mhtml"):
            color = YELLOW                # Storyboard
        elif resolution == "audio only":
            color = GREEN                 # Audio Only
        else:
            color = CYAN                  # Video


        print(
            color +
            f"{f.get('format_id', '-'):>6} | "
            f"{(f.get('ext') or '-'):5} | "
            f"{resolution:<12} | "
            f"{str(fps):>5} | "
            f"{str(ch):>3} | "
            f"{filesize_mib:>14} | "
            f"{str(tbr):>8} | "
            f"{proto:<6} | "
            f"{vcodec:<12} | "
            f"{str(vbr):>8} | "
            f"{acodec:<10} | "
            f"{str(abr):>6} | "
            f"{str(asr):>6} | "
            f"{more:<10} | "
            f"{info_text}"
            + RESET
        )

    return formats

# ------------------------------------------------------------
#  다운로드 처리
# ------------------------------------------------------------

def build_download_opts(download_dir, video_fmt=None, audio_fmt=None, convert_to=None):
    opts = {
        **ydl_base_opts,
        "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
    }

    # 특정 포맷 선택
    if video_fmt or audio_fmt:
        if audio_fmt:
            fmt = f"{video_fmt}+{audio_fmt}" if video_fmt else audio_fmt
        else:
            fmt = video_fmt
        opts["format"] = fmt
    else:
        # 자동 best 매핑
        opts["format"] = "bv*+ba/best"

    # 변환 옵션 (mp3/mp4)
    if convert_to == "mp3":
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
        ]
    elif convert_to == "mp4":
        opts["postprocessors"] = [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
        ]

    return opts

def progress_hook(d):
    if d["status"] == "downloading":
        p = d.get("downloaded_bytes", 0)
        t = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
        percent = (p / t) * 100
        sys.stdout.write(f"\r다운로드 중... {percent:5.1f}%")
        sys.stdout.flush()
    elif d["status"] == "finished":
        print("\n병합 및 후처리 중...")

def download_video(url, download_dir, video_fmt=None, audio_fmt=None, convert_to=None):
    print_header(f"다운로드 시작: {url}")

    opts = build_download_opts(download_dir, video_fmt, audio_fmt, convert_to)

    with YoutubeDL(opts) as ydl:
        ydl.download([url])

    print("\n다운로드 완료.")

# ------------------------------------------------------------
# 플레이리스트 전체 다운로드
# ------------------------------------------------------------

def download_playlist(url, download_dir, convert_to=None):
    print_header("플레이리스트 전체 다운로드 시작")

    opts = {
        **ydl_base_opts,
        "outtmpl": os.path.join(download_dir, "%(playlist_title)s/%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "format": "bv*+ba/best",
    }

    if convert_to == "mp3":
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
        ]

    with YoutubeDL(opts) as ydl:
        ydl.download([url])

    print("\n플레이리스트 다운로드 완료.")

# ------------------------------------------------------------
# 멀티 다운로드 큐
# ------------------------------------------------------------

def worker_download(q, download_dir):
    while True:
        try:
            task = q.get_nowait()
        except queue.Empty:
            return

        url = task["url"]
        convert = task["convert"]

        download_video(url, download_dir, convert_to=convert)
        q.task_done()

def process_download_queue(tasks, download_dir, threads=3):
    print_header("멀티 다운로드 큐 실행")
    q = queue.Queue()

    for t in tasks:
        q.put(t)

    for _ in range(threads):
        th = threading.Thread(target=worker_download, args=(q, download_dir))
        th.daemon = True
        th.start()

    q.join()
    print("모든 다운로드가 완료되었습니다.")

# ------------------------------------------------------------
# CLI 입력
# ------------------------------------------------------------

def main():
    print_header("YouTube Downloader CLI")

    download_dir = input("다운로드 저장 위치를 입력하세요 (미입력='./download'): ").strip()

    # 다운로드 경로 기본값 + 유효성 검사
    if not download_dir:
        download_dir = "./download"

    os.makedirs(download_dir, exist_ok=True)

    url = input("유튜브 URL을 입력하세요: ").strip()

    # 플레이리스트 자동 감지
    if "playlist" in url.lower():
        print("플레이리스트 URL 감지됨.")
        conv = input("변환 옵션 (mp3/mp4/없음): ").strip()
        download_playlist(url, download_dir, convert_to=(conv if conv else None))
        return

    # 단일 영상 정보 조회
    info = fetch_video_info(url)

    title = info.get("title")
    print(f"\n영상 제목: {title}")

    formats = list_formats(info)

    # 사용자가 포맷 선택
    video_fmt = input("\n선택할 VIDEO 포맷 ID (없으면 Enter): ").strip() or None
    audio_fmt = input("선택할 AUDIO 포맷 ID (없으면 Enter): ").strip() or None
    conv = input("변환 옵션 (mp3/mp4/없음): ").strip()
    convert_to = conv if conv else None

    download_video(url, download_dir, video_fmt, audio_fmt, convert_to)

if __name__ == "__main__":
    main()
