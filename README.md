
---

# YouTube Downloader 사용자 가이드

본 프로그램은 `yt-dlp` 기반의 YouTube 다운로드 CLI 도구입니다.
영상 및 오디오를 원하는 형식으로 선택 다운로드할 수 있습니다.

---

# 1. 설치 방법

---

# 1.1 Python 설치

Python 3.10 이상 권장
(최신 `yt-dlp`는 3.9 지원 종료)

설치 확인:

```bash
python3 --version
```

---

## ■ macOS

### 1) Homebrew 설치 여부 확인

```bash
brew --version
```

### 2) Python 설치

```bash
brew install python
```

설치 확인:

```bash
python3 --version
```

---

## ■ Linux (Ubuntu / Debian 계열)

```bash
sudo apt update
sudo apt install python3 python3-pip
```

설치 확인:

```bash
python3 --version
```

---

## ■ Linux (Alpine / iSH 환경)

```bash
apk update
apk add python3 py3-pip
```

설치 확인:

```bash
python3 --version
```

※ iSH 환경은 Python 버전이 낮을 수 있으므로 3.10 이상인지 반드시 확인

---

# 1.2 가상환경 사용 (권장)

## macOS / Linux 공통

```bash
python3 -m venv venv
source venv/bin/activate
```

확인:

```bash
which python
```

가상환경 경로가 출력되어야 정상

---

# 1.3 필수 패키지 설치

## macOS / Linux 공통

```bash
pip install --upgrade pip
pip install yt-dlp
```

업데이트 확인:

```bash
yt-dlp -U
```

---

# 1.4 ffmpeg 설치 (필수)

영상 병합 및 mp3 변환에 필요합니다.

---

## ■ macOS

```bash
brew install ffmpeg
```

확인:

```bash
ffmpeg -version
```

Homebrew 기본 경로:

```
/opt/homebrew/bin
```

Intel Mac의 경우:

```
/usr/local/bin
```

---

## ■ Linux (Ubuntu / Debian)

```bash
sudo apt install ffmpeg
```

확인:

```bash
ffmpeg -version
```

---

## ■ Linux (Alpine / iSH)

```bash
apk add ffmpeg
```

확인:

```bash
ffmpeg -version
```

---

# 2. 실행 방법

## macOS / Linux 공통

```bash
python3 youtube_downloader_cli.py
```

가상환경 사용 시:

```bash
source venv/bin/activate
python youtube_downloader_cli.py
```

---

# 3. 기본 사용 절차

프로그램 실행 후 아래 순서로 진행됩니다.

---

## 3.1 다운로드 저장 경로 입력

```
다운로드 저장 위치를 입력하세요 (미입력='./download'):
```

* 입력하지 않으면 기본 경로 사용
* 입력한 경로가 없으면 자동 생성

### macOS 예시 경로

```
/Users/사용자명/Downloads
/Volumes/외장디스크명/temp
```

### Linux 예시 경로

```
/home/사용자명/Downloads
/mnt/storage/temp
```

---

## 3.2 YouTube URL 입력

```
유튜브 URL을 입력하세요:
```

* 단일 영상 URL
* 플레이리스트 URL 모두 가능

---

# 4. 플레이리스트 다운로드

URL에 `list=` 파라미터가 포함되면 자동 감지됩니다.

```
플레이리스트 URL 감지됨.
변환 옵션 (mp3/mp4/없음):
```

| 입력값 | 설명           |
| --- | ------------ |
| mp3 | 모든 영상 mp3 변환 |
| mp4 | mp4 형식 변환    |
| 없음  | 원본 형식 유지     |

저장 구조:

```
[저장경로]/플레이리스트명/영상파일
```

---

# 5. 단일 영상 다운로드

---

## 5.1 포맷 목록 출력

출력 예:

```
ID | EXT | RESOLUTION | FPS | FILESIZE | VCODEC | ACODEC
```

---

## 5.2 Video 포맷 선택

```
VIDEO 포맷 ID 선택 (엔터=자동 최고화질):
```

---

## 5.3 Audio 포맷 선택

```
AUDIO 포맷 ID 선택 (엔터=자동 최고음질):
```

---

## 5.4 변환 옵션 선택

```
변환 옵션 (mp3/mp4/없음):
```

| 옵션  | 결과              |
| --- | --------------- |
| mp3 | 오디오 추출 후 mp3 변환 |
| mp4 | mp4 컨테이너로 변환    |
| 없음  | 원본 유지           |

---

# 6. 다운로드 동작 방식

내부 포맷 전략:

```
bv*+ba/best
```

의미:

* 최고 Video 스트림
* 최고 Audio 스트림
* 병합 후 출력
* 실패 시 best 단일 스트림

---

# 7. 다운로드 진행 상태

* 진행률 (%)
* 다운로드 속도
* 남은 시간
* 병합 처리 상태

---

# 8. 오류 처리 정책

* 네트워크 재시도 3회
* 조각 다운로드 재시도
* 중단 파일 이어받기
* 일부 영상 오류 발생 시 자동 스킵

---

# 9. 멤버십 / 로그인 영상 다운로드

쿠키 파일 사용 가능:

```
cookies.txt
```

프로그램 설정에서 경로 지정 필요.

---

# 10. 저장 파일 형식

## 단일 영상

```
영상제목.확장자
```

## 플레이리스트

```
플레이리스트명/영상제목.확장자
```

---

# 11. 자주 묻는 질문

### Q1. 포맷이 몇 개 안 나옵니다.

* yt-dlp 버전 문제
* 로그인 필요 영상
* 네트워크 차단
* Python 버전 문제 (3.10 이상 필요)

확인:

```bash
yt-dlp -U
```

---

### Q2. mp3 변환이 안 됩니다.

* ffmpeg 설치 여부 확인
* PATH 등록 확인

macOS:

```bash
echo $PATH
```

Linux:

```bash
echo $PATH
```

---

### Q3. iSH에서 오류가 발생합니다.

* Python 3.10 이상인지 확인
* Alpine 패키지 최신화
* 최신 yt-dlp 재설치

---

# 12. 사용 시 주의사항

* 저작권 보호 콘텐츠 무단 배포 금지
* 상업적 사용 시 법적 책임 발생 가능
* YouTube 이용 약관 준수 필요

---

# 13. 권장 운영 방식

### macOS 권장

* Homebrew 기반 관리
* 가상환경 사용
* 정기적 `brew upgrade`

### Linux 권장

* 서버 환경에서는 별도 사용자 계정으로 실행
* crontab 자동화 가능
* 로그 파일 리다이렉션 운영

---

필요하시면 추가 제공 가능합니다:

* 서버 운영용 배포 가이드
* systemd 서비스 등록 방법
* cron 자동 다운로드 구성
* Docker 기반 실행 가이드
* iSH 전용 최적화 문서

원하시는 운영 환경을 말씀해 주시면 그에 맞춰 설계 문서 수준으로 정리해 드리겠습니다.
