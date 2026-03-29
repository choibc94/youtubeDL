#!/usr/bin/env python3
import os
import sys
import queue
import threading
import platform
import shutil
import subprocess


VENV_DIR = os.path.join(os.path.dirname(__file__), "venv")

# ------------------------------------------------------------
# venv 확인
# ------------------------------------------------------------
def is_venv():
    ensure_ffmpeg()
    return sys.prefix != sys.base_prefix

def get_venv_python():
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")

def is_restricted_env():
    return (
        "ANDROID_ROOT" in os.environ
        or "PREFIX" in os.environ
        or "PYODIDE" in os.environ
        or platform.system() not in ("Linux", "Darwin", "Windows")
    )
# ------------------------------------------------------------
# venv 환경 구성
# ------------------------------------------------------------
def ensure_venv():
    if is_venv():
        return

    # 제한 환경 (iPad 등)
    if is_restricted_env():
        print("[INFO] 제한된 환경 → venv 생략")
        return
    
    print("[INFO] 실행 환경 구성 중...")

    # 1. venv 생성
    if not os.path.exists(VENV_DIR):
        print("[INFO] venv 생성 중...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

    # 2. venv python 경로
    venv_python = get_venv_python()


    try:
        subprocess.check_call(
            [venv_python, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except:
        print("[WARN] pip 없음 → bootstrap 진행")

        try:
            subprocess.check_call([venv_python, "-m", "ensurepip", "--upgrade"])
        except:
            print("[WARN] ensurepip 실패 → get-pip 사용")

            subprocess.check_call([
                venv_python,
                "-c",
                "import urllib.request as u; u.urlretrieve('https://bootstrap.pypa.io/get-pip.py','get-pip.py')"
            ])
            subprocess.check_call([venv_python, "get-pip.py"])

    # 3. pip 업그레이드 + yt-dlp 설치
    print("[INFO] 패키지 설치 중...")
    subprocess.check_call([venv_python, "-m", "pip", "install", "-U", "pip"])
    subprocess.check_call([venv_python, "-m", "pip", "install", "-U", "yt-dlp"])

    # 4. 자기 자신을 venv python으로 재실행
    print("[INFO] 환경 구성 완료. 재실행합니다.\n")
    os.execv(venv_python, [venv_python] + sys.argv)

# ------------------------------------------------------------
# 패키지 설치
# ------------------------------------------------------------
def ensure_python_package(package_name, import_name=None):
    try:
        __import__(import_name or package_name)
        return
    except ImportError:
        print(f"[INFO] {package_name} 설치 시도")

    pip_cmd = [sys.executable, "-m", "pip", "install", "-U", package_name]

    # venv 여부 판단
    in_venv = sys.prefix != sys.base_prefix

    # venv가 아닐 때만 --user 사용
    if not in_venv:
        pip_cmd = [sys.executable, "-m", "pip", "install", "--user", "-U", package_name]

    try:
        subprocess.check_call(pip_cmd)
    except subprocess.CalledProcessError:
        print(f"[WARN] 일반 설치 실패 → --break-system-packages 시도")

        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "--break-system-packages", "-U", package_name
            ])
        except Exception:
            print(f"[ERROR] {package_name} 자동 설치 실패")
            print(f"수동 설치 필요:")
            print(f"  pip install {package_name}")
            sys.exit(1)            

# ------------------------------------------------------------
# 패키지 업데이트
# ------------------------------------------------------------
def update_package(package_name):
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-U", package_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except:
        pass

# ------------------------------------------------------------
# ffmpeg 설치 함수
# ------------------------------------------------------------
def ensure_ffmpeg():
    system = platform.system()

    def is_ffmpeg_exists():
        return shutil.which("ffmpeg") is not None

    if is_ffmpeg_exists():
        return

    print("[INFO] ffmpeg가 설치되어 있지 않습니다. 자동 설치를 시도합니다...")

    try:
        if system == "Darwin":
            # macOS (Homebrew)
            subprocess.check_call(["brew", "install", "ffmpeg"])

        elif system == "Linux":
            if shutil.which("apt"):
                subprocess.check_call(["sudo", "apt", "update"])
                subprocess.check_call(["sudo", "apt", "install", "-y", "ffmpeg"])
            else:
                print("[WARN] 패키지 매니저 없음 → ffmpeg 수동 설치 필요")
                return

        elif system == "Windows":
            print("[ERROR] Windows에서는 자동 설치를 지원하지 않습니다.")
            print("https://ffmpeg.org/download.html 에서 직접 설치하세요.")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] ffmpeg 설치 실패: {e}")
        sys.exit(1)

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
    elif system == "Windows":     # Windows native
        return None
    else:                         # 그 외
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

