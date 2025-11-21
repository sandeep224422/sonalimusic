#!/usr/bin/env python3
"""
COMPLETE WORKING YOUTUBE.PY - Ready to use with PyTgCalls
For: https://github.com/sandeep224422/sonalimusic
API: https://yt-apizefron-9930f07c38ef.herokuapp.com

USAGE:
Replace your SONALI_MUSIC/platforms/Youtube.py with this file
This file provides TWO functions that work with your API:
1. YoutubeDownload() - For audio playback
2. YoutubeVideDownload() - For video playback
Both return:
- url: Direct Telegram URL to stream (NO file download!)
- title, duration, thumb: Song/video information
"""

import asyncio
import os
import re
import json
from typing import Union
from urllib.parse import quote_plus
import random
import requests
import aiohttp
import yt_dlp
from pyrogram import Client, filters
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

try:
    from SONALI_MUSIC.utils.database import is_on_off
    from SONALI_MUSIC.utils.formatters import time_to_seconds
except ImportError:
    pass

HEROKU_API_BASE = "https://yt-apizefron-9930f07c38ef.herokuapp.com"
API_TIMEOUT = 180

async def fetch_song_entry(query: str):
    encoded_query = quote_plus(query)
    url = f"{HEROKU_API_BASE}/song?query={encoded_query}"
    print(f"🔍 [API] Fetching /song entry for: {query}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                if response.status != 200:
                    print(f"❌ [API] /song error {response.status}")
                    return None
                data = await response.json()
                if not data.get("success"):
                    print(f"⚠️ [API] /song returned: {data}")
                    return None
                video_id = data.get("videoId")
                if not video_id:
                    return None
                data["link"] = f"{HEROKU_API_BASE}/audio/{video_id}"
                data["videoLink"] = f"{HEROKU_API_BASE}/video/{video_id}"
                data["playLink"] = f"{HEROKU_API_BASE}/play/{video_id}"
                return data
    except asyncio.TimeoutError:
        print(f"❌ [API] /song timeout after {API_TIMEOUT}s")
    except Exception as exc:
        print(f"❌ [API] /song failed: {exc}")
    return None

async def fetch_info(video_id: str):
    url = f"{HEROKU_API_BASE}/info/{video_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as exc:
        print(f"⚠️ [API] /info error: {exc}")
    return None

async def enrich_entry(entry: dict):
    if entry.get("title") and entry.get("duration") and entry.get("thumb"):
        return entry
    video_id = entry.get("videoId")
    if not video_id:
        return entry
    info = await fetch_info(video_id)
    if not info:
        return entry
    entry.setdefault("title", info.get("title"))
    entry.setdefault("duration", info.get("duration"))
    thumb = info.get("thumbnail") or info.get("thumb")
    if thumb:
        entry.setdefault("thumb", thumb)
    return entry

def cookie_txt_file():
    try:
        cookie_dir = f"{os.getcwd()}/cookies"
        if not os.path.exists(cookie_dir):
            return None
        cookies_files = [f for f in os.listdir(cookie_dir) if f.endswith(".txt")]
        if not cookies_files:
            return None
        cookie_file = os.path.join(cookie_dir, random.choice(cookies_files))
        return cookie_file if os.path.exists(cookie_file) else None
    except Exception:
        return None

async def fallback_ytdlp_download(query: str, video_only: bool = False):
    try:
        print(f"🔄 [FALLBACK] Using yt-dlp for: {query}")
        results = VideosSearch(query, limit=1)
        result = await results.next()
        if not result.get('result'):
            return None
        video = result['result'][0]
        video_url = video['link']
        video_id = video['id']
        download_folder = "downloads"
        os.makedirs(download_folder, exist_ok=True)
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best' if video_only else 'bestaudio/best',
            'outtmpl': f'{download_folder}/{video_id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        cookie_file = cookie_txt_file()
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            print(f"✅ [FALLBACK] Downloaded to: {filename}")
            return {
                'file_path': filename,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumb': info.get('thumbnail', ''),
                'source': 'ytdlp_fallback'
            }
    except Exception as e:
        print(f"❌ [FALLBACK] yt-dlp failed: {e}")
        return None

async def YoutubeDownload(query: str, message=None):
    print(f"\n{'='*60}\n🎵 YOUTUBE AUDIO REQUEST: {query}\n{'='*60}\n")
    api_result = await fetch_song_entry(query)
    if api_result and api_result.get("link"):
        api_result = await enrich_entry(api_result)
        result = {
            'url': api_result['link'],
            'title': api_result.get('title', 'Unknown'),
            'duration': api_result.get('duration', 0),
            'thumb': api_result.get('thumb', ''),
            'source': 'heroku_api',
            'videoId': api_result.get('videoId')
        }
        print("✅ SUCCESS via Heroku API (audio)")
        print(f"   URL: {result['url'][:60]}...")
        print(f"   Title: {result['title']}")
        print(f"   Duration: {result['duration']}s")
        return result
    fallback_result = await fallback_ytdlp_download(query, video_only=False)
    if fallback_result:
        print("✅ SUCCESS via yt-dlp fallback (audio)")
        return fallback_result
    error_msg = "❌ Could not get audio from API or fallback"
    print(error_msg)
    if message:
        await message.reply_text(error_msg)
    raise Exception(error_msg)

async def YoutubeVideDownload(query: str, message=None):
    print(f"\n{'='*60}\n🎬 YOUTUBE VIDEO REQUEST: {query}\n{'='*60}\n")
    api_result = await fetch_song_entry(query)
    if api_result and api_result.get("videoLink"):
        api_result = await enrich_entry(api_result)
        result = {
            'url': api_result['videoLink'],
            'title': api_result.get('title', 'Unknown'),
            'duration': api_result.get('duration', 0),
            'thumb': api_result.get('thumb', ''),
            'source': 'heroku_api',
            'resolution': api_result.get('resolution', 'auto'),
            'videoId': api_result.get('videoId')
        }
        print("✅ SUCCESS via Heroku API (video)")
        print(f"   URL: {result['url'][:60]}...")
        print(f"   Title: {result['title']}")
        print(f"   Duration: {result['duration']}s")
        print(f"   Resolution: {result['resolution']}")
        return result
    fallback_result = await fallback_ytdlp_download(query, video_only=True)
    if fallback_result:
        fallback_result['resolution'] = fallback_result.get('resolution', 'N/A')
        print("✅ SUCCESS via yt-dlp fallback (video)")
        return fallback_result
    error_msg = "❌ Could not get video from API or fallback"
    print(error_msg)
    if message:
        await message.reply_text(error_msg)
    raise Exception(error_msg)

"""
HOW TO USE IN YOUR BOT:
from SONALI_MUSIC.platforms.Youtube import YoutubeDownload, YoutubeVideDownload
from pytgcalls.types import AudioPiped, VideoPiped, HighQualityAudio, HighQualityVideo

# AUDIO PLAYBACK
@Client.on_message(filters.command("play"))
async def play_command(client, message):
    query = message.text.split(None, 1)[1]
    chat_id = message.chat.id
    try:
        result = await YoutubeDownload(query, message)
        stream_url = result['url'] if 'url' in result else result['file_path']
        await pytgcalls.play(
            chat_id,
            AudioPiped(stream_url, HighQualityAudio())
        )
        await message.reply_text(f"🎵 Playing: {result['title']}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# VIDEO PLAYBACK
@Client.on_message(filters.command("vplay"))
async def vplay_command(client, message):
    query = message.text.split(None, 1)[1]
    chat_id = message.chat.id
    try:
        result = await YoutubeVideDownload(query, message)
        stream_url = result['url'] if 'url' in result else result['file_path']
        await pytgcalls.play(
            chat_id,
            VideoPiped(stream_url, HighQualityVideo(), HighQualityAudio())
        )
        await message.reply_text(f"🎬 Playing: {result['title']}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
"""
