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

# Import your bot's utility functions (if available)
try:
    from SONALI_MUSIC.utils.database import is_on_off
    from SONALI_MUSIC.utils.formatters import time_to_seconds
except ImportError:
    # These are optional - file works without them
    pass

# ============================================================================
# API CONFIGURATION
# ============================================================================

HEROKU_API_BASE = "https://yt-apizefron-9930f07c38ef.herokuapp.com"
API_TIMEOUT = 180  # 3 minutes for API to download + upload


# ============================================================================
# CORE API FUNCTIONS
# ============================================================================

async def search_and_get_audio(query: str):
    """Search for audio using Heroku API /api/song endpoint"""
    try:
        encoded_query = quote_plus(query)
        search_url = f"{HEROKU_API_BASE}/api/song?query={encoded_query}"
        
        print(f"🔍 [API] Searching audio: {query}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'ok' and data.get('type') == 'audio' and data.get('link'):
                        print(f"✅ [API] Audio found! Source: {data.get('source', 'unknown')}")
                        return data
                    else:
                        print(f"⚠️ [API] Invalid response: {data.get('status')}")
                        return None
                else:
                    print(f"❌ [API] Error {response.status}")
                    return None
    except asyncio.TimeoutError:
        print(f"❌ [API] Timeout after {API_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"❌ [API] Error: {e}")
        return None


async def search_and_get_video(query: str):
    """Search for video using Heroku API /api/video endpoint"""
    try:
        encoded_query = quote_plus(query)
        search_url = f"{HEROKU_API_BASE}/api/video?query={encoded_query}"
        
        print(f"🔍 [API] Searching video: {query}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'ok' and data.get('type') == 'video' and data.get('link'):
                        print(f"✅ [API] Video found! Source: {data.get('source', 'unknown')}")
                        return data
                    else:
                        print(f"⚠️ [API] Invalid response: {data.get('status')}")
                        return None
                else:
                    print(f"❌ [API] Error {response.status}")
                    return None
    except asyncio.TimeoutError:
        print(f"❌ [API] Timeout after {API_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"❌ [API] Error: {e}")
        return None


# ============================================================================
# FALLBACK: YT-DLP DOWNLOAD (if API fails)
# ============================================================================

def cookie_txt_file():
    """Get random cookie file for yt-dlp fallback"""
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
    """Fallback: Download using yt-dlp if API fails"""
    try:
        print(f"🔄 [FALLBACK] Using yt-dlp for: {query}")
        
        # Search YouTube
        results = VideosSearch(query, limit=1)
        result = await results.next()
        
        if not result.get('result'):
            return None
        
        video = result['result'][0]
        video_url = video['link']
        video_id = video['id']
        
        # Download with yt-dlp
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
                'file_path': filename,  # Local file for fallback
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumb': info.get('thumbnail', ''),
                'source': 'ytdlp_fallback'
            }
    except Exception as e:
        print(f"❌ [FALLBACK] yt-dlp failed: {e}")
        return None


# ============================================================================
# MAIN FUNCTIONS (Called by your play commands)
# ============================================================================

async def YoutubeDownload(query: str, message=None):
    """
    Main function for audio download/streaming
    
    Returns:
        dict with either:
        - 'url': Direct Telegram URL for streaming (API success)
        - 'file_path': Local file path (fallback)
        Plus: 'title', 'duration', 'thumb', 'source'
    
    Raises:
        Exception if all methods fail
    """
    print(f"\n{'='*60}")
    print(f"🎵 YOUTUBE AUDIO REQUEST: {query}")
    print(f"{'='*60}\n")
    
    # TRY 1: Use Heroku API (fast, cached, no download needed)
    try:
        api_result = await search_and_get_audio(query)
        
        if api_result and api_result.get('link'):
            result = {
                'url': api_result['link'],  # Direct streaming URL!
                'title': api_result.get('title', 'Unknown'),
                'duration': api_result.get('duration', 0),
                'thumb': api_result.get('thumb', ''),
                'source': api_result.get('source', 'api'),
                'videoId': api_result.get('jobId', 'unknown')
            }
            
            print(f"✅ SUCCESS via API!")
            print(f"   URL: {result['url'][:50]}...")
            print(f"   Title: {result['title']}")
            print(f"   Duration: {result['duration']}s")
            
            return result
    except Exception as e:
        print(f"⚠️ API failed: {e}")
    
    # TRY 2: Fallback to yt-dlp (downloads local file)
    try:
        fallback_result = await fallback_ytdlp_download(query, video_only=False)
        
        if fallback_result:
            print(f"✅ SUCCESS via yt-dlp fallback!")
            return fallback_result
    except Exception as e:
        print(f"⚠️ Fallback failed: {e}")
    
    # FAILED: No method worked
    error_msg = "❌ Could not get audio from any source (API + fallback failed)"
    print(error_msg)
    if message:
        try:
            await message.reply_text(error_msg)
        except:
            pass
    raise Exception(error_msg)


async def YoutubeVideDownload(query: str, message=None):
    """
    Main function for video download/streaming
    
    Returns:
        dict with either:
        - 'url': Direct Telegram URL for streaming (API success)
        - 'file_path': Local file path (fallback)
        Plus: 'title', 'duration', 'thumb', 'source', 'resolution'
    
    Raises:
        Exception if all methods fail
    """
    print(f"\n{'='*60}")
    print(f"🎬 YOUTUBE VIDEO REQUEST: {query}")
    print(f"{'='*60}\n")
    
    # TRY 1: Use Heroku API (fast, cached, no download needed)
    try:
        api_result = await search_and_get_video(query)
        
        if api_result and api_result.get('link'):
            result = {
                'url': api_result['link'],  # Direct streaming URL!
                'title': api_result.get('title', 'Unknown'),
                'duration': api_result.get('duration', 0),
                'thumb': api_result.get('thumb', ''),
                'source': api_result.get('source', 'api'),
                'resolution': api_result.get('resolution', 'N/A'),
                'videoId': api_result.get('jobId', 'unknown')
            }
            
            print(f"✅ SUCCESS via API!")
            print(f"   URL: {result['url'][:50]}...")
            print(f"   Title: {result['title']}")
            print(f"   Duration: {result['duration']}s")
            print(f"   Resolution: {result['resolution']}")
            
            return result
    except Exception as e:
        print(f"⚠️ API failed: {e}")
    
    # TRY 2: Fallback to yt-dlp (downloads local file)
    try:
        fallback_result = await fallback_ytdlp_download(query, video_only=True)
        
        if fallback_result:
            fallback_result['resolution'] = 'N/A'
            print(f"✅ SUCCESS via yt-dlp fallback!")
            return fallback_result
    except Exception as e:
        print(f"⚠️ Fallback failed: {e}")
    
    # FAILED: No method worked
    error_msg = "❌ Could not get video from any source (API + fallback failed)"
    print(error_msg)
    if message:
        try:
            await message.reply_text(error_msg)
        except:
            pass
    raise Exception(error_msg)


# ============================================================================
# EXAMPLE USAGE IN YOUR PLAY COMMANDS
# ============================================================================

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
        # Get audio info (URL or file_path)
        result = await YoutubeDownload(query, message)
        
        # Check if we got a URL (API) or file_path (fallback)
        if 'url' in result:
            # STREAM URL DIRECTLY - NO DOWNLOAD!
            stream_url = result['url']
            print(f"✅ Streaming from URL: {stream_url}")
        else:
            # Use local file (fallback)
            stream_url = result['file_path']
            print(f"✅ Streaming from file: {stream_url}")
        
        # Play with PyTgCalls
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
        # Get video info (URL or file_path)
        result = await YoutubeVideDownload(query, message)
        
        # Check if we got a URL (API) or file_path (fallback)
        if 'url' in result:
            # STREAM URL DIRECTLY - NO DOWNLOAD!
            stream_url = result['url']
            print(f"✅ Streaming from URL: {stream_url}")
        else:
            # Use local file (fallback)
            stream_url = result['file_path']
            print(f"✅ Streaming from file: {stream_url}")
        
        # Play with PyTgCalls
        await pytgcalls.play(
            chat_id,
            VideoPiped(stream_url, HighQualityVideo(), HighQualityAudio())
        )
        
        await message.reply_text(f"🎬 Playing: {result['title']}")
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
"""
