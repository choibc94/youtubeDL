#!/usr/bin/env python3
import os
import sys
import queue
import threading
import platform
import shutil
from yt_dlp import YoutubeDL

# ------------------------------------------------------------
# 기본 환경 설정
# ------------------------------------------------------------
FFMPEG_PATH = "/opt/homebrew/bin"  # Homebrew ffmpeg 경로(macOS 기준)

def detect_ffmpeg_path():
    system = platform.system()

    if system == "Darwin":        # macOS
        return "/opt/homebrew/bin"
    elif system == "Linux":       # WSL 포함
        return "/usr/bin"
    else:                         # Windows native
        return None               # PATH 사용

FFMPEG_PATH = detect_ffmpeg_path()

# ydl_base_opts
# ffmpeg 경로 강제 지정
# macOS <-> VSCode 환경 차이 무시
# 최신 component 사용
# SSL 검증 우회
# 로그 최소화
ydl_base_opts = {
    "ignoreerrors": True,               # 오류발생 시 계속 진행(맴버십 전용, 삭제, 지역 제한, 접근 권한 부족, 네워크 일시 오류등이 발생해도 스킵하고 다음 영상으로 진행)
    "continue_dl": True,                # 일부 분할 다운로드된 파일이 있을 경우, 해당 파일을 이어받기 위한 옵션
    "retries": 3,                       # 네트워크 오류(http 오류, 연결 timeout등)발생 시 전체 요청을 재시도하는 횟수 지정
    "fragment_retries": 3,              # HLS/MPEG-DASH와 같은 분할 다운로드(조각 단위 다운로드) 중 개별 조각 다운로드가 실패하면 해당 조각을 몇 번까지 재시도할지를 지정
    "quiet": False,                     # 로그 최소화
    "no_warnings": True,                # 경고 제거
    "ffmpeg_location": FFMPEG_PATH,     # ffmpeg/ffprobe가 단일 경로 또는 디렉토리여도 정상 인식(존재하면 직접 사용, 미존재시 PATH에서 찾음)
    "prefer_ffmpeg": True,              # ffmpeg이 여러 위치에 있어도 지정한 경로를 우선 사용하도록 강제함.
    "nocheckcertificate": True,         # SSL 검증 비활성화
    "remote_components": "ejs:github",  # 최신 extractor component를 GitHub에서 가져오도록 지정
    "merge_output_format": "mp4",       # ffmpeg 병합의 명시적 포맷 지정
    #"cookiefile": "cookies.txt",       # 실제 멤버십 계정이 있고, 해당 콘텐츠 접근 권한이 있는 경우에만
}

# ------------------------------------------------------------
# 유틸 함수
# ------------------------------------------------------------

def print_header(title):
    print("\n" + "=" * 70)
    print(f"[ {title} ]")
    print("=" * 70)

# 볼륨 감지 및 다운로드 경로 생성
def detect_volumes():
    system = platform.system()
    volumes = []

    if system == "Darwin":  # macOS
        base = "/Volumes"
        if os.path.exists(base):
            for v in os.listdir(base):
                volumes.append(os.path.join(base, v))

    elif system == "Linux":
        bases = ["/mnt", "/media", "/run/media"]
        for base in bases:
            if os.path.exists(base):
                for root, dirs, _ in os.walk(base):
                    for d in dirs:
                        volumes.append(os.path.join(root, d))
                    break

    elif system == "Windows":
        from string import ascii_uppercase
        for letter in ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                volumes.append(drive)

    return volumes


def build_download_paths():
    paths = []

    volumes = detect_volumes()

    for v in volumes:
        path = os.path.join(v, "Downloads", "Youtube")
        paths.append(path)

    # 홈 디렉토리 기본값 추가
    home_default = os.path.join(os.path.expanduser("~"), "Downloads", "Youtube")
    paths.insert(0, home_default)

    return paths


def safe_input(prompt=""):
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting.")
        sys.exit(0)


