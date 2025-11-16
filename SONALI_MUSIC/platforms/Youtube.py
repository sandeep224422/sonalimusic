"""
CORRECTED BOT CODE - Fixed for Heroku API
API: https://yt-apizefron-9930f07c38ef.herokuapp.com

MAIN FIXES:
1. Increased timeout from 30s to 180s (API needs time for first-time downloads)
2. Removed download_from_api_link function (caused FileNotFoundError)
3. Direct URL streaming - NO local file downloads needed
4. Better error logging for debugging
5. Proper handling of cached songs (instant) vs new songs (needs processing)

HOW IT WORKS:
- First request for a song: API downloads from YouTube, uploads to Telegram (~60-120s)
- Subsequent requests: API returns cached URL instantly (~1-2s)
- Bot streams Telegram URLs directly with PyTgCalls - NO downloading needed
"""

import asyncio
import os
import re
import json
from typing import Union
from urllib.parse import quote_plus
import requests
import yt_dlp
from pyrogram import Client, filters
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from SONALI_MUSIC.utils.database import is_on_off
from SONALI_MUSIC.utils.formatters import time_to_seconds
import aiohttp

# API Configuration
HEROKU_API_BASE = "https://yt-apizefron-9930f07c38ef.herokuapp.com"

# IMPORTANT: Increased timeout to 180 seconds (3 minutes)
# This allows API time to download from YouTube and upload to Telegram
API_TIMEOUT = 180


def cookie_txt_file():
    """Get random cookie file for yt-dlp (fallback only)"""
    try:
        cookie_dir = f"{os.getcwd()}/cookies"
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir, exist_ok=True)
            return None
        
        cookies_files = [f for f in os.listdir(cookie_dir) if f.endswith(".txt")]
        if not cookies_files:
            return None
        
        cookie_file = os.path.join(cookie_dir, random.choice(cookies_files))
        if os.path.exists(cookie_file):
            return cookie_file
        return None
    except Exception as e:
        print(f"Error getting cookie file: {e}")
        return None


async def search_and_get_audio(query: str):
    """
    Search for audio using /api/song?query= endpoint
    
    Returns:
        dict with 'status', 'type', 'link', 'title', 'duration', 'thumb', 'source'
        OR None if failed
    """
    try:
        encoded_query = quote_plus(query)
        search_url = f"{HEROKU_API_BASE}/api/song?query={encoded_query}"
        
        print(f"🔍 Searching audio: {query}")
        print(f"🔗 API URL: {search_url}")
        
        async with aiohttp.ClientSession() as session:
            # FIXED: Increased timeout to 180 seconds
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                print(f"📡 Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📦 Response data: {json.dumps(data, indent=2)}")
                    
                    # Check if we got valid audio data
                    if data.get('status') == 'ok' and data.get('type') == 'audio' and data.get('link'):
                        source = data.get('source', 'unknown')
                        print(f"✅ Audio found! Source: {source}")
                        return data
                    else:
                        print(f"⚠️ Invalid response format: {data}")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ API error {response.status}: {error_text[:200]}")
                    return None
                    
    except asyncio.TimeoutError:
        print(f"❌ Timeout error: API took longer than {API_TIMEOUT} seconds")
        return None
    except Exception as e:
        print(f"❌ Error searching audio: {e}")
        import traceback
        traceback.print_exc()
        return None


async def search_and_get_video(query: str):
    """
    Search for video using /api/video?query= endpoint
    
    Returns:
        dict with 'status', 'type', 'link', 'title', 'duration', 'thumb', 'source'
        OR None if failed
    """
    try:
        encoded_query = quote_plus(query)
        search_url = f"{HEROKU_API_BASE}/api/video?query={encoded_query}"
        
        print(f"🔍 Searching video: {query}")
        print(f"🔗 API URL: {search_url}")
        
        async with aiohttp.ClientSession() as session:
            # FIXED: Increased timeout to 180 seconds
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                print(f"📡 Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📦 Response data: {json.dumps(data, indent=2)}")
                    
                    # Check if we got valid video data
                    if data.get('status') == 'ok' and data.get('type') == 'video' and data.get('link'):
                        source = data.get('source', 'unknown')
                        print(f"✅ Video found! Source: {source}")
                        return data
                    else:
                        print(f"⚠️ Invalid response format: {data}")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ API error {response.status}: {error_text[:200]}")
                    return None
                    
    except asyncio.TimeoutError:
        print(f"❌ Timeout error: API took longer than {API_TIMEOUT} seconds")
        return None
    except Exception as e:
        print(f"❌ Error searching video: {e}")
        import traceback
        traceback.print_exc()
        return None


