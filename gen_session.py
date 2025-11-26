from pyrogram import Client

API_ID = "YOUR_API_ID"
API_HASH = "YOUR_API_HASH"

print("Go to https://my.telegram.org to get API_ID and API_HASH")
print("Starting session generation...")

with Client("music_session", api_id=API_ID, api_hash=API_HASH) as app:
    session_string = app.export_session_string()
    print("\n" + "="*50)
    print("YOUR SESSION STRING:")
    print(session_string)
    print("="*50)
    print("\nSave this string in your main bot file!")