def detect_volumes():
    system = platform.system()
    volumes = []

    if system == "Darwin":

        try:
            result = subprocess.check_output(["mount"], text=True)

            for line in result.splitlines():

                if not line.startswith("/dev/"):
                    continue

                parts = line.split(" on ")
                if len(parts) < 2:
                    continue

                mount_point = parts[1].split(" (")[0]

                if mount_point.startswith("/Volumes/"):
                    volumes.append(mount_point)

        except Exception:
            pass

    if "ANDROID_ROOT" in os.environ:
        volumes.extend(detect_android_storage())
    
    elif system == "Linux":

        try:
            with open("/proc/mounts") as f:

                for line in f:

                    parts = line.split()
                    device = parts[0]
                    mount_point = parts[1]

                    if not device.startswith("/dev/"):
                        continue

                    # Android 대응 추가
                    if mount_point.startswith("/storage"):
                        volumes.append(mount_point)

                    if mount_point.startswith(("/mnt", "/media", "/run/media")):
                        volumes.append(mount_point)

        except Exception:
            pass

    elif system == "Windows":

        from string import ascii_uppercase
        import os

        for letter in ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                volumes.append(drive)


    return volumes

#Android 다운로드 별도 작업
def detect_android_storage():
    base = "/storage"
    result = []

    if os.path.exists(base):
        for name in os.listdir(base):

            # emulated 제외
            if name == "emulated":
                continue

            path = os.path.join(base, name)

            if os.path.isdir(path):
                free = get_free_space(path)
                result.append((path, free))

    return result


def build_download_paths():

    paths = []
    volumes = detect_volumes()

    for v in volumes:

        # 숨김 볼륨 제외
        if os.path.basename(v).startswith("."):
            continue

        path = os.path.join(v, "Downloads", "Youtube")

        free = get_free_space(v)

        # 용량 조회 불가능하면 제외
        if free is None:
            free = 0

        paths.append((path, free))

    # 홈 디렉토리 기본값
    home_default = os.path.join(os.path.expanduser("~"), "Downloads", "Youtube")
    home_free = get_free_space(os.path.expanduser("~"))

    paths.insert(0, (home_default, home_free))

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
    os.makedirs(download_dir, exist_ok=True)
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

    for idx, (path, free) in enumerate(paths, 1):
        free_str = format_size(free)
        print(f"{idx}. {path} ({free_str} free)")

    custom_index = len(paths) + 1
    print(f"{custom_index}. 직접 입력")

    print("\n번호를 입력하세요 (엔터=기본값): ", end="")
    choice = safe_input().strip()

    if not choice:
        return paths[0][0]

    if choice.isdigit():

        index = int(choice)

        if 1 <= index <= len(paths):
            return paths[index - 1][0]

        if index == custom_index:
            custom = safe_input("다운로드 경로 : ").strip()
            if custom:
                return custom

    print("잘못된 입력입니다. 기본값을 사용합니다.")
    return paths[0][0]

# ------------------------------------------------------------
# 초기화
# ------------------------------------------------------------
def initialize_environment():
    global YoutubeDL

    print("[INFO] 실행 환경 점검 중...")

    if not is_venv():
        print("[ERROR] 현재 Python은 system 환경입니다.")
        print("$ python3 -m venv venv")
        print("$ source venv/bin/activate")
        print(" 다시 실행하세요.")
        sys.exit(1)

    # 1. 설치 보장
    ensure_python_package("yt-dlp", "yt_dlp")

    # 2. 선택적 업데이트 (옵션)
    update_package("yt-dlp")

    # 3. import
    from yt_dlp import YoutubeDL

    # 4. ffmpeg (OS 패키지 : 필요 시 수동 업데이트)
    #ensure_ffmpeg()



def main():

    initialize_environment()

    while True:

        try:

            print("\n===== Youtube Downloader =====\n")

            download_dir = select_download_path()

            url = safe_input("유튜브 URL을 입력하세요: ").strip()

            if not url:
                print("URL이 비어있습니다.")
                continue

            download_video(url, download_dir)

            print("\n유튜브 URL 관련 파일 다운로드 완료\n")

        except KeyboardInterrupt:
            print("\n 작업이 취소되었습니다.")
            print("메인 메뉴로 돌아갑니다.\n")
            continue

if __name__ == "__main__":

    # venv 환경
    ensure_venv()

    main()