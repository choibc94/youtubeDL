## 📱 Galaxy Tab S2 (Termux) 환경에서 yt-dlp 실행 환경 구축 가이드

본 문서는 **Android Galaxy Tab S2**에서 **Termux**를 기반으로 **yt-dlp** 및 Python 다운로드 스크립트를 실행하기 위한 전체 설치 절차를 정리한 기술 문서입니다.

모든 명령은 Termux 터미널 기준입니다.

-----

### 1\. Termux 설치

Google Play 스토어의 Termux는 오래된 버전이므로 반드시 **최신 버전**을 아래에서 받아야 합니다.

  * **공식 설치 URL:**
    `https://f-droid.org/en/packages/com.termux/`

설치 후 **Termux를 실행**합니다.

-----

### 2\. 패키지 업데이트

Termux는 기본적으로 오래된 패키지가 포함되어 있으므로 우선 시스템 패키지를 최신화합니다.

```bash
pkg update
pkg upgrade
```

-----

### 3\. 필수 패키지 설치

**Python**, **FFmpeg**, **OpenSSL**, 기본 툴들을 설치합니다.

```bash
pkg install python ffmpeg openssl wget tar unzip
```

  * **설치 확인:**

<!-- end list -->

```bash
python --version
ffmpeg -version
```

-----

### 4\. Python 환경 구성

#### 4.1. pip 관련 정책 안내

**Termux는 pip를 수동 업그레이드하는 것을 금지합니다.**

따라서 아래 명령은 **절대 실행하면 안 됩니다**:

```bash
pip install --upgrade pip    # 금지
```

> ⚠️ **Termux 내부 환경이 깨지므로 절대 금지됩니다.**

-----

### 5\. yt-dlp 설치

Termux의 pip는 yt-dlp 설치에 문제가 없으며 아래 명령으로 바로 설치 가능합니다.

```bash
pip install yt-dlp
```

  * **버전 확인:**

<!-- end list -->

```bash
yt-dlp --version
```

-----

### 6\. FFmpeg 확인

영상/음성 변환을 위해 **FFmpeg**는 필수이며 Termux 기본 패키지로 설치 가능합니다.

  * **설치 확인:**

<!-- end list -->

```bash
which ffmpeg
which ffprobe
```

둘 다 `/data/data/com.termux/files/usr/bin/` 내에 존재하면 정상입니다.

-----

### 7\. 프로젝트 실행을 위한 작업 디렉토리 구성

예: `youtubeDL` 디렉토리 생성

```bash
mkdir -p ~/youtubeDL
cd ~/youtubeDL
```

GitHub(혹은 PC에서 이동)으로 받은 Python 스크립트를 배치합니다.

-----

### 8\. 가상환경 (venv)은 선택적으로 사용 가능

Termux는 **venv**도 정상 동작합니다.

```bash
python -m venv venv
source venv/bin/activate
```

  * **비활성화:**

<!-- end list -->

```bash
deactivate
```

> **※ 참고:** Termux는 pip를 시스템 레벨에서 보호하기 때문에 venv를 사용해도 **pip 업그레이드는 금지**됩니다.

-----

### 9\. Python 스크립트 실행

프로그램 이름이 `youtube_downloader_cli.py`라고 가정합니다.

```bash
python youtube_downloader_cli.py
```

다운로드 폴더는 입력이 없으면 자동으로 기본 `./download`가 생성됩니다.

-----

### 10\. 문제 발생 시 확인 항목

#### 10.1. FFmpeg 미탐지

yt-dlp는 **PATH**에 FFmpeg가 있어야 합니다.

```bash
echo $PATH
which ffmpeg
```

둘 중 하나라도 정상 출력되면 FFmpeg가 인식된 것입니다.

#### 10.2. pip 업그레이드 오류

Termux 정책이므로 **정상이며 무시**해야 합니다.

#### 10.3. SSL 오류 발생 시

```bash
pkg install openssl
pip install certifi
```

-----

### 부록: 설치 전체 명령 모음

아래 명령을 순서대로 실행하면 모든 환경이 자동 준비됩니다.

```bash
pkg update
pkg upgrade
pkg install python ffmpeg openssl wget tar unzip
pip install yt-dlp
mkdir -p ~/youtubeDL
cd ~/youtubeDL
```

  * **필요 시 (가상환경):**

<!-- end list -->

```bash
python -m venv venv
source venv/bin/activate
```

-----