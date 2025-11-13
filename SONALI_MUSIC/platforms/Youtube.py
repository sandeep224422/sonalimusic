import asyncio
import os
import re
import json
from typing import Union
import requests
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from SONALI_MUSIC.utils.database import is_on_off
from SONALI_MUSIC.utils.formatters import time_to_seconds
import os
import glob
import random
import logging
import aiohttp

# External API endpoints
HEROKU_API_BASE = "https://yt-apizefron-9930f07c38ef.herokuapp.com"
NEW_API_URL = "https://apikeyy-zeta.vercel.app/api"


def cookie_txt_file():
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


async def download_song(link: str, media_type: str = "audio"):
    # Extract video ID from various YouTube URL formats
    video_id = None
    if 'v=' in link:
        video_id = link.split('v=')[-1].split('&')[0].split('#')[0]
    elif 'youtu.be/' in link:
        video_id = link.split('youtu.be/')[-1].split('?')[0].split('&')[0]
    elif len(link) == 11 and link.replace('-', '').replace('_', '').isalnum():
        video_id = link
    
    if not video_id:
        match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11})', link)
        if match:
            video_id = match.group(1)
        else:
            print(f"Could not extract video ID from link: {link}")
            return None
    
    # Clean video ID (remove prefixes like "0_")
    video_id = video_id.split('_')[-1] if '_' in video_id else video_id

    download_folder = "downloads"
    os.makedirs(download_folder, exist_ok=True)
    
    if media_type == "video":
        preferred_exts = ["mp4", "mkv", "webm"]
        default_ext = "mp4"
    else:
        preferred_exts = ["mp3", "m4a", "webm"]
        default_ext = "mp3"

    # Check if file already exists
    for ext in preferred_exts:
        file_path = os.path.join(download_folder, f"{video_id}.{ext}")
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"File already exists: {file_path}")
            return file_path
    
    heroku_endpoint = "video" if media_type == "video" else "audio"
    heroku_url = f"{HEROKU_API_BASE}/{heroku_endpoint}/{video_id}"
    fallback_endpoint = "video" if media_type == "video" else "song"
    new_song_url = f"{NEW_API_URL}/{fallback_endpoint}/{video_id}"

    # Create timeout for downloads
    timeout = aiohttp.ClientTimeout(total=300, connect=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            # Try Heroku API first - with proper headers for API client detection
            headers = {
                'User-Agent': 'python-aiohttp/1.0',
                'Accept': 'audio/*, video/*, */*'  # Important for API detection
            }
            
            print(f"🔗 Requesting from Heroku API: {heroku_url}")
            
            async with session.get(heroku_url, headers=headers, allow_redirects=True) as response:
                print(f"📊 API Response Status: {response.status}")
                
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    print(f"📦 Content-Type: {content_type}")
                    
                    file_extension = default_ext
                    if 'video' in content_type:
                        file_extension = "mp4"
                    elif 'audio' in content_type:
                        if 'mpeg' in content_type or 'mp3' in content_type:
                            file_extension = "mp3"
                        elif 'm4a' in content_type:
                            file_extension = "m4a"
                    
                    file_name = f"{video_id}.{file_extension}"
                    file_path = os.path.join(download_folder, file_name)
                    
                    print(f"💾 Downloading to: {file_path}")
                    
                    try:
                        total_size = 0
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                if chunk:
                                    f.write(chunk)
                                    total_size += len(chunk)
                        
                        print(f"✅ Downloaded {total_size} bytes")
                        
                        # Verify file was downloaded successfully
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            print(f"✅ File verified: {file_path} ({os.path.getsize(file_path)} bytes)")
                            return file_path
                        else:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            print(f"❌ Downloaded file is empty: {file_path}")
                    except Exception as e:
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except:
                                pass
                        print(f"❌ Error writing file {file_path}: {e}")
                        import traceback
                        traceback.print_exc()
                elif response.status == 302:
                    # Handle redirect
                    redirect_url = response.headers.get('Location')
                    print(f"🔄 Redirect detected to: {redirect_url}")
                    if redirect_url:
                        async with session.get(redirect_url, headers=headers) as redirect_response:
                            if redirect_response.status == 200:
                                content_type = redirect_response.headers.get('Content-Type', '')
                                file_extension = default_ext
                                if 'video' in content_type:
                                    file_extension = "mp4"
                                elif 'audio' in content_type:
                                    if 'mpeg' in content_type or 'mp3' in content_type:
                                        file_extension = "mp3"
                                    elif 'm4a' in content_type:
                                        file_extension = "m4a"
                                
                                file_name = f"{video_id}.{file_extension}"
                                file_path = os.path.join(download_folder, file_name)
                                
                                try:
                                    with open(file_path, 'wb') as f:
                                        async for chunk in redirect_response.content.iter_chunked(8192):
                                            if chunk:
                                                f.write(chunk)
                                    
                                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                        print(f"✅ File downloaded from redirect: {file_path}")
                                        return file_path
                                    else:
                                        if os.path.exists(file_path):
                                            os.remove(file_path)
                                except Exception as e:
                                    if os.path.exists(file_path):
                                        try:
                                            os.remove(file_path)
                                        except:
                                            pass
                                    print(f"❌ Error downloading from redirect: {e}")
                else:
                    error_text = await response.text()
                    print(f"❌ Heroku API failed with status: {response.status}")
                    print(f"Response: {error_text[:200]}")
        except aiohttp.ClientError as e:
            print(f"❌ Heroku API network error: {e}")
            import traceback
            traceback.print_exc()
        except Exception as e:
            print(f"❌ Heroku API failed: {e}")
            import traceback
            traceback.print_exc()

        # Try fallback API
        try:
            print(f"🔄 Trying fallback API: {new_song_url}")
            async with session.get(new_song_url) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        data = await response.json()
                        download_url = data.get("link") or data.get("url")
                        if download_url:
                            data.setdefault("format", default_ext)
                            return await download_file(session, download_url, video_id, data)
                    else:
                        file_extension = default_ext
                        if 'video' in content_type:
                            file_extension = "mp4"
                        elif 'audio' in content_type:
                            if 'mpeg' in content_type or 'mp3' in content_type:
                                file_extension = "mp3"
                            elif 'm4a' in content_type:
                                file_extension = "m4a"
                        
                        file_name = f"{video_id}.{file_extension}"
                        file_path = os.path.join(download_folder, file_name)
                        
                        try:
                            with open(file_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                return file_path
                            else:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                        except Exception as e:
                            if os.path.exists(file_path):
                                try:
                                    os.remove(file_path)
                                except:
                                    pass
                            print(f"❌ Error writing file {file_path}: {e}")
                else:
                    print(f"❌ Fallback API failed with status: {response.status}")
        except Exception as e:
            print(f"❌ Fallback API failed: {e}")
        
        print("❌ All APIs failed, will use cookies method")
        return None


async def download_file(session, download_url, video_id, data):
    """Helper function to download file from URL"""
    try:
        file_format = data.get("ext") or data.get("format") or "mp3"
        if isinstance(file_format, str) and "/" in file_format:
            file_extension = file_format.split("/")[-1].lower()
        else:
            file_extension = str(file_format).lower()
        if not file_extension:
            file_extension = "mp3"
        file_name = f"{video_id}.{file_extension}"
        download_folder = "downloads"
        os.makedirs(download_folder, exist_ok=True)
        file_path = os.path.join(download_folder, file_name)

        async with session.get(download_url) as file_response:
            if file_response.status != 200:
                print(f"❌ Download URL returned status {file_response.status}")
                return None
                
            try:
                with open(file_path, 'wb') as f:
                    async for chunk in file_response.content.iter_chunked(8192):
                        if chunk:
                            f.write(chunk)
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return file_path
                else:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return None
            except Exception as e:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                print(f"❌ Error writing file {file_path}: {e}")
                return None
    except aiohttp.ClientError as e:
        print(f"❌ Network or client error occurred while downloading: {e}")
        return None
    except Exception as e:
        print(f"❌ Error occurred while downloading song: {e}")
        return None

async def check_file_size(link):
    cookie_file = cookie_txt_file()
    if not cookie_file:
        return None
        
    async def get_format_info(link):
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_file,
            "-J",
            link,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f'Error:\n{stderr.decode()}')
            return None
        return json.loads(stdout.decode())

    def parse_size(formats):
        total_size = 0
        for format in formats:
            if 'filesize' in format:
                total_size += format['filesize']
        return total_size

    info = await get_format_info(link)
    if info is None:
        return None
    
    formats = info.get('formats', [])
    if not formats:
        print("No formats found.")
        return None
    
    total_size = parse_size(formats)
    return total_size

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        cookie_file = cookie_txt_file()
        if not cookie_file:
            return 0, "No cookie file available"
            
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_file,
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        cookie_file = cookie_txt_file()
        if not cookie_file:
            return []
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --cookies {cookie_file} --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        cookie_file = cookie_txt_file()
        if not cookie_file:
            return [], link
        ytdl_opts = {"quiet": True, "cookiefile": cookie_file}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if not "dash" in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()
        
        def audio_dl():
            cookie_file = cookie_txt_file()
            ydl_optssx = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            if cookie_file:
                ydl_optssx["cookiefile"] = cookie_file
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz) and os.path.getsize(xyz) > 0:
                return xyz
            x.download([link])
            if os.path.exists(xyz) and os.path.getsize(xyz) > 0:
                return xyz
            raise FileNotFoundError(f"Audio file not created: {xyz}")

        def video_dl():
            cookie_file = cookie_txt_file()
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            if cookie_file:
                ydl_optssx["cookiefile"] = cookie_file
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz) and os.path.getsize(xyz) > 0:
                return xyz
            x.download([link])
            if os.path.exists(xyz) and os.path.getsize(xyz) > 0:
                return xyz
            raise FileNotFoundError(f"Video file not created: {xyz}")

        def song_video_dl():
            cookie_file = cookie_txt_file()
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            if cookie_file:
                ydl_optssx["cookiefile"] = cookie_file
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])
            possible_paths = [f"downloads/{title}.mp4", f"downloads/{title}"]
            for path in possible_paths:
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    return path
            raise FileNotFoundError(f"Video file not created for {title}")

        def song_audio_dl():
            cookie_file = cookie_txt_file()
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            if cookie_file:
                ydl_optssx["cookiefile"] = cookie_file
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])
            possible_paths = [f"downloads/{title}.mp3", f"downloads/{title}.m4a"]
            for path in possible_paths:
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    return path
            raise FileNotFoundError(f"Audio file not created for {title}")

        if songvideo:
            downloaded_file = await download_song(link, media_type="video")
            if downloaded_file and os.path.exists(downloaded_file):
                return downloaded_file
            print("Using cookies fallback for song video download")
            try:
                downloaded_file = await loop.run_in_executor(None, song_video_dl)
                if downloaded_file and os.path.exists(downloaded_file):
                    return downloaded_file
            except Exception as e:
                print(f"Cookies fallback failed: {e}")
                import traceback
                traceback.print_exc()
            raise FileNotFoundError(f"Failed to download video for {link}")
            
        elif songaudio:
            downloaded_file = await download_song(link, media_type="audio")
            if downloaded_file and os.path.exists(downloaded_file):
                return downloaded_file
            print("Using cookies fallback for song audio download")
            try:
                downloaded_file = await loop.run_in_executor(None, song_audio_dl)
                if downloaded_file and os.path.exists(downloaded_file):
                    return downloaded_file
            except Exception as e:
                print(f"Cookies fallback failed: {e}")
                import traceback
                traceback.print_exc()
            raise FileNotFoundError(f"Failed to download audio for {link}")
            
        elif video:
            if await is_on_off(1):
                direct = True
                downloaded_file = await download_song(link, media_type="video")
                if downloaded_file and os.path.exists(downloaded_file):
                    return downloaded_file, direct
                print("Using cookies fallback for video download")
                file_size = await check_file_size(link)
                if not file_size:
                    print("None file Size")
                    return None, direct
                total_size_mb = file_size / (1024 * 1024)
                if total_size_mb > 250:
                    print(f"File size {total_size_mb:.2f} MB exceeds the 250MB limit.")
                    return None, direct
                try:
                    downloaded_file = await loop.run_in_executor(None, video_dl)
                    if downloaded_file and os.path.exists(downloaded_file):
                        return downloaded_file, direct
                except Exception as e:
                    print(f"Video download failed: {e}")
                    import traceback
                    traceback.print_exc()
                return None, direct
            else:
                proc = await asyncio.create_subprocess_exec(
                    "yt-dlp",
                    "--cookies", cookie_txt_file() or "",
                    "-g",
                    "-f",
                    "best[height<=?720][width<=?1280]",
                    f"{link}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = False
                    return downloaded_file, direct
                else:
                   file_size = await check_file_size(link)
                   if not file_size:
                     print("None file Size")
                     return None, True
                   total_size_mb = file_size / (1024 * 1024)
                   if total_size_mb > 250:
                     print(f"File size {total_size_mb:.2f} MB exceeds the 250MB limit.")
                     return None, True
                   direct = True
                   try:
                       downloaded_file = await loop.run_in_executor(None, video_dl)
                       if downloaded_file and os.path.exists(downloaded_file):
                           return downloaded_file, direct
                   except Exception as e:
                       print(f"Video download failed: {e}")
                       import traceback
                       traceback.print_exc()
                   return None, direct
        else:
            direct = True
            downloaded_file = await download_song(link, media_type="audio")
            if downloaded_file and os.path.exists(downloaded_file):
                return downloaded_file, direct
            print("Using cookies fallback for audio download")
            try:
                downloaded_file = await loop.run_in_executor(None, audio_dl)
                if downloaded_file and os.path.exists(downloaded_file):
                    return downloaded_file, direct
            except Exception as e:
                print(f"Audio download failed: {e}")
                import traceback
                traceback.print_exc()
            raise FileNotFoundError(f"Failed to download audio for {link}")
