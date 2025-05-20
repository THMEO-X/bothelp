import discord
from discord.ext import commands
import google.generativeai as genai
import openai
import os
import json
import storage
from flask import Flask
from threading import Thread

# Tạo web server giữ bot online cho Render + UptimeRobot
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Lấy API keys từ biến môi trường
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AUTHORIZED_USER_ID = 1299386568712392765  # ID cá nhân của bạn

# Cấu hình AI
openai.api_key = OPENAI_API_KEY
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")

# Cấu hình bot Discord, tắt lệnh help mặc định để không bị lỗi trùng tên
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# File lưu trạng thái kênh có bật AI
STATE_FILE = "channels.json"

def load_channels():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_channels():
    with open(STATE_FILE, "w") as f:
        json.dump(monitored_channels, f)

monitored_channels = load_channels()

@bot.event
async def on_ready():
    print(f"Bot đã đăng nhập với tên {bot.user.name}")
    await bot.change_presence(activity=discord.Game(
        name="!start id channel\n!stop id channel"))

@bot.command()
async def help(ctx):
    await ctx.send("`!start` - id channel\n`!stop` - id channel")

@bot.command()
async def start(ctx, channel_id: int):
    is_owner = ctx.author.id == AUTHORIZED_USER_ID
    is_server_owner = ctx.author.id == ctx.guild.owner_id
    if not (is_owner or is_server_owner):
        await ctx.send("Bạn không có quyền sử dụng lệnh này.")
        return
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send("Không tìm thấy kênh với ID đó.")
        return
    monitored_channels[str(channel_id)] = True
    save_channels()
    await ctx.send(f"AI đã được bật ở <#{channel_id}>.")

@bot.command()
async def stop(ctx, channel_id: int):
    is_owner = ctx.author.id == AUTHORIZED_USER_ID
    is_server_owner = ctx.author.id == ctx.guild.owner_id
    if not (is_owner or is_server_owner):
        await ctx.send("Bạn không có quyền sử dụng lệnh này.")
        return
    if str(channel_id) in monitored_channels:
        del monitored_channels[str(channel_id)]
        save_channels()
        await ctx.send(f"AI đã tắt ở <#{channel_id}>.")
    else:
        await ctx.send("Kênh này chưa được bật AI.")

# Gọi 2 AI (Gemini và GPT) và chọn câu trả lời ngắn gọn nhất
async def generate_best_response(prompt):
    responses = []

    try:
        gemini_result = gemini_model.generate_content(
            f"Trả lời theo hướng logic trình tự dài ngắn tùy trường hợp cần dùng, bằng tiếng Việt nếu được, có thể dùng emoji:\n{prompt}")
        if gemini_result.text:
            responses.append(gemini_result.text.strip())
    except Exception as e:
        print("Gemini lỗi:", e)

    try:
        gpt_result = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Trả lời có logic có thể ngắn dài tùy trường hợp, bằng tiếng Việt nếu có thể, có thể dùng emoji trong câu tất nhiên không phải câu nào cũng dùng emoji:\n{prompt}"}],
            temperature=0.7
        )
        responses.append(gpt_result["choices"][0]["message"]["content"].strip())
    except Exception as e:
        print("GPT lỗi:", e)

    if not responses:
        return "Tôi chưa thể trả lời câu hỏi này."

    best = min(responses, key=lambda x: len(x) + x.count("..."))
    return best

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if str(message.channel.id) in monitored_channels:
        try:
            async with message.channel.typing():  # Hiện trạng thái đang gõ
                user_input = message.content
                reply = await generate_best_response(user_input)
                await message.channel.send(reply)

                history = storage.get("history", [])
                history.append({
                    "user": str(message.author),
                    "channel_id": message.channel.id,
                    "question": user_input,
                    "answer": reply
                })
                storage.set("history", history[-50:])  # Lưu tối đa 50 dòng
        except Exception as e:
            print(f"Lỗi: {e}")
            await message.channel.send("⚠️ Đã xảy ra lỗi khi tạo phản hồi.")

    await bot.process_commands(message)

# Bắt đầu bot và web server
keep_alive()
bot.run(DISCORD_TOKEN)