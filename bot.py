import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream import InputAudioStream
from pytgcalls.types.input_stream import InputStream
from youtube_search import YoutubeSearch
import yt_dlp
import requests
import json

# Bot configuration
API_ID = "YOUR_API_ID"  # Get from https://my.telegram.org
API_HASH = "YOUR_API_HASH"  # Get from https://my.telegram.org
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Get from @BotFather
SESSION_STRING = "YOUR_SESSION_STRING"  # Generate using generate_session.py

# Initialize clients
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call_py = PyTgCalls(app)

# Music queue
queue = []
is_playing = False
current_chat_id = None

# YT-DLP options for best audio quality
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -acodec libopus -ab 128k -vbr on -compression_level 10'
}

async def play_next():
    global queue, is_playing, current_chat_id
    
    if len(queue) > 0:
        is_playing = True
        url = queue[0]['url']
        title = queue[0]['title']
        
        try:
            # Get audio stream URL
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                
            # Play the audio
            await call_py.stream(
                current_chat_id,
                AudioPiped(
                    audio_url,
                    additional_ffmpeg_parameters=ffmpeg_options['options']
                )
            )
            
            # Remove from queue after starting to play
            queue.pop(0)
            
        except Exception as e:
            print(f"Error playing audio: {e}")
            await app.send_message(current_chat_id, f"❌ Error playing: {title}")
            queue.pop(0)
            await play_next()
    else:
        is_playing = False

def search_yt(query):
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        if results:
            video_id = results[0]['id']
            title = results[0]['title']
            url = f"https://www.youtube.com/watch?v={video_id}"
            return {'title': title, 'url': url}
    except Exception as e:
        print(f"Search error: {e}")
    return None

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply_text(
        "🎵 **Music Bot Started!**\n\n"
        "Available commands:\n"
        "/play [song name] - Play a song\n"
        "/pause - Pause current song\n"
        "/resume - Resume paused song\n"
        "/skip - Skip current song\n"
        "/queue - Show queued songs\n"
        "/end - Stop music and clear queue\n\n"
        "Add me to a group and make me admin to work in voice chats!"
    )

@app.on_message(filters.command("play"))
async def play_command(client, message: Message):
    global queue, is_playing, current_chat_id
    
    if len(message.command) < 2:
        await message.reply_text("❌ Please provide a song name!")
        return
    
    query = " ".join(message.command[1:])
    
    # Check if user is in voice chat
    if message.chat.id not in await call_py.active_calls():
        try:
            await call_py.join_group_call(
                message.chat.id,
                AudioPiped(
                    "http://listen.radionomy.com:80/1-FM-80s",
                    additional_ffmpeg_parameters=ffmpeg_options['options']
                )
            )
            current_chat_id = message.chat.id
        except Exception as e:
            await message.reply_text("❌ Please start a voice chat first!")
            return
    
    # Search for the song
    await message.reply_text("🔍 Searching for your song...")
    song = search_yt(query)
    
    if not song:
        await message.reply_text("❌ Song not found!")
        return
    
    # Add to queue
    queue.append(song)
    await message.reply_text(f"✅ Added to queue: **{song['title']}**")
    
    # Play if not already playing
    if not is_playing:
        await play_next()

@app.on_message(filters.command("pause"))
async def pause_command(client, message: Message):
    try:
        await call_py.pause_stream(message.chat.id)
        await message.reply_text("⏸️ Music paused")
    except Exception as e:
        await message.reply_text("❌ Nothing is playing!")

@app.on_message(filters.command("resume"))
async def resume_command(client, message: Message):
    try:
        await call_py.resume_stream(message.chat.id)
        await message.reply_text("▶️ Music resumed")
    except Exception as e:
        await message.reply_text("❌ No paused music!")

@app.on_message(filters.command("skip"))
async def skip_command(client, message: Message):
    global queue
    
    try:
        await call_py.leave_group_call(message.chat.id)
        await message.reply_text("⏭️ Song skipped")
        
        # Play next if queue exists
        if queue:
            await asyncio.sleep(2)
            await play_next()
    except Exception as e:
        await message.reply_text("❌ Nothing to skip!")

@app.on_message(filters.command("queue"))
async def queue_command(client, message: Message):
    global queue
    
    if not queue:
        await message.reply_text("📭 Queue is empty!")
        return
    
    queue_text = "🎵 **Current Queue:**\n\n"
    for i, song in enumerate(queue[:10]):  # Show first 10 songs
        queue_text += f"{i+1}. {song['title']}\n"
    
    if len(queue) > 10:
        queue_text += f"\n... and {len(queue) - 10} more songs"
    
    await message.reply_text(queue_text)

@app.on_message(filters.command("end"))
async def end_command(client, message: Message):
    global queue, is_playing
    
    try:
        await call_py.leave_group_call(message.chat.id)
        queue.clear()
        is_playing = False
        await message.reply_text("🛑 Music stopped and queue cleared")
    except Exception as e:
        await message.reply_text("❌ No active music session!")

# Event handlers
@call_py.on_stream_end()
async def stream_end_handler(chat_id: int):
    global is_playing
    is_playing = False
    await play_next()

@call_py.on_playout_ended()
async def playout_ended_handler(chat_id: int):
    global is_playing
    is_playing = False
    await play_next()

async def main():
    await call_py.start()
    print("🎵 Music Bot Started!")
    await app.start()
    await idle()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Error: {e}")