async def check_job_status(job_id: str):
    """
    Check background job status using /api/status?id= endpoint
    
    Returns:
        dict with job status information OR None if failed
    """
    try:
        status_url = f"{HEROKU_API_BASE}/api/status?id={job_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(status_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return None
    except Exception as e:
        print(f"❌ Error checking job status: {e}")
        return None


async def play_from_api(query: str, message):
    """
    SIMPLIFIED: Get audio URL from API and return for direct streaming
    
    NO FILE DOWNLOAD - Returns Telegram URL that can be streamed directly by PyTgCalls
    
    Returns:
        dict with 'url', 'title', 'duration', 'thumb', 'source'
        
    Raises:
        Exception if audio cannot be fetched
    """
    try:
        print(f"\n{'='*50}")
        print(f"🎵 PLAY AUDIO REQUEST: {query}")
        print(f"{'='*50}\n")
        
        # Get the song info from API
        api_result = await search_and_get_audio(query)
        
        if not api_result:
            raise Exception("Could not get audio from API - no result returned")
        
        # Check if status is 'processing' (means background job is running)
        if api_result.get('status') == 'processing' and api_result.get('jobId'):
            job_id = api_result.get('jobId')
            print(f"⏳ Job is processing: {job_id}")
            
            status_msg = await message.reply_text(f"⏳ Processing audio, please wait...")
            
            # Poll for job completion (max 60 attempts = 2 minutes)
            max_attempts = 60
            for attempt in range(max_attempts):
                await asyncio.sleep(2)  # Wait 2 seconds between checks
                
                status_data = await check_job_status(job_id)
                
                if status_data and status_data.get('status') == 'ok':
                    print(f"✅ Job completed!")
                    # Job completed, break and use the final result
                    api_result = status_data
                    break
                    
                elif status_data and status_data.get('status') == 'error':
                    error = status_data.get('error', 'Unknown error')
                    print(f"❌ Job failed: {error}")
                    raise Exception(f"Processing failed: {error}")
                    
                elif status_data and status_data.get('status') == 'processing':
                    progress = status_data.get('progress', 'Processing...')
                    print(f"⏳ Progress: {progress} ({attempt + 1}/{max_attempts})")
                    
                    # Update message every 10 seconds (every 5 attempts)
                    if attempt % 5 == 0 and attempt > 0:
                        try:
                            await status_msg.edit_text(
                                f"⏳ {progress}\n"
                                f"Time elapsed: {(attempt + 1) * 2} seconds"
                            )
                        except:
                            pass
            
            # Delete status message
            try:
                await status_msg.delete()
            except:
                pass
            
            # Final check - if still no link, fail
            if not api_result.get('link'):
                raise Exception("Processing timeout - no audio link received")
        
        # Extract data from API response
        if api_result and api_result.get('link'):
            audio_url = api_result['link']
            title = api_result.get('title', 'Unknown Title')
            duration = api_result.get('duration', 0)
            thumb = api_result.get('thumb', '')
            source = api_result.get('source', 'unknown')
            
            print(f"\n✅ AUDIO READY:")
            print(f"   Title: {title}")
            print(f"   URL: {audio_url}")
            print(f"   Duration: {duration}s")
            print(f"   Source: {source}")
            print(f"   Thumbnail: {thumb[:50]}...")
            
            # RETURN THE URL DIRECTLY - PyTgCalls will stream it!
            return {
                'url': audio_url,      # Stream this URL directly with PyTgCalls
                'title': title,
                'duration': duration,
                'thumb': thumb,
                'source': source
            }
        else:
            raise Exception("Could not get audio link from API")
            
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        try:
            await message.reply_text(error_msg)
        except:
            pass
        raise


