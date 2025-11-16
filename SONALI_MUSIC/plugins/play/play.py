import random
import string

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message
from pytgcalls.exceptions import NoActiveGroupCall

import config
from SONALI_MUSIC import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app
from SONALI_MUSIC.core.call import Sona
from SONALI_MUSIC.utils import seconds_to_min, time_to_seconds
from SONALI_MUSIC.utils.channelplay import get_channeplayCB
from SONALI_MUSIC.utils.decorators.language import languageCB
from SONALI_MUSIC.utils.decorators.play import PlayWrapper
from SONALI_MUSIC.utils.formatters import formats
from SONALI_MUSIC.utils.inline import (
    botplaylist_markup,
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
)
from SONALI_MUSIC.utils.logger import play_logs
from SONALI_MUSIC.utils.stream.stream import stream
from config import BANNED_USERS, lyrical

# ============================================================================
# ✅ HEROKU API INTEGRATION - Added by Brahix
# ============================================================================
import asyncio
import aiohttp
from urllib.parse import quote_plus

HEROKU_API_BASE = "https://yt-apizefron-9930f07c38ef.herokuapp.com"
API_TIMEOUT = 180  # 3 minutes for first-time downloads

async def get_audio_from_api(query: str):
    """Get audio from Heroku API - returns instantly if cached!"""
    try:
        encoded_query = quote_plus(query)
        search_url = f"{HEROKU_API_BASE}/api/song?query={encoded_query}"
        
        print(f"🔍 [API] Searching: {query}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'ok' and data.get('link'):
                        print(f"✅ [API] Found! Source: {data.get('source', 'unknown')}")
                        
                        # Convert API response to YouTube.track() format
                        return {
                            'title': data.get('title', 'Unknown'),
                            'duration_min': seconds_to_min(data.get('duration', 0)),
                            'thumb': data.get('thumb', config.YOUTUBE_IMG_URL),
                            'vidid': data.get('jobId', 'api_track'),
                            'url': data.get('link'),  # Direct Telegram URL!
                        }, data.get('jobId', 'api_track')
                    else:
                        print(f"⚠️ [API] Invalid response")
                        return None, None
                else:
                    print(f"❌ [API] Error {response.status}")
                    return None, None
    except Exception as e:
        print(f"❌ [API] Exception: {e}")
        return None, None

async def get_video_from_api(query: str):
    """Get video from Heroku API"""
    try:
        encoded_query = quote_plus(query)
        search_url = f"{HEROKU_API_BASE}/api/video?query={encoded_query}"
        
        print(f"🔍 [API] Searching video: {query}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'ok' and data.get('link'):
                        print(f"✅ [API] Video found! Source: {data.get('source', 'unknown')}")
                        
                        return {
                            'title': data.get('title', 'Unknown'),
                            'duration_min': seconds_to_min(data.get('duration', 0)),
                            'thumb': data.get('thumb', config.YOUTUBE_IMG_URL),
                            'vidid': data.get('jobId', 'api_video'),
                            'url': data.get('link'),  # Direct Telegram URL!
                        }, data.get('jobId', 'api_video')
                    else:
                        return None, None
                else:
                    return None, None
    except Exception as e:
        print(f"❌ [API] Video exception: {e}")
        return None, None

# ============================================================================


@app.on_message(
   filters.command(["play", "vplay", "cplay", "cvplay", "playforce", "vplayforce", "cplayforce", "cvplayforce"] ,prefixes=["/", "!", "%", ",", "", ".", "@", "#"])
            
    & filters.group
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    mystic = await message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    plist_id = None
    slider = None
    plist_type = None
    spotify = None
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    audio_telegram = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )

    video_telegram = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )
    if audio_telegram:
        if audio_telegram.file_size > 104857600:
            return await mystic.edit_text(_["play_5"])
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention)
            )
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }

            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    elif video_telegram:
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    return await mystic.edit_text(
                        _["play_7"].format(f"{' | '.join(formats)}")
                    )
            except:
                return await mystic.edit_text(
                    _["play_7"].format(f"{' | '.join(formats)}")
                )
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_8"])
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=True,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    elif url:
        if await YouTube.exists(url):
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(
                        url,
                        config.PLAYLIST_FETCH_LIMIT,
                        message.from_user.id,
                    )
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "yt"
                if "&" in url:
                    plist_id = (url.split("=")[1]).split("&")[0]
                else:
                    plist_id = url.split("=")[1]
                img = config.PLAYLIST_IMG_URL
                cap = _["play_9"]
            else:
                try:
                    details, track_id = await YouTube.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(
                    details["title"],
                    details["duration_min"],
                )
        elif await Spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                return await mystic.edit_text(
                    "» sᴘᴏᴛɪғʏ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ʏᴇᴛ.\n\nᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ."
                )
            if "track" in url:
                try:
                    details, track_id = await Spotify.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try:
                    details, plist_id = await Spotify.playlist(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spplay"
                img = config.SPOTIFY_PLAYLIST_IMG_URL
                cap = _["play_11"].format(app.mention, message.from_user.mention)
            elif "album" in url:
                try:
                    details, plist_id = await Spotify.album(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spalbum"
                img = config.SPOTIFY_ALBUM_IMG_URL
                cap = _["play_11"].format(app.mention, message.from_user.mention)
            elif "artist" in url:
                try:
                    details, plist_id = await Spotify.artist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spartist"
                img = config.SPOTIFY_ARTIST_IMG_URL
                cap = _["play_11"].format(message.from_user.first_name)
            else:
                return await mystic.edit_text(_["play_15"])
        elif await Apple.valid(url):
            if "album" in url:
                try:
                    details, track_id = await Apple.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try:
                    details, plist_id = await Apple.playlist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "apple"
                cap = _["play_12"].format(app.mention, message.from_user.mention)
                img = url
            else:
                return await mystic.edit_text(_["play_3"])
        elif await Resso.valid(url):
            try:
                details, track_id = await Resso.track(url)
            except:
                return await mystic.edit_text(_["play_3"])
            streamtype = "youtube"
            img = details["thumb"]
            cap = _["play_10"].format(details["title"], details["duration_min"])
        elif await SoundCloud.valid(url):
            try:
                details, track_path = await SoundCloud.download(url)
            except:
                return await mystic.edit_text(_["play_3"])
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                return await mystic.edit_text(
                    _["play_6"].format(
                        config.DURATION_LIMIT_MIN,
                        app.mention,
                    )
                )
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="soundcloud",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        else:
            try:
                await Sona.stream_call(url)
            except NoActiveGroupCall:
                await mystic.edit_text(_["black_9"])
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=_["play_17"],
                )
            except Exception as e:
                return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            await mystic.edit_text(_["str_2"])
            try:
                await stream(
                    _,
                    mystic,
                    message.from_user.id,
                    url,
                    chat_id,
                    message.from_user.first_name,
                    message.chat.id,
                    video=video,
                    streamtype="index",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await play_logs(message, streamtype="M3u8 or Index Link")
    else:
        if len(message.command) < 2:
            buttons = botplaylist_markup(_)
            return await mystic.edit_text(
                _["play_18"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        slider = True
        query = message.text.split(None, 1)[1]
        if "-v" in query:
            query = query.replace("-v", "")
        
        # ✅ MODIFIED: Try API first, fallback to YouTube.track()
        try:
            if video:
                details, track_id = await get_video_from_api(query)
            else:
                details, track_id = await get_audio_from_api(query)
            
            # If API failed, use original YouTube.track()
            if not details:
                print("⚠️ [API] Failed, using YouTube.track() fallback")
                details, track_id = await YouTube.track(query)
        except:
            # Fallback to original method
            try:
                details, track_id = await YouTube.track(query)
            except:
                return await mystic.edit_text(_["play_4"])
        
        streamtype = "youtube"
        img = details["thumb"]
        cap = _["play_10"].format(details["title"], details["duration_min"])

    if plist_type:
        ran_hash = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=10)
        )
        lyrical[ran_hash] = plist_id
        buttons = playlist_markup(_, ran_hash, message.from_user.id, plist_type, channel)
        await mystic.delete()
        await message.reply_photo(
            photo=img,
            caption=cap,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return await play_logs(message, streamtype=plist_type)
    else:
        if slider:
            buttons = slider_markup(_, track_id, message.from_user.id, query, track_id)
            await mystic.delete()
            await message.reply_photo(
                photo=img,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return await play_logs(message, streamtype=streamtype)
        else:
            buttons = track_markup(_, track_id, message.from_user.id, channel)
            await mystic.delete()
            await message.reply_photo(
                photo=img,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return await play_logs(message, streamtype=streamtype)