def get_free_space(path):
    try:
        total, used, free = shutil.disk_usage(path)
        return free
    except Exception:
        return None


def format_size(size):
    if size is None:
        return "N/A"

    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} PB"    
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
# 다운로드 저장 위치 선택
# ------------------------------------------------------------
def select_download_path():

    paths = build_download_paths()

    print("\n다운로드 저장 위치를 선택하세요:\n")

    for idx, path in enumerate(paths):
        free = get_free_space(path)
        free_str = format_size(free)
        print(f"{idx}. {path} ({free_str} free)")

    custom_index = len(paths) + 1
    print(f"{custom_index}. 직접 입력")

    print("\n번호를 입력하세요 (엔터=기본값): ", end="")
    choice = safe_input().strip()

    if not choice:
        return paths[0]

    if choice.isdigit():

        index = int(choice)

        if 1 <= index <= len(paths):
            return paths[index - 1]

        if index == custom_index:
            custom = safe_input("다운로드 경로 : ").strip()
            if custom:
                return custom

    print("잘못된 입력입니다. 기본값을 사용합니다.")
    return paths[0]


# ------------------------------------------------------------
# CLI 입력
# ------------------------------------------------------------

def main():
    print_header("YouTube Downloader CLI")

    download_dir = select_download_path()
    print(f"\n선택된 다운로드 경로: {download_dir}\n")

    os.makedirs(download_dir, exist_ok=True)

    url = safe_input("유튜브 URL을 입력하세요: ").strip()

    # -------------------------------
    # 🔹 다운로드 방식 선택 추가
    # -------------------------------
    print("\n다운로드 방식을 선택하세요:")
    print("1. 자동 (최적 영상+오디오)")
    print("2. 수동 (포맷 직접 선택)")
    print("\n번호 입력 (엔터=자동): ", end="")

    mode = safe_input().strip()

    if not mode or mode == "1":
        download_mode = "auto"
    elif mode == "2":
        download_mode = "manual"
    else:
        print("잘못된 입력입니다. 자동 모드로 진행합니다.")
        download_mode = "auto"

    # -------------------------------
    # 플레이리스트 자동 감지
    # -------------------------------
    if "list=" in url.lower():
        print("플레이리스트 URL 감지됨.")
        conv = safe_input("변환 옵션 (mp3/mp4/없음): ").strip()
        download_playlist(url, download_dir, convert_to=(conv if conv else None))
        return

    # -------------------------------
    # 🔹 자동 모드
    # -------------------------------
    if download_mode == "auto":
        print("\n자동 모드: 최적 품질로 다운로드합니다.")
        conv = safe_input("변환 옵션 (mp3/mp4/없음): ").strip()
        convert_to = conv if conv else None

        download_video(url, download_dir, convert_to=convert_to)
        return

    # -------------------------------
    # 🔹 수동 모드 (기존 로직 유지)
    # -------------------------------
    info = fetch_video_info(url)

    title = info.get("title")
    print(f"\n영상 제목: {title}")

    formats = list_formats(info)

    video_fmt = safe_input("\n선택할 VIDEO 포맷 ID (없으면 Enter): ").strip() or None
    audio_fmt = safe_input("선택할 AUDIO 포맷 ID (없으면 Enter): ").strip() or None
    conv = safe_input("변환 옵션 (mp3/mp4/없음): ").strip()
    convert_to = conv if conv else None

    download_video(url, download_dir, video_fmt, audio_fmt, convert_to)

def main():

    while True:

        try:

            print("\n===== Youtube Downloader =====\n")

            download_dir = select_download_path()

            url = safe_input("유튜브 URL을 입력하세요: ").strip()

            if not url:
                print("URL이 비어있습니다.")
                continue

            download_video(url, download_dir)

            print("\n다운로드 완료\n")

        except KeyboardInterrupt:
            print("\n⛔ 작업이 취소되었습니다.")
            print("메인 메뉴로 돌아갑니다.\n")
            continue

if __name__ == "__main__":
    main()