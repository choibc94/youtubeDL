#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import queue
import threading
from yt_dlp import YoutubeDL
from pathlib import Path

###############################################################################
# 공용 유틸 함수
###############################################################################

def input_nonempty(prompt):
    """비어있지 않은 입력만 허용."""
    while True:
        x = input(prompt).strip()
        if x:
            return x

def print_separator():
    print("-" * 70)


###############################################################################
# yt-dlp Wrapper
###############################################################################

def get_video_info(url):
    """URL의 가능한 포맷 목록을 반환"""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def list_formats(info):
    """비디오/오디오 포맷 리스트 반환"""
    video_formats = []
    audio_formats = []
    for f in info.get("formats", []):
        if f.get("vcodec") != "none" and f.get("acodec") == "none":
            video_formats.append(f)
        elif f.get("vcodec") == "none" and f.get("acodec") != "none":
            audio_formats.append(f)
    return video_formats, audio_formats


###############################################################################
# 진행률 Hook
###############################################################################

def progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "0%")
        speed = d.get("_speed_str", "N/A")
        eta = d.get("_eta_str", "N/A")
        print(f"\r진행률: {percent} | 속도: {speed} | ETA: {eta}", end="", flush=True)
    elif d["status"] == "finished":
        print("\n다운로드 완료. 후처리 시작...")


###############################################################################
# 다운로드 함수 (영상+음성 병합, 변환 가능)
###############################################################################

def download_with_options(url, download_dir, v_opt, a_opt, conv_ext=None):
    """지정된 비디오/오디오 포맷으로 다운로드 및 병합, 변환"""
    format_str = None

    # 자동 best 모드
    if v_opt == "best":
        format_str = "bestvideo+bestaudio/best"
    else:
        # 사용자가 videoID, audioID 지정한 경우
        if a_opt:
            format_str = f"{v_opt}+{a_opt}"
        else:
            format_str = v_opt

    ydl_opts = {
        "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "merge_output_format": "mp4",
        "format": format_str,
        "postprocessors": [],
    }

    # 변환 옵션
    if conv_ext:
        if conv_ext == "mp3":
            ydl_opts["postprocessors"].append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            })
        elif conv_ext == "mp4":
            ydl_opts["postprocessors"].append({
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            })

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


###############################################################################
# 플레이리스트 처리
###############################################################################

def extract_playlist_urls(info):
    """플레이리스트 내 영상 URL 목록 추출"""
    entries = info.get("entries", [])
    urls = []
    for item in entries:
        if item and "url" in item:
            base = item.get("webpage_url") or item.get("url")
            urls.append(base)
    return urls


###############################################################################
# 멀티 다운로드 큐
###############################################################################

class DownloadWorker(threading.Thread):
    def __init__(self, q, download_dir, v_opt, a_opt, conv_ext):
        super().__init__()
        self.q = q
        self.download_dir = download_dir
        self.v_opt = v_opt
        self.a_opt = a_opt
        self.conv_ext = conv_ext

    def run(self):
        while True:
            try:
                url = self.q.get_nowait()
            except queue.Empty:
                break

            print_separator()
            print(f"[QUEUE] 다운로드 시작: {url}")
            try:
                download_with_options(url, self.download_dir, self.v_opt, self.a_opt, self.conv_ext)
            except Exception as e:
                print(f"[ERROR] {url}: {e}")
            finally:
                self.q.task_done()


###############################################################################
# CLI 동작 메인 로직
###############################################################################

def cli():
    print_separator()
    print("YouTube 다운로드 CLI")
    print_separator()

    # 1. 다운로드 위치 설정
    download_dir = input_nonempty("다운로드 경로를 입력하세요: ")
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    # 2. URL 입력
    url = input_nonempty("유튜브 URL 또는 플레이리스트 URL을 입력하세요: ")

    # 3. 포맷 분석
    print("\n정보 분석 중...")
    info = get_video_info(url)
    is_playlist = "entries" in info

    # 3-1. 영상 리스트 출력 (단일 영상인 경우)
    if not is_playlist:
        video_formats, audio_formats = list_formats(info)

        print_separator()
        print("[영상 포맷 리스트]")
        for idx, f in enumerate(video_formats):
            print(f"{idx:03d}: {f.get('format_id')} | {f.get('resolution')} | {f.get('vcodec')} | {f.get('filesize', 'N/A')}")

        print_separator()
        print("[오디오 포맷 리스트]")
        for idx, f in enumerate(audio_formats):
            print(f"{idx:03d}: {f.get('format_id')} | {f.get('acodec')} | {f.get('abr')}kbps | {f.get('filesize', 'N/A')}")

        print_separator()

        mode = input("자동 best 선택(Y) 또는 수동 선택(N)? [Y/N]: ").strip().upper()

        if mode == "Y":
            v_opt = "best"
            a_opt = None
        else:
            v_idx = int(input("다운로드할 영상 포맷 번호: "))
            a_idx = int(input("다운로드할 오디오 포맷 번호: "))
            v_opt = video_formats[v_idx]["format_id"]
            a_opt = audio_formats[a_idx]["format_id"]

    else:
        print("[플레이리스트 감지] 전체 목록을 대상으로 처리합니다.")
        v_opt = "best"
        a_opt = None

    # 변환 옵션
    print_separator()
    conv = input("변환 옵션 선택 (none/mp3/mp4): ").strip().lower()
    if conv not in ["none", "mp3", "mp4"]:
        conv = "none"
    conv_ext = None if conv == "none" else conv

    # 플레이리스트라면 전체 URL 을 큐로 투입
    if is_playlist:
        urls = extract_playlist_urls(info)
        print(f"[플레이리스트] 총 {len(urls)}개 항목")
    else:
        urls = [url]

    # 멀티 다운로드 큐
    th_count = input("멀티 다운로드 스레드 수 지정(기본 2): ").strip()
    th_count = int(th_count) if th_count.isdigit() and int(th_count) > 0 else 2

    q = queue.Queue()
    for u in urls:
        q.put(u)

    workers = []
    for _ in range(th_count):
        t = DownloadWorker(q, download_dir, v_opt, a_opt, conv_ext)
        t.start()
        workers.append(t)

    for t in workers:
        t.join()

    print_separator()
    print("모든 다운로드가 완료되었습니다.")
    print_separator()


###############################################################################
# 엔트리포인트
###############################################################################

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        print("\n사용자 인터럽트로 종료되었습니다.")