async def play_video_from_api(query: str, message):
    """
    SIMPLIFIED: Get video URL from API and return for direct streaming
    
    NO FILE DOWNLOAD - Returns Telegram URL that can be streamed directly by PyTgCalls
    
    Returns:
        dict with 'url', 'title', 'duration', 'thumb', 'source', 'resolution'
        
    Raises:
        Exception if video cannot be fetched
    """
    try:
        print(f"\n{'='*50}")
        print(f"🎬 PLAY VIDEO REQUEST: {query}")
        print(f"{'='*50}\n")
        
        # Get the video info from API
        api_result = await search_and_get_video(query)
        
        if not api_result:
            raise Exception("Could not get video from API - no result returned")
        
        # Check if status is 'processing' (means background job is running)
        if api_result.get('status') == 'processing' and api_result.get('jobId'):
            job_id = api_result.get('jobId')
            print(f"⏳ Job is processing: {job_id}")
            
            status_msg = await message.reply_text(f"⏳ Processing video, please wait...")
            
            # Poll for job completion (max 60 attempts = 2 minutes)
            max_attempts = 60
            for attempt in range(max_attempts):
                await asyncio.sleep(2)  # Wait 2 seconds between checks
                
                status_data = await check_job_status(job_id)
                
                if status_data and status_data.get('status') == 'ok':
                    print(f"✅ Job completed!")
                    # Job completed, break and use the final result
                    api_result = status_data
                    break
                    
                elif status_data and status_data.get('status') == 'error':
                    error = status_data.get('error', 'Unknown error')
                    print(f"❌ Job failed: {error}")
                    raise Exception(f"Processing failed: {error}")
                    
                elif status_data and status_data.get('status') == 'processing':
                    progress = status_data.get('progress', 'Processing...')
                    print(f"⏳ Progress: {progress} ({attempt + 1}/{max_attempts})")
                    
                    # Update message every 10 seconds (every 5 attempts)
                    if attempt % 5 == 0 and attempt > 0:
                        try:
                            await status_msg.edit_text(
                                f"⏳ {progress}\n"
                                f"Time elapsed: {(attempt + 1) * 2} seconds"
                            )
                        except:
                            pass
            
            # Delete status message
            try:
                await status_msg.delete()
            except:
                pass
            
            # Final check - if still no link, fail
            if not api_result.get('link'):
                raise Exception("Processing timeout - no video link received")
        
        # Extract data from API response
        if api_result and api_result.get('link'):
            video_url = api_result['link']
            title = api_result.get('title', 'Unknown Title')
            duration = api_result.get('duration', 0)
            thumb = api_result.get('thumb', '')
            source = api_result.get('source', 'unknown')
            resolution = api_result.get('resolution', 'N/A')
            
            print(f"\n✅ VIDEO READY:")
            print(f"   Title: {title}")
            print(f"   URL: {video_url}")
            print(f"   Duration: {duration}s")
            print(f"   Resolution: {resolution}")
            print(f"   Source: {source}")
            print(f"   Thumbnail: {thumb[:50]}...")
            
            # RETURN THE URL DIRECTLY - PyTgCalls will stream it!
            return {
                'url': video_url,      # Stream this URL directly with PyTgCalls
                'title': title,
                'duration': duration,
                'thumb': thumb,
                'source': source,
                'resolution': resolution
            }
        else:
            raise Exception("Could not get video link from API")
            
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        try:
            await message.reply_text(error_msg)
        except:
            pass
        raise


# ============================================================================
# EXAMPLE USAGE WITH PyTgCalls
# ============================================================================

"""
EXAMPLE: How to use these functions in your music bot

from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, VideoPiped, HighQualityAudio, HighQualityVideo

# Initialize PyTgCalls
pytgcalls = PyTgCalls(your_client)
await pytgcalls.start()

# PLAY AUDIO
@Client.on_message(filters.command("play"))
async def play_command(client, message):
    query = message.text.split(None, 1)[1]  # Get song name
    chat_id = message.chat.id
    
    try:
        # Get audio URL from API
        result = await play_from_api(query, message)
        
        # Stream directly with PyTgCalls - NO file download!
        await pytgcalls.play(
            chat_id,
            AudioPiped(
                result['url'],          # Stream Telegram URL directly!
                HighQualityAudio()
            )
        )
        
        # Send success message
        await message.reply_text(
            f"🎵 Now playing:\n"
            f"**{result['title']}**\n"
            f"Duration: {result['duration']}s\n"
            f"Source: {result['source']}"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


# PLAY VIDEO
@Client.on_message(filters.command("vplay"))
async def vplay_command(client, message):
    query = message.text.split(None, 1)[1]  # Get video name
    chat_id = message.chat.id
    
    try:
        # Get video URL from API
        result = await play_video_from_api(query, message)
        
        # Stream directly with PyTgCalls - NO file download!
        await pytgcalls.play(
            chat_id,
            VideoPiped(
                result['url'],          # Stream Telegram URL directly!
                HighQualityVideo(),
                HighQualityAudio()
            )
        )
        
        # Send success message
        await message.reply_text(
            f"🎬 Now playing:\n"
            f"**{result['title']}**\n"
            f"Duration: {result['duration']}s\n"
            f"Resolution: {result.get('resolution', 'N/A')}\n"
            f"Source: {result['source']}"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
"""


# ============================================================================
# FALLBACK: Direct YouTube download (use only if API fails)
# ============================================================================

async def fallback_download_youtube(query: str):
    """
    FALLBACK ONLY - Use this if API is down
    Downloads directly from YouTube using yt-dlp
    """
    try:
        # Search YouTube
        results = VideosSearch(query, limit=1)
        result = await results.next()
        
        if not result['result']:
            return None
        
        video = result['result'][0]
        video_url = video['link']
        
        # Download with yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            
            return {
                'file_path': filename,
                'title': info['title'],
                'duration': info['duration'],
                'thumb': info['thumbnail']
            }
    except Exception as e:
        print(f"Fallback download error: {e}")
        return None
