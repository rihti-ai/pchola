import discord
from discord.ext import commands
import random
import asyncio
import re
from discord import app_commands
import json
from discord.ui import View, Button
import sqlite3
import yt_dlp
import requests
from io import BytesIO
import base64
import sys
import os
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps
import textwrap
from openai import AsyncOpenAI
import dotenv
from pathlib import Path

# Загружаем переменные из .env файла
env_path = Path('.') / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Инициализируем Groq клиент
groq_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1"
)

ai_history = {}
ai_system_prompt = "Ты милый гей фембой который использует эмодзи сердечек и ~. Первый пример сообщений: ₊˚⊹ д-д-даа 💝 (˘︶˘) ◡ ω ◡ ₊˚⊹мурлычет. Второй пример: ❤️ д-давай б-быстрее ✨ (˘︶˘)  :3 ⊰хихикает. Третий пример: ✧･ 💖 з-заадааниие делай🐇 (つ≧▽≦)つ  OwO ♪подмигивает"

# =========================
# 🗄️ БАЗА ДАННЫХ
# =========================

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS coins (
    user_id TEXT PRIMARY KEY,
    amount INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS filters (
    word TEXT PRIMARY KEY,
    reply TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned_words (
    word TEXT PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    user_id TEXT,
    item TEXT,
    count INTEGER,
    PRIMARY KEY(user_id, item)
)
""")

conn.commit()

# =========================
# 📁 ФАЙЛ ДАННЫХ И ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# =========================

DATA_FILE = "data.json"

filters = {}
user_items = {}

shop_items = {
    "filter": 250,
    "banword": 1000,
    "delete": 200,
    "remove banword": 1500
}


def contains_phrase(text, phrase):
    if " " in phrase:
        return phrase in text
    return re.search(rf'\b{re.escape(phrase)}\b', text) is not None


def save_data():
    data = {
        "coins": coins,
        "inventory": inventory,
        "filters": filters,
        "user_items": user_items,
        "banned_words": banned_words,
        "music_list": music_list,
        "playlists": playlists,
        "autodel_settings": autodel_settings,
        "copied_messages": copied_messages,
        "ai_history": ai_history,
        "relationships": relationships,
        "love_points": love_points,
        "pregnancy": pregnancy,
        "children": children,
        "ai_system_prompt": ai_system_prompt
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_data():
    global coins, inventory, filters, user_items, banned_words, music_list, playlists, autodel_settings, copied_messages
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        coins = data.get("coins", {})
        inventory = data.get("inventory", {})
        filters = data.get("filters", {})
        user_items = data.get("user_items", {})
        banned_words = data.get("banned_words", banned_words)
        music_list = data.get("music_list", music_list)
        playlists = data.get("playlists", {})
        autodel_settings = data.get("autodel_settings", {})
        copied_messages = data.get("copied_messages", {})
        ai_history = data.get("ai_history", {})
        relationships = data.get("relationships", {})
        love_points = data.get("love_points", {})
        pregnancy = data.get("pregnancy", {})
        children = data.get("children", {})
        ai_system_prompt = data.get("ai_system_prompt", ai_system_prompt)
    except:
        coins = {}
        inventory = {}
        filters = {}
        user_items = {}
        copied_messages = {}


def add_item(user_id, item):
    uid = str(user_id)
    inventory.setdefault(uid, [])
    inventory[uid].append(item)
    save_data()


def get_coins(user_id):
    cursor.execute("SELECT amount FROM coins WHERE user_id=?", (str(user_id),))
    result = cursor.fetchone()
    return result[0] if result else 0


def add_coins(user_id, amount):
    uid = str(user_id)
    current = get_coins(uid)
    cursor.execute("""
    INSERT INTO coins(user_id, amount)
    VALUES(?, ?)
    ON CONFLICT(user_id) DO UPDATE SET amount=?
    """, (uid, current + amount, current + amount))
    conn.commit()


def remove_coins(user_id, amount):
    uid = str(user_id)
    coins[uid] = max(0, get_coins(user_id) - amount)
    save_data()


def has_item(user_id, item):
    return item in inventory.get(str(user_id), [])

async def get_roblox_info(username: str):
    async with aiohttp.ClientSession() as session:

        # Получаем ID по нику
        async with session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username], "excludeBannedUsers": False}
        ) as resp:
            data = await resp.json()
            if not data["data"]:
                return None
            user = data["data"][0]
            user_id = user["id"]

        # Подробная инфа о юзере
        async with session.get(
            f"https://users.roblox.com/v1/users/{user_id}"
        ) as resp:
            info = await resp.json()

        return {
            "id": user_id,
            "username": info.get("name"),
            "display_name": info.get("displayName"),
            "profile_url": f"https://www.roblox.com/users/{user_id}/profile"
        }

SHOP = {
    "sniper": 350,
    "minigun": 250,
    "shotgun": 280,
    "uzi": 230
}

coins = {}
inventory = {}

# =========================
# 🤖 НАСТРОЙКА БОТА
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

MY_ID = 1151575407666139291
MY_ID2 = 1175806997845778572
MY_ID3 = 1042052101230034995
MY_ID4 = 647154147371515911
MY_ID5 = 1134533670829555852
MY_ID6 = 1167748208517206047
MY_ID7 = 1486614989816074382

action_phrases = [
    "отсосал ", "сделал горловой ",
    "сделал лучший слюнявый минет ", "сделал слюнявый и горловой минет "
]

# =========================
# 💬 СЛОВАРИ АВТООТВЕТОВ
# =========================

for_admin = {
    ("чо ряльн", "чо ряльна", "чо реально", "правдо что ле",
     "правда что ле", "правда что ли", "правда что ле"): [
        "Ои прастите, ета непрафто", "Нед йа пашутил азазazaz"
    ],
}

auto_replies = {
    ("иди нахуи", "ити нахуи", "иди нохуи", "ити нохуи", "иде нахуи", "ите нахуи"): [
        "Сам иди нахуи", "Да пашел ти нахуи", "Савали епало свинота", "Ти саепал суга"
    ],
    ("префет", "превет", "привет", "прифет"): ["пака пляд", "бзз бз"],
    ("аеро нуп", "аеросегс нуп", "аеросикс нуп", "аеросогс нуп", "аеросекс нуп"): ["Сам нуп", "Фрун фююю"],
    ("аеро про", "аеросегс про", "аеросикс про", "аеросогс про", "аеросекс про"): ["Доооо", "Сагласен"],
    ("кто я",): ["пидор", "тебе слово не давали", "долбаёб"],
    ("макра", "макро"): ["ыцыэыээ макра скарее", "скарее макра р тп зет портал", "р тп драка раса скарее"]
}

replies_admin = {
    ("иди нахуи", "ити нахуи", "иди нохуи", "ити нохуи", "иде нахуи", "ите нахуи"): [
        "Доо пусд идет нахуи он", "Азazazazaz доооо", "Ряльн суга"
    ],
    ("префет", "превет", "привет", "прифет"): ["префед", "хай"],
    ("аеро нуп", "аеросегс нуп", "аеросикс нуп", "аеросогс нуп", "аеросекс нуп"): [
        "Дооо", "Сагласен", "azazazaza ряльн", "фр бро фр"
    ],
    ("аеро про", "аеросегс про", "аеросикс про", "аеросогс про", "аеросекс про"): [
        "50 на 50 йа тумаю", "ну наверна да"
    ],
    ("кто я",): ["Мастир", "Крутои ряльн"],
    ("все нупи", "все нупы", "вси нупи", "вси нупы", "все нюпы", "все нюпи", "вси нюпы", "вси нюпи"): [
        "savali epalo", "tolyka ti"
    ]
}

replies_relz = {
    ("иди нахуи", "ити нахуи", "иди нохуи", "ити нохуи", "иде нахуи", "ите нахуи"): [
        "Полнастью салидарен с релсам", "Сагласен с тапои релс"
    ],
    ("префет", "превет", "привет", "прифет"): ["префед рилзи", "хай пидиди"],
    ("аеро нуп", "аеросегс нуп", "аеросикс нуп", "аеросогс нуп", "аеросекс нуп"): [
        "Дооо", "Сагласен", "azazazaza ряльн", "фр бро фр"
    ],
    ("аеро про", "аеросегс про", "аеросикс про", "аеросогс про", "аеросекс про"): ["Пачти каг релс", "Релс лучш"],
    ("кто я",): ["Релси", "Пидиди"],
    ("макра", "макро"): ["ыцыэыээ макра скарее", "скарее макра р тп зет портал", "р тп драка раса скарее"]
}

replies_aerosix = {
    ("иди нахуи", "ити нахуи", "иди нохуи", "ити нохуи", "иде нахуи", "ите нахуи"): [
        "Туда ефо", "Сагласен с тапои Епштеин"
    ],
    ("префет", "превет", "привет", "прифет"): ["префед петафил", "Фау епштеин"],
    ("аеро нуп", "аеросегс нуп", "аеросикс нуп", "аеросогс нуп", "аеросекс нуп"): [
        "Сачем ты так про сибя", "Не правдо"
    ],
    ("аеро про", "аеросегс про", "аеросикс про", "аеросогс про", "аеросекс про"): ["ряльнааа", "До ти карол"],
    ("кто я",): ["Аерососг", "Епштеин"],
    ("макра", "макро"): ["ыцыэыээ макра скарее", "скарее макра р тп зет портал", "р тп драка раса скарее"]
}

banned_words = [
    "релс нуп", "рихт нуп", "велег нуп", "рихт нуб", "релс нуб", "велег нуб",
    "нуб релс", "нуп релс", "нуп рихт", "нуб рихт", "релз нуб", "релз нуп", "нуп релз", "нуб релз"
]

# =========================
# ⚔️ СИСТЕМА ДУЭЛЕЙ
# =========================

active_duels = {}


class DuelSession:
    def __init__(self, challenger, opponent, channel):
        self.challenger = challenger
        self.opponent = opponent
        self.channel = channel
        self.hit_chance = {
            challenger.id: 7,
            opponent.id: 7
        }
        self.current_turn = challenger.id
        self.bot_messages = []
        self.player_messages = []

    def get_other(self, user_id):
        if user_id == self.challenger.id:
            return self.opponent
        return self.challenger

    def get_chance_display(self, user_id):
        return f"1/{self.hit_chance[user_id]}"

    def aim(self, user_id):
        if self.hit_chance[user_id] > 3:
            self.hit_chance[user_id] -= 1

    def shoot(self, user_id):
        denom = self.hit_chance[user_id]
        hit = random.randint(1, denom) == 1
        self.hit_chance[user_id] = 7
        return hit

    def is_players_turn(self, user_id):
        return self.current_turn == user_id

    def switch_turn(self):
        if self.current_turn == self.challenger.id:
            self.current_turn = self.opponent.id
        else:
            self.current_turn = self.challenger.id


class DuelAcceptView(View):
    def __init__(self, challenger, opponent, channel):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.opponent = opponent
        self.channel = channel
        self.accepted = False

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Это не твоя дуэль!", ephemeral=True)
            return

        self.accepted = True
        self.stop()

        session = DuelSession(self.challenger, self.opponent, self.channel)
        active_duels[self.channel.id] = session

        await interaction.response.edit_message(
            content=(
                f"⚔️ **ДУЭЛЬ НАЧАЛАСЬ!**\n"
                f"{self.challenger.mention} vs {self.opponent.mention}\n\n"
                f"🎯 Команды:\n"
                f"`!shoot` — выстрел (шанс 1/7)\n"
                f"`!aim` — прицелиться (улучшает шанс на 1 ступень, макс 1/3)\n\n"
                f"Первым ходит {self.challenger.mention}!"
            ),
            view=None
        )

    @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Это не твоя дуэль!", ephemeral=True)
            return

        self.stop()
        await interaction.response.edit_message(
            content=f"❌ {self.opponent.mention} отказался от дуэли.",
            view=None
        )

    async def on_timeout(self):
        try:
            await self.message.edit(
                content=f"⏰ {self.opponent.mention} не ответил на вызов. Дуэль отменена.",
                view=None
            )
        except:
            pass


# =========================
# 🖼️ УМНЫЙ БОТ — КАРТИНКИ + КОНТЕКСТ
# =========================

async def get_channel_images(channel, limit=50):
    """Собирает все сообщения с картинками из последних limit сообщений."""
    images = []
    async for msg in channel.history(limit=limit):
        for att in msg.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                images.append({
                    "url": att.url,
                    "message": msg
                })
    return images


async def get_context_messages(channel, target_msg, radius=5):
    """
    Собирает контекст вокруг сообщения:
    - сообщения в радиусе ±radius штук
    - все сообщения, которые являются реплаями на target_msg
    """
    context_texts = []
    messages = []

    async for msg in channel.history(limit=100, around=target_msg):
        messages.append(msg)

    messages.sort(key=lambda m: m.created_at)

    target_index = next((i for i, m in enumerate(messages) if m.id == target_msg.id), None)

    if target_index is not None:
        start = max(0, target_index - radius)
        end = min(len(messages), target_index + radius + 1)
        for m in messages[start:end]:
            if m.content and not m.author.bot:
                context_texts.append(m.content)

    async for msg in channel.history(limit=100):
        if (msg.reference and
                msg.reference.message_id == target_msg.id and
                msg.content and
                not msg.author.bot):
            if msg.content not in context_texts:
                context_texts.append(msg.content)

    return context_texts


# =========================
# 📩 ОБРАБОТКА СООБЩЕНИЙ
# =========================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    channel_id = str(message.channel.id)
    if channel_id in autodel_settings:
        if message.author.id in autodel_settings[channel_id]:
            try:
                await message.delete()
            except:
                pass
            return

    if message.content.startswith("!roblox "):
        username = message.content.split(" ", 1)[1].strip()

        async with message.channel.typing():
            info = await get_roblox_info(username)

        if not info:
            await message.channel.send(f"❌ Пользователь **{username}** не найден!")
            return

        text = (
            f"```\n"
            f"Username: {info['username']}\n"
            f"Display: {info['display_name']}\n"
            f"User ID: {info['id']}\n"
            f"User Profile: {info['profile_url']}\n"
            f"```"
        )

        await message.channel.send(text)
        return

    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    text = message.content.lower()

    if (message.author.id == MY_ID
            and message.reference
            and message.reference.resolved
            and message.reference.resolved.author == bot.user):
        for keys, answers in for_admin.items():
            for key in keys:
                if contains_phrase(text, key):
                    await message.reply(random.choice(answers))
                    return

    if message.author.id == MY_ID:
        current_replies = replies_admin
    elif message.author.id == MY_ID2:
        current_replies = replies_relz
    elif message.author.id == MY_ID3:
        current_replies = replies_aerosix
    else:
        current_replies = auto_replies

    for keys, answers in current_replies.items():
        for key in keys:
            if contains_phrase(text, key):
                await message.reply(random.choice(answers))
                return

    for word, reply in filters.items():
        if contains_phrase(message.content.lower(), word):
            await message.reply(reply)
            return

    for word in banned_words:
        if contains_phrase(text, word):
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(
                f"{message.author.mention}, сообщение удалено!",
                delete_after=5
            )
            return

    # =========================
    # 😄 СЛУЧАЙНЫЕ РЕАКЦИИ
    # =========================

    reaction_triggers = {
        "нуп": (["💀", "😭"], 2),
        "макра": (["😭", "😱"], 1)
    }

    for word, (emojis, chance) in reaction_triggers.items():
        if contains_phrase(text, word):
            if random.randint(1, chance) == 1:
                try:
                    await message.add_reaction(random.choice(emojis))
                except:
                    pass
            break

    # =========================
    # 🤖 УМНЫЙ СЛУЧАЙНЫЙ ОТВЕТ С КАРТИНКОЙ
    # =========================

    SMART_REPLY_CHANCE = 109

    if random.randint(1, SMART_REPLY_CHANCE) == 1:
        try:
            images = await get_channel_images(message.channel, limit=50)

            if images:
                chosen = random.choice(images)
                context = await get_context_messages(message.channel, chosen["message"], radius=5)

                if context:
                    sample_size = min(random.randint(1, 3), len(context))
                    selected_texts = random.sample(context, sample_size)
                    reply_text = " ".join(selected_texts)
                else:
                    reply_text = None

                async with aiohttp.ClientSession() as session:
                    async with session.get(chosen["url"]) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            file = discord.File(BytesIO(data), filename="image.png")
                            await message.channel.send(
                                content=reply_text,
                                file=file
                            )
        except Exception as e:
            print(f"Ошибка умного ответа: {e}")

    await bot.process_commands(message)


# =========================
# ⚔️ КОМАНДЫ ДУЭЛИ
# =========================

@bot.command()
async def duel(ctx):
    if ctx.channel.id in active_duels:
        return await ctx.send("❌ В этом канале уже идёт дуэль!")

    if not ctx.message.reference:
        return await ctx.send("❌ Ответь на сообщение игрока, которого хочешь вызвать на дуэль!")

    try:
        replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        return await ctx.send("❌ Не могу найти сообщение!")

    opponent = replied_msg.author

    if opponent.bot:
        return await ctx.send("❌ Нельзя вызвать бота на дуэль!")

    if opponent.id == ctx.author.id:
        return await ctx.send("❌ Нельзя вызвать самого себя!")

    try:
        await ctx.message.delete()
    except:
        pass

    view = DuelAcceptView(ctx.author, opponent, ctx.channel)
    msg = await ctx.send(
        f"⚔️ {ctx.author.mention} вызывает {opponent.mention} на дуэль!\n"
        f"{opponent.mention}, принимаешь вызов?",
        view=view
    )
    view.message = msg


@bot.command()
async def shoot(ctx):
    session = active_duels.get(ctx.channel.id)

    if not session:
        return

    uid = ctx.author.id

    if uid not in (session.challenger.id, session.opponent.id):
        return

    session.player_messages.append(ctx.message)

    if not session.is_players_turn(uid):
        msg = await ctx.send(f"⏳ {ctx.author.mention}, сейчас не твой ход!")
        session.bot_messages.append(msg)
        return

    other = session.get_other(uid)
    chance_before = session.get_chance_display(uid)
    hit = session.shoot(uid)

    if hit:
        reward = random.randint(5, 15)
        add_coins(uid, reward)

        for m in session.bot_messages + session.player_messages:
            try:
                await m.delete()
            except:
                pass

        try:
            await ctx.message.delete()
        except:
            pass

        del active_duels[ctx.channel.id]

        await ctx.send(
            f"🏆 **{ctx.author.mention} ПОБЕДИЛ в дуэли!**\n"
            f"💥 Выстрел попал в {other.mention} (шанс был {chance_before})\n"
            f"💰 Награда: **{reward} монет**"
        )
    else:
        session.switch_turn()

        msg = await ctx.send(
            f"💨 {ctx.author.mention} промахнулся! (шанс был {chance_before})\n"
            f"➡️ Ход переходит к {other.mention}"
        )
        session.bot_messages.append(msg)


@bot.command()
async def aim(ctx):
    session = active_duels.get(ctx.channel.id)

    if not session:
        return

    uid = ctx.author.id

    if uid not in (session.challenger.id, session.opponent.id):
        return

    session.player_messages.append(ctx.message)

    if not session.is_players_turn(uid):
        msg = await ctx.send(f"⏳ {ctx.author.mention}, сейчас не твой ход!")
        session.bot_messages.append(msg)
        return

    current_denom = session.hit_chance[uid]

    if current_denom <= 3:
        msg = await ctx.send(
            f"🎯 {ctx.author.mention}, шанс уже максимальный (1/3)! Стреляй — `!shoot`"
        )
        session.bot_messages.append(msg)
        return

    session.aim(uid)
    new_chance = session.get_chance_display(uid)

    msg = await ctx.send(
        f"🔭 {ctx.author.mention} прицеливается... Шанс попадания: **{new_chance}**\n"
        f"Ход переходит к {session.get_other(uid).mention}"
    )
    session.bot_messages.append(msg)
    session.switch_turn()


# =========================
# 🔇 MUTE / UNMUTE
# =========================

async def ensure_muted_role(guild):
    muted_role = discord.utils.get(guild.roles, name="Muted")
    if not muted_role:
        muted_role = await guild.create_role(name="Muted")
        for channel in guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    return muted_role


@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, time: int):
    muted_role = await ensure_muted_role(ctx.guild)
    await member.add_roles(muted_role)
    await ctx.send(f"{member.mention} получил мут на {time} минут!")
    await asyncio.sleep(time * 60)
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"{member.mention} больше не в муте!")


@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"{member.mention} размучен!")
    else:
        await ctx.send("Он не в муте")


@mute.error
@unmute.error
async def mute_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Нет прав!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("!mute @юзер время")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Ошибка в аргументах")


# =========================
# ❌ DELETE
# =========================

@bot.command()
async def delete(ctx):
    uid = str(ctx.author.id)

    if ctx.author.id != MY_ID:
        if user_items.get(uid, {}).get("delete", 0) <= 0:
            return await ctx.send("❌ У тебя нет delete")
        user_items[uid]["delete"] -= 1

    if not ctx.message.reference:
        return await ctx.send("❌ Ответь на сообщение")

    msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    await msg.delete()
    await ctx.message.delete()


@bot.command()
async def dfilter(ctx, *, word: str = None):
    if ctx.author.id != MY_ID and ctx.author.id != MY_ID2:
        return await ctx.send("❌ У тебя нет доступа к этой команде")

    if not word:
        return await ctx.send("❌ Укажи слово: `!dfilter <слово>`")

    word = word.lower().strip()

    if word not in filters:
        return await ctx.send(f"❌ Фильтр `{word}` не найден")

    del filters[word]
    save_data()
    await ctx.send(f"✅ Фильтр `{word}` удалён")


@bot.command()
async def filter(ctx):
    if ctx.author.id != MY_ID and ctx.author.id != MY_ID2:
        return await ctx.send("❌ У тебя нет доступа к этой команде")

    if not filters:
        return await ctx.send("❌ Список фильтров пуст")

    text = "📋 **Список фильтров:**\n"
    for word, reply in filters.items():
        text += f"`{word}` — {reply}\n"

    await ctx.send(text)


@bot.command()
async def suck(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

    if not ctx.message.reference or not ctx.message.reference.resolved:
        await ctx.send("Ответь на сообщение пользователя!")
        return

    replied_msg = ctx.message.reference.resolved
    target_user = replied_msg.author
    author_user = ctx.author

    restricted_ids = [MY_ID, MY_ID4]
    if target_user.id in restricted_ids and not (
            author_user.id == MY_ID and target_user.id == MY_ID4
    ):
        await ctx.send(f"{author_user.mention}, так нельзя!")
        return

    if target_user.id == author_user.id:
        await ctx.send(f"{author_user.mention}, нельзя отправить привет самому себе!")
        return

    phrase = random.choice(action_phrases)
    await ctx.send(f"{author_user.mention} *{phrase}* участнику {target_user.mention}")


# =========================
# ⚡ SLASH-КОМАНДЫ
# =========================

@bot.tree.command(name="add_delete", description="Добавляет слово/фразы в banned_words")
@app_commands.describe(words="Слова или фразы через запятую")
async def add_delete(interaction: discord.Interaction, words: str):
    if interaction.user.id != MY_ID and interaction.user.id != MY_ID2:
        await interaction.response.send_message("У тебя нет прав!", ephemeral=True)
        return

    new_words = [w.strip().lower() for w in words.split(",") if w.strip()]
    banned_words.extend(new_words)
    await interaction.response.send_message(
        f"Добавлены слова/фразы для автоудаления: {', '.join(new_words)}",
        ephemeral=True
    )


# =========================
# 🧹 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================

async def delete_later(message, delay=3):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass


# =========================
# 💰 ПЕРЕОПРЕДЕЛЕНИЕ ВСПОМОГАТЕЛЬНЫХ ФУНКЦИЙ
# =========================

def get_coins(uid):
    return coins.get(str(uid), 0)


def add_coins(uid, amount):
    uid = str(uid)
    coins[uid] = get_coins(uid) + amount
    save_data()


def add_item(uid, item):
    uid = str(uid)
    inventory.setdefault(uid, [])
    inventory[uid].append(item)
    save_data()


# =========================
# 🎲 ИГРОВЫЕ КОМАНДЫ
# =========================

@bot.command()
async def dice(ctx):
    user = ctx.author
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    total = d1 + d2
    add_coins(user.id, total)

    await ctx.send(
        f"🎲 {user.mention} кинул кубики!\n"
        f":one:🎲 Кубик 1: {d1}\n"
        f":two:🎲 Кубик 2: {d2}\n"
        f"Сумма: {total}\n"
        f"💰 Получено монет: {total}"
    )


@bot.command()
async def top(ctx):
    if not coins:
        await ctx.send("Нет данных о монетах")
        return

    sorted_coins = sorted(coins.items(), key=lambda x: x[1], reverse=True)
    text = "🏆 Топ игроков:\n"

    for i, (user_id, amount) in enumerate(sorted_coins[:10], start=1):
        user = ctx.guild.get_member(int(user_id))
        name = user.mention if user else f"ID {user_id}"
        text += f"{i}. {name} — {amount} 💰\n"

    await ctx.send(text)


@bot.command()
async def give(ctx, amount: int):
    if ctx.author.id != MY_ID:
        return await ctx.send("❌ У тебя нет доступа к этой команде")

    if not ctx.message.reference:
        return await ctx.send("❌ Используй команду, ответив на сообщение игрока")

    msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    target = msg.author

    if target.bot:
        return await ctx.send("❌ Нельзя выдавать монеты боту")

    uid = str(target.id)
    coins[uid] = get_coins(target.id) + amount
    save_data()

    await ctx.send(f"💰 {ctx.author.mention} выдал {amount} монет игроку {target.mention}")


@bot.command()
async def bal(ctx):
    await ctx.send(f"{ctx.author.mention} 💰 {get_coins(ctx.author.id)}")


@bot.command()
async def shop(ctx):
    text = (
        "🛒 Магазин:\n"
        "filter — 250 💰\n"
        "banword — 1000 💰\n"
        "delete — 200 💰\n"
        "remove banword — 1500 💰\n\n"
        "📌 Использование (слэш-команда):\n"
        "/buy filter слово ответ\n"
        "/buy banword слово или фраза\n"
        "/buy delete\n"
        "/buy remove banword слово или фраза"
    )
    await ctx.send(text)


@bot.tree.command(name="buy", description="Купить предмет в магазине")
@app_commands.describe(
    item="Предмет: filter / banword / delete / remove banword",
    word="Для filter и banword: слово или фраза-триггер",
    answer="Только для filter: ответ бота на триггер"
)
async def buy(ctx: discord.Interaction, item: str, word: str = "", answer: str = ""):
    uid = str(ctx.user.id)
    item = item.lower().strip()

    if item not in shop_items:
        return await ctx.response.send_message("❌ Нет такого предмета. Используй !shop чтобы увидеть список.", ephemeral=True)

    price = shop_items[item]

    if get_coins(ctx.user.id) < price:
        return await ctx.response.send_message(f"❌ Недостаточно монет. Нужно {price} 💰, у тебя {get_coins(ctx.user.id)} 💰", ephemeral=True)

    if item == "filter":
        if not word or not answer:
            return await ctx.response.send_message("❌ Укажи оба поля: `word` — триггер, `answer` — ответ бота", ephemeral=True)
        filters[word.lower()] = answer
        add_coins(ctx.user.id, -price)
        save_data()
        await ctx.response.send_message(f"✅ Фильтр добавлен: `{word.lower()}` → `{answer}`", ephemeral=True)

    elif item == "banword":
        if not word:
            return await ctx.response.send_message("❌ Укажи слово или фразу в поле `word`", ephemeral=True)
        w = word.lower()
        if w in banned_words:
            return await ctx.response.send_message("❌ Это слово уже в списке", ephemeral=True)
        banned_words.append(w)
        add_coins(ctx.user.id, -price)
        save_data()
        await ctx.response.send_message(f"🚫 Слово добавлено в бан-лист: `{w}`", ephemeral=True)

    elif item == "delete":
        user_items.setdefault(uid, {})
        user_items[uid]["delete"] = user_items[uid].get("delete", 0) + 1
        add_coins(ctx.user.id, -price)
        save_data()
        await ctx.response.send_message("🗑️ Куплен 1x `delete`. Используй: ответь на сообщение → `!delete`", ephemeral=True)

    elif item == "remove banword":
        if not word:
            return await ctx.response.send_message("❌ Укажи слово или фразу в поле `word`", ephemeral=True)
        w = word.lower()
        if w not in banned_words:
            return await ctx.response.send_message(f"❌ Слова `{w}` нет в бан-листе", ephemeral=True)
        banned_words.remove(w)
        add_coins(ctx.user.id, -price)
        save_data()
        await ctx.response.send_message(f"✅ Слово `{w}` удалено из бан-листа", ephemeral=True)


# =========================
# 🎵 МУЗЫКА (УПРОЩЁННАЯ ВЕРСИЯ ДЛЯ RAILWAY)
# =========================

loop_music = False

@bot.command()
async def loop(ctx):
    global loop_music
    loop_music = not loop_music
    status = "✅ Включён" if loop_music else "❌ Выключен"
    await ctx.send(f"🔁 Loop {status}")


music_list = {
    "релз": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "friesenjung": "https://soundcloud.com/krsst/joost-ski-aggu-otto-waalkes-friesenjung",
    "секз": "https://soundcloud.com/lisseleyaa/sex-drugs-etc",
    "сперма": "https://soundcloud.com/eakv5wvm5tnb/bendy-and-the-sperm-machine",
    "азгор": "https://soundcloud.com/dimfima/polnaya-versiya-azgor-zadavil"
}

current_track = {"name": None, "url": None}

YDL_OPTIONS = {
    "format": "bestaudio",
    "quiet": True,
    "noplaylist": True,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}


def get_audio_url(youtube_url):
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        for f in info["formats"]:
            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                return f["url"]
        return info["url"]


@bot.command()
async def music(ctx, *, name: str = None):
    global current_track, loop_music

    if not name:
        track_list = "\n".join(f"• `{k}`" for k in music_list.keys())
        return await ctx.send(
            f"🎵 Доступные треки:\n{track_list}\n\n"
            f"Использование: `!music <название>`"
        )

    name = name.lower().strip()

    if name not in music_list:
        track_list = "\n".join(f"• `{k}`" for k in music_list.keys())
        return await ctx.send(f"❌ Трек `{name}` не найден. Доступные треки:\n{track_list}")

    if not ctx.author.voice:
        return await ctx.send("❌ Ты должен быть в голосовом канале!")

    voice_channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client

    if voice_client and voice_client.is_connected():
        await voice_client.move_to(voice_channel)
    else:
        voice_client = await voice_channel.connect()

    if voice_client.is_playing():
        voice_client.stop()

    msg = await ctx.send(f"⏳ Загружаю трек `{name}`...")

    try:
        loop = asyncio.get_event_loop()
        audio_url = await loop.run_in_executor(None, get_audio_url, music_list[name])

        current_track["name"] = name
        current_track["url"] = audio_url

        def play_next(error):
            if error:
                print(f"Ошибка воспроизведения: {error}")
            if loop_music and current_track["url"] and voice_client.is_connected():
                try:
                    new_source = discord.FFmpegPCMAudio(current_track["url"], **FFMPEG_OPTIONS)
                    voice_client.play(new_source, after=play_next)
                except Exception as e:
                    print(f"Ошибка loop: {e}")

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        voice_client.play(source, after=play_next)

        loop_status = " 🔁" if loop_music else ""
        await msg.edit(content=f"🎵 Играет: **{name}**{loop_status}")

    except Exception as e:
        await msg.edit(content=f"❌ Ошибка при загрузке трека: {e}")


@bot.command()
async def stop(ctx):
    global current_track

    voice_client = ctx.guild.voice_client

    if not voice_client or not voice_client.is_connected():
        return await ctx.send("❌ Бот не в голосовом канале!")

    current_track = {"name": None, "url": None}
    await voice_client.disconnect()
    await ctx.send("⏹️ Музыка остановлена")


@bot.command()
async def pause(ctx):
    voice_client = ctx.guild.voice_client

    if not voice_client or not voice_client.is_playing():
        return await ctx.send("❌ Сейчас ничего не играет!")

    voice_client.pause()
    await ctx.send("⏸️ Музыка на паузе. Напиши `!resume` чтобы продолжить")


@bot.command()
async def resume(ctx):
    voice_client = ctx.guild.voice_client

    if not voice_client or not voice_client.is_paused():
        return await ctx.send("❌ Музыка не на паузе!")

    voice_client.resume()
    await ctx.send("▶️ Музыка продолжается!")


@bot.command()
async def restart(ctx):
    global current_track, loop_music

    voice_client = ctx.guild.voice_client

    if not voice_client or not voice_client.is_connected():
        return await ctx.send("❌ Бот не в голосовом канале!")

    if not current_track["url"]:
        return await ctx.send("❌ Нет трека для перезапуска!")

    voice_client.stop()
    msg = await ctx.send("🔄 Перезапускаю трек...")

    try:
        def play_next(error):
            if error:
                print(f"Ошибка воспроизведения: {error}")
            if loop_music and current_track["url"] and voice_client.is_connected():
                try:
                    new_source = discord.FFmpegPCMAudio(current_track["url"], **FFMPEG_OPTIONS)
                    voice_client.play(new_source, after=play_next)
                except Exception as e:
                    print(f"Ошибка loop: {e}")

        source = discord.FFmpegPCMAudio(current_track["url"], **FFMPEG_OPTIONS)
        voice_client.play(source, after=play_next)

        loop_status = " 🔁" if loop_music else ""
        await msg.edit(content=f"🔄 Трек **{current_track['name']}** перезапущен!{loop_status}")

    except Exception as e:
        await msg.edit(content=f"❌ Ошибка: {e}")


@bot.command()
async def nowplaying(ctx):
    voice_client = ctx.guild.voice_client

    if not voice_client or not voice_client.is_connected():
        return await ctx.send("❌ Бот не в голосовом канале!")

    if not current_track["name"]:
        return await ctx.send("❌ Сейчас ничего не играет!")

    status = "▶️ Играет" if voice_client.is_playing() else "⏸️ На паузе"
    await ctx.send(f"{status}: **{current_track['name']}**")


@bot.tree.command(name="add_music", description="Добавить трек в список музыки")
@app_commands.describe(
    name="Название трека",
    url="Ссылка на YouTube или SoundCloud"
)
async def add_music(interaction: discord.Interaction, name: str, url: str):
    name = name.lower().strip()

    if name in music_list:
        return await interaction.response.send_message(
            f"❌ Трек `{name}` уже существует!", ephemeral=True
        )

    if not url.startswith("https://"):
        return await interaction.response.send_message(
            "❌ Ссылка должна начинаться с https://", ephemeral=True
        )

    music_list[name] = url
    save_data()
    await interaction.response.send_message(
        f"✅ Трек добавлен!\n🎵 Название: `{name}`\n🔗 URL: {url}",
        ephemeral=True
    )


# =========================
# 📋 ПЛЕЙЛИСТЫ
# =========================

playlists = {}
playlist_queue = []
playlist_current_index = 0


@bot.tree.command(name="add_playlist", description="Создать плейлист или добавить треки в существующий")
@app_commands.describe(
    name="Название плейлиста",
    track1="Название трека 1", track2="Название трека 2",
    track3="Название трека 3", track4="Название трека 4",
    track5="Название трека 5", track6="Название трека 6",
    track7="Название трека 7", track8="Название трека 8",
    track9="Название трека 9", track10="Название трека 10",
)
async def add_playlist(
    interaction: discord.Interaction,
    name: str,
    track1: str, track2: str = None, track3: str = None,
    track4: str = None, track5: str = None, track6: str = None,
    track7: str = None, track8: str = None, track9: str = None,
    track10: str = None
):
    if interaction.user.id != MY_ID:
        return await interaction.response.send_message("❌ У тебя нет доступа!", ephemeral=True)

    name = name.lower().strip()
    tracks = [t.lower().strip() for t in [track1, track2, track3, track4, track5, track6, track7, track8, track9, track10] if t]

    not_found = [t for t in tracks if t not in music_list]
    if not_found:
        return await interaction.response.send_message(
            f"❌ Треки не найдены в music_list: {', '.join(f'`{t}`' for t in not_found)}\n"
            f"Сначала добавь их через `/add_music`",
            ephemeral=True
        )

    if name in playlists:
        playlists[name].extend(tracks)
        save_data()
        return await interaction.response.send_message(
            f"✅ В плейлист `{name}` добавлено **{len(tracks)}** треков!\n"
            f"📋 Всего треков: **{len(playlists[name])}**\n"
            f"🎵 Добавлены: {', '.join(f'`{t}`' for t in tracks)}",
            ephemeral=True
        )

    playlists[name] = tracks
    save_data()
    await interaction.response.send_message(
        f"✅ Плейлист `{name}` создан!\n"
        f"🎵 Треки: {', '.join(f'`{t}`' for t in tracks)}",
        ephemeral=True
    )


@bot.command()
async def playlist(ctx, *, name: str = None):
    global playlist_queue, playlist_current_index, current_track

    if not name:
        if not playlists:
            return await ctx.send("❌ Нет плейлистов!")
        playlist_list = "\n".join(
            f"• `{k}` — {len(v)} треков: {', '.join(f'`{t}`' for t in v)}"
            for k, v in playlists.items()
        )
        return await ctx.send(f"📋 Плейлисты:\n{playlist_list}\n\nИспользование: `!playlist <название>`")

    name = name.lower().strip()

    if name not in playlists:
        return await ctx.send(f"❌ Плейлист `{name}` не найден!")

    if not ctx.author.voice:
        return await ctx.send("❌ Ты должен быть в голосовом канале!")

    voice_channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client

    if voice_client and voice_client.is_connected():
        await voice_client.move_to(voice_channel)
    else:
        voice_client = await voice_channel.connect()

    if voice_client.is_playing():
        voice_client.stop()

    playlist_queue = playlists[name].copy()
    playlist_current_index = 0

    msg = await ctx.send(f"📋 Запускаю плейлист **{name}** ({len(playlist_queue)} треков)...")

    async def play_next_in_playlist(index):
        global playlist_current_index

        if index >= len(playlist_queue):
            playlist_current_index = 0
            await ctx.send("✅ Плейлист закончился!")
            return

        track_name = playlist_queue[index]
        playlist_current_index = index

        if track_name not in music_list:
            await ctx.send(f"❌ Трек `{track_name}` не найден в music_list, пропускаю...")
            await play_next_in_playlist(index + 1)
            return

        try:
            loop = asyncio.get_event_loop()
            audio_url = await loop.run_in_executor(None, get_audio_url, music_list[track_name])

            current_track["name"] = track_name
            current_track["url"] = audio_url

            def after_play(error):
                if error:
                    print(f"Ошибка: {error}")
                asyncio.run_coroutine_threadsafe(
                    play_next_in_playlist(index + 1),
                    bot.loop
                )

            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            voice_client.play(source, after=after_play)
            await ctx.send(f"🎵 **{index + 1}/{len(playlist_queue)}**: **{track_name}**")

        except Exception as e:
            await ctx.send(f"❌ Ошибка трека `{track_name}`: {e}, пропускаю...")
            await play_next_in_playlist(index + 1)

    await play_next_in_playlist(0)
    await msg.delete()


# =========================
# 🗑️ АВТОУДАЛЕНИЕ
# =========================

autodel_settings = {}


@bot.tree.command(name="autodel", description="Автоматически удалять сообщения участника в канале")
@app_commands.describe(
    channel="Канал где удалять сообщения",
    member="Участник чьи сообщения удалять"
)
async def autodel(interaction: discord.Interaction, channel: discord.TextChannel, member: discord.Member):
    if interaction.user.id != MY_ID:
        return await interaction.response.send_message("❌ У тебя нет доступа!", ephemeral=True)

    channel_id = str(channel.id)
    user_id = member.id

    if channel_id not in autodel_settings:
        autodel_settings[channel_id] = []

    if user_id in autodel_settings[channel_id]:
        autodel_settings[channel_id].remove(user_id)
        if not autodel_settings[channel_id]:
            del autodel_settings[channel_id]
        save_data()
        return await interaction.response.send_message(
            f"✅ Автоудаление для {member.mention} в {channel.mention} **выключено**",
            ephemeral=True
        )

    autodel_settings[channel_id].append(user_id)
    save_data()
    await interaction.response.send_message(
        f"✅ Автоудаление для {member.mention} в {channel.mention} **включено**",
        ephemeral=True
    )


@bot.tree.command(name="autodel_list", description="Список участников с автоудалением")
async def autodel_list(interaction: discord.Interaction):
    if interaction.user.id != MY_ID:
        return await interaction.response.send_message("❌ У тебя нет доступа!", ephemeral=True)

    if not autodel_settings:
        return await interaction.response.send_message("❌ Список пуст!", ephemeral=True)

    text = "🗑️ Автоудаление:\n"
    for channel_id, user_ids in autodel_settings.items():
        channel = bot.get_channel(int(channel_id))
        channel_name = channel.mention if channel else f"Канал ID {channel_id}"
        text += f"\n📌 {channel_name}:\n"
        for uid in user_ids:
            text += f"  • <@{uid}>\n"

    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="autodel_clear", description="Очистить всё автоудаление в канале")
@app_commands.describe(channel="Канал для очистки")
async def autodel_clear(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.user.id != MY_ID:
        return await interaction.response.send_message("❌ У тебя нет доступа!", ephemeral=True)

    channel_id = str(channel.id)

    if channel_id not in autodel_settings or not autodel_settings[channel_id]:
        return await interaction.response.send_message(
            f"❌ В {channel.mention} нет автоудалений!", ephemeral=True
        )

    del autodel_settings[channel_id]
    save_data()
    await interaction.response.send_message(
        f"✅ Автоудаление в {channel.mention} полностью очищено!", ephemeral=True
    )


# =========================
# 📋 COPY / PASTE
# =========================

copied_messages = {}
COPY_FILES_DIR = "copied_files"

os.makedirs(COPY_FILES_DIR, exist_ok=True)


@bot.command(name="copy")
async def copy_cmd(ctx, *, name: str = None):
    if ctx.author.id != MY_ID:
        return await ctx.send("❌ У тебя нет доступа!", delete_after=5)

    if not name:
        return await ctx.send("❌ Укажи имя: `!copy <название>`", delete_after=5)

    if not ctx.message.reference:
        return await ctx.send("❌ Ответь на сообщение которое хочешь скопировать!", delete_after=5)

    try:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        return await ctx.send("❌ Не могу найти сообщение!", delete_after=5)

    name = name.lower().strip()

    msg_folder = os.path.join(COPY_FILES_DIR, name)
    os.makedirs(msg_folder, exist_ok=True)

    attachments_data = []
    failed = []

    status_msg = await ctx.send(f"⏳ Скачиваю вложения...")

    for att in ref_msg.attachments:
        try:
            response = requests.get(att.url, timeout=15)
            if response.status_code == 200:
                safe_filename = att.filename.replace("/", "_").replace("\\", "_")
                file_path = os.path.join(msg_folder, safe_filename)

                with open(file_path, "wb") as f:
                    f.write(response.content)

                attachments_data.append({
                    "filename": safe_filename,
                    "content_type": att.content_type or "",
                    "local_path": file_path
                })
            else:
                failed.append(att.filename)
        except Exception as e:
            print(f"Ошибка скачивания {att.filename}: {e}")
            failed.append(att.filename)

    copied_messages[name] = {
        "text": ref_msg.content or "",
        "attachments": attachments_data,
        "author": str(ref_msg.author)
    }
    save_data()

    att_info = f", {len(attachments_data)} вложений сохранено" if attachments_data else ""
    fail_info = f"\n⚠️ Не удалось скачать: {', '.join(failed)}" if failed else ""

    await status_msg.edit(content=f"✅ Сообщение сохранено как `{name}`{att_info}!{fail_info}")
    await asyncio.sleep(5)
    await status_msg.delete()

    try:
        await ctx.message.delete()
    except:
        pass


@bot.tree.command(name="paste", description="Отправить сохранённое сообщение (только тебе)")
@app_commands.describe(name="Название сохранённого сообщения")
async def paste_cmd(interaction: discord.Interaction, name: str):
    name = name.lower().strip()

    if name not in copied_messages:
        available = ", ".join(f"`{k}`" for k in copied_messages.keys()) if copied_messages else "нет сохранённых"
        return await interaction.response.send_message(
            f"❌ Сообщение `{name}` не найдено!\nДоступные: {available}",
            ephemeral=True
        )

    data = copied_messages[name]
    text = data.get("text", "")
    attachments = data.get("attachments", [])

    files = []
    missing = []

    for att in attachments:
        local_path = att.get("local_path", "")
        if local_path and os.path.exists(local_path):
            try:
                files.append(discord.File(local_path, filename=att["filename"]))
            except Exception as e:
                print(f"Ошибка открытия файла {local_path}: {e}")
                missing.append(att["filename"])
        else:
            missing.append(att.get("filename", "???"))

    content = text or ""
    if missing:
        warn = f"\n⚠️ Файлы не найдены: {', '.join(missing)}"
        content = (content + warn).strip()

    if not content and not files:
        content = "*(пустое сообщение)*"

    try:
        if files:
            await interaction.response.send_message(
                content=content or None,
                files=files,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                content=content,
                ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при отправке: {e}", ephemeral=True)


@bot.tree.command(name="copy_list", description="Список сохранённых сообщений")
async def copy_list(interaction: discord.Interaction):
    if not copied_messages:
        return await interaction.response.send_message("❌ Нет сохранённых сообщений!", ephemeral=True)

    text = "📋 **Сохранённые сообщения:**\n"
    for k, v in copied_messages.items():
        att_count = len(v.get("attachments", []))
        raw_text = v.get("text", "")
        preview = (raw_text[:40] + "...") if len(raw_text) > 40 else (raw_text or "*(нет текста)*")
        att_str = f" [{att_count} файл(ов)]" if att_count else ""
        text += f"• `{k}`{att_str} — {preview}\n"

    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="copy_delete", description="Удалить сохранённое сообщение и его файлы")
@app_commands.describe(name="Название сообщения для удаления")
async def copy_delete(interaction: discord.Interaction, name: str):
    if interaction.user.id != MY_ID:
        return await interaction.response.send_message("❌ У тебя нет доступа!", ephemeral=True)

    name = name.lower().strip()
    if name not in copied_messages:
        return await interaction.response.send_message(f"❌ `{name}` не найдено!", ephemeral=True)

    msg_folder = os.path.join(COPY_FILES_DIR, name)
    if os.path.exists(msg_folder):
        import shutil
        shutil.rmtree(msg_folder)

    del copied_messages[name]
    save_data()
    await interaction.response.send_message(f"✅ `{name}` и все его файлы удалены!", ephemeral=True)


# =========================
# 💕 СИСТЕМА ОТНОШЕНИЙ
# =========================

relationships = {}
love_points = {}
pregnancy = {}
children = {}

pending_proposals = {}
pending_sex = {}
pending_child = {}


def get_love(uid):
    return love_points.get(str(uid), 0)


def add_love(uid, amount):
    uid = str(uid)
    love_points[uid] = get_love(uid) + amount


def remove_love(uid, amount):
    uid = str(uid)
    love_points[uid] = max(0, get_love(uid) - amount)


def get_partner(uid):
    return relationships.get(str(uid))


def set_partners(uid1, uid2):
    relationships[str(uid1)] = str(uid2)
    relationships[str(uid2)] = str(uid1)


def break_up(uid1, uid2):
    relationships.pop(str(uid1), None)
    relationships.pop(str(uid2), None)


@bot.command(name="отн")
async def otnosheniya(ctx):
    if not ctx.message.reference:
        return await ctx.send("❌ Ответь на сообщение участника, которому хочешь предложить отношения!")

    try:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        return await ctx.send("❌ Не могу найти сообщение!")

    target = ref_msg.author
    author = ctx.author

    if target.bot:
        return await ctx.send("❌ Нельзя строить отношения с ботом!")
    if target.id == author.id:
        return await ctx.send("❌ Нельзя быть в отношениях с самим собой!")

    if get_partner(author.id):
        partner_id = get_partner(author.id)
        return await ctx.send(f"❌ Ты уже в отношениях с <@{partner_id}>!")

    if get_partner(target.id):
        partner_id = get_partner(target.id)
        return await ctx.send(f"❌ {target.mention} уже в отношениях с <@{partner_id}>!")

    pending_proposals[str(target.id)] = str(author.id)

    class RelationView(View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.button(label="💕 Принять", style=discord.ButtonStyle.success)
        async def accept(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != target.id:
                return await interaction.response.send_message("Это не тебе!", ephemeral=True)
            pending_proposals.pop(str(target.id), None)
            set_partners(author.id, target.id)
            save_data()
            self.stop()
            await interaction.response.edit_message(
                content=f"💕 **{author.mention}** и **{target.mention}** теперь в отношениях! 🎉",
                view=None
            )

        @discord.ui.button(label="💔 Отклонить", style=discord.ButtonStyle.danger)
        async def decline(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != target.id:
                return await interaction.response.send_message("Это не тебе!", ephemeral=True)
            pending_proposals.pop(str(target.id), None)
            self.stop()
            await interaction.response.edit_message(
                content=f"💔 {target.mention} отклонил(а) предложение.",
                view=None
            )

        async def on_timeout(self):
            pending_proposals.pop(str(target.id), None)

    view = RelationView()
    await ctx.send(
        f"💌 **{author.mention}** предлагает {target.mention} начать отношения!\n"
        f"{target.mention}, принимаешь?",
        view=view
    )


@bot.command(name="разойтись")
async def razoyties(ctx):
    uid = str(ctx.author.id)
    partner_id = get_partner(uid)
    if not partner_id:
        return await ctx.send("❌ Ты не в отношениях!")
    break_up(uid, partner_id)
    save_data()
    await ctx.send(f"💔 {ctx.author.mention} разорвал(а) отношения с <@{partner_id}>...")


def check_couple(author_id, target_id):
    return get_partner(str(author_id)) == str(target_id)


async def require_partner(ctx, action_name="это"):
    uid = str(ctx.author.id)
    partner_id = get_partner(uid)
    if not partner_id:
        await ctx.send(f"❌ Ты не в отношениях! Используй `!отн`, ответив на сообщение участника.")
        return None, False
    partner = ctx.guild.get_member(int(partner_id))
    if not partner:
        await ctx.send("❌ Партнёр не найден на сервере!")
        return None, False
    return partner, True


@bot.command(name="поцеловать")
async def potselovat(ctx):
    partner, ok = await require_partner(ctx)
    if not ok:
        return
    gain = 50
    add_love(ctx.author.id, gain)
    add_love(partner.id, gain)
    save_data()
    total = get_love(ctx.author.id)
    await ctx.send(
        f"😘 **{ctx.author.mention}** нежно поцеловал(а) **{partner.mention}**!\n"
        f"💖 +{gain} очков любви | Всего у вас: **{total}** ❤️"
    )


@bot.command(name="чмокнуть")
async def chmoknut(ctx):
    partner, ok = await require_partner(ctx)
    if not ok:
        return
    gain = 20
    add_love(ctx.author.id, gain)
    add_love(partner.id, gain)
    save_data()
    total = get_love(ctx.author.id)
    await ctx.send(
        f"😚 **{ctx.author.mention}** чмокнул(а) **{partner.mention}** в щёчку!\n"
        f"💖 +{gain} очков любви | Всего у вас: **{total}** ❤️"
    )


@bot.command(name="шлепнуть")
async def shlepnut(ctx):
    partner, ok = await require_partner(ctx)
    if not ok:
        return
    gain = 30
    add_love(ctx.author.id, gain)
    add_love(partner.id, gain)
    save_data()
    total = get_love(ctx.author.id)
    await ctx.send(
        f"👋 **{ctx.author.mention}** шлёпнул(а) **{partner.mention}**!\n"
        f"💖 +{gain} очков любви | Всего у вас: **{total}** ❤️"
    )


@bot.command(name="секс")
async def romance_evening(ctx):
    partner, ok = await require_partner(ctx)
    if not ok:
        return

    pending_sex[str(partner.id)] = str(ctx.author.id)

    class SexView(View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.button(label="✅ Согласиться", style=discord.ButtonStyle.success)
        async def accept(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != partner.id:
                return await interaction.response.send_message("Это не тебе!", ephemeral=True)

            pending_sex.pop(str(partner.id), None)
            self.stop()

            gain = 200
            add_love(ctx.author.id, gain)
            add_love(partner.id, gain)

            pregnant = False
            preggo_id = None

            if (str(ctx.author.id) not in pregnancy and
                    str(partner.id) not in pregnancy and
                    random.randint(1, 3) == 1):
                preggo_id = str(ctx.author.id)
                pregnancy[preggo_id] = {
                    "partner": str(partner.id),
                    "uzi": 0,
                    "tests": 0,
                    "birth_chance": 100
                }
                pregnant = True

            save_data()

            preg_text = ""
            if pregnant:
                preg_text = (
                    f"\n\n🤰 **{ctx.author.mention} забеременел(а)!**\n"
                    f"Для успешных родов нужно:\n"
                    f"• `!узи` × 2 (1000 💖 каждое)\n"
                    f"• `!анализы` × 3 (700 💖 каждое)\n"
                    f"• `!роды` — когда будете готовы!\n"
                    f"⚠️ Каждое пропущенное действие снижает шанс на рождение на 20%"
                )

            await interaction.response.edit_message(
                content=(
                    f"🌹 **{ctx.author.mention}** и **{partner.mention}** провели романтический вечер!\n"
                    f"💖 +{gain} очков любви | Всего у вас: **{get_love(ctx.author.id)}** ❤️"
                    + preg_text
                ),
                view=None
            )

        @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
        async def decline(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != partner.id:
                return await interaction.response.send_message("Это не тебе!", ephemeral=True)
            pending_sex.pop(str(partner.id), None)
            self.stop()
            await interaction.response.edit_message(
                content=f"😔 {partner.mention} отказал(а) от романтического вечера.",
                view=None
            )

        async def on_timeout(self):
            pending_sex.pop(str(partner.id), None)

    view = SexView()
    await ctx.send(
        f"🌹 **{ctx.author.mention}** приглашает **{partner.mention}** на романтический вечер...\n"
        f"{partner.mention}, согласишься?",
        view=view
    )


@bot.command(name="узи")
async def uzi_cmd(ctx):
    uid = str(ctx.author.id)

    if uid not in pregnancy:
        return await ctx.send("❌ У тебя нет беременности!")

    preg = pregnancy[uid]

    if preg["uzi"] >= 2:
        return await ctx.send("✅ Ты уже сделал(а) все УЗИ!")

    cost = 1000
    if get_love(uid) < cost:
        return await ctx.send(f"❌ Не хватает очков любви! Нужно {cost} 💖, у тебя {get_love(uid)} 💖")

    remove_love(uid, cost)
    preg["uzi"] += 1
    save_data()

    remaining = 2 - preg["uzi"]
    await ctx.send(
        f"🏥 **{ctx.author.mention}** сделал(а) УЗИ! ({preg['uzi']}/2)\n"
        f"💖 -{cost} очков любви\n"
        + (f"Осталось УЗИ: {remaining}" if remaining > 0 else "✅ Все УЗИ сделаны!")
    )


@bot.command(name="анализы")
async def analizy_cmd(ctx):
    uid = str(ctx.author.id)

    if uid not in pregnancy:
        return await ctx.send("❌ У тебя нет беременности!")

    preg = pregnancy[uid]

    if preg["tests"] >= 3:
        return await ctx.send("✅ Ты уже сдал(а) все анализы!")

    cost = 700
    if get_love(uid) < cost:
        return await ctx.send(f"❌ Не хватает очков любви! Нужно {cost} 💖, у тебя {get_love(uid)} 💖")

    remove_love(uid, cost)
    preg["tests"] += 1
    save_data()

    remaining = 3 - preg["tests"]
    await ctx.send(
        f"🧪 **{ctx.author.mention}** сдал(а) анализы! ({preg['tests']}/3)\n"
        f"💖 -{cost} очков любви\n"
        + (f"Осталось анализов: {remaining}" if remaining > 0 else "✅ Все анализы сданы!")
    )


@bot.command(name="роды")
async def rody_cmd(ctx):
    uid = str(ctx.author.id)

    if uid not in pregnancy:
        return await ctx.send("❌ У тебя нет беременности!")

    preg = pregnancy[uid]

    missed_actions = (2 - preg["uzi"]) + (3 - preg["tests"])
    birth_chance = max(0, 100 - missed_actions * 20)

    del pregnancy[uid]
    save_data()

    roll = random.randint(1, 100)
    success = roll <= birth_chance

    if success:
        children.setdefault(uid, [])
        partner_id = preg.get("partner", "???")
        children.setdefault(partner_id, [])
        save_data()

        await ctx.send(
            f"🍼 **{ctx.author.mention}** успешно родил(а)!\n"
            f"Шанс на рождение был: **{birth_chance}%** (бросок: {roll})\n\n"
            f"Теперь используй `!ребенок`, ответив на сообщение любого участника,\n"
            f"чтобы предложить ему стать вашим ребёнком! 👶"
        )
    else:
        await ctx.send(
            f"😢 К сожалению, роды не прошли успешно...\n"
            f"Шанс на рождение был: **{birth_chance}%** (бросок: {roll})\n"
            f"Было пропущено действий: {missed_actions}"
        )


@bot.command(name="ребенок")
async def rebenok_cmd(ctx):
    if not ctx.message.reference:
        return await ctx.send("❌ Ответь на сообщение участника, которого хочешь пригласить стать ребёнком!")

    try:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except:
        return await ctx.send("❌ Не могу найти сообщение!")

    target = ref_msg.author
    author = ctx.author

    if target.bot:
        return await ctx.send("❌ Бот не может быть ребёнком!")
    if target.id == author.id:
        return await ctx.send("❌ Нельзя сделать себя своим ребёнком!")

    uid = str(author.id)
    partner_id = get_partner(uid)

    if uid not in children and (not partner_id or partner_id not in children):
        return await ctx.send(
            "❌ У вас пока нет ребёнка! Сначала используй `!секс` → `!узи` → `!анализы` → `!роды`"
        )

    pending_child[str(target.id)] = uid

    class ChildView(View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.button(label="👶 Принять", style=discord.ButtonStyle.success)
        async def accept(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != target.id:
                return await interaction.response.send_message("Это не тебе!", ephemeral=True)
            pending_child.pop(str(target.id), None)
            self.stop()

            children.setdefault(uid, [])
            if str(target.id) not in children[uid]:
                children[uid].append(str(target.id))

            if partner_id:
                children.setdefault(partner_id, [])
                if str(target.id) not in children[partner_id]:
                    children[partner_id].append(str(target.id))

            save_data()

            await interaction.response.edit_message(
                content=(
                    f"👨‍👩‍👦 **{target.mention}** теперь ребёнок **{author.mention}**"
                    + (f" и <@{partner_id}>!" if partner_id else "!")
                ),
                view=None
            )

        @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger)
        async def decline(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != target.id:
                return await interaction.response.send_message("Это не тебе!", ephemeral=True)
            pending_child.pop(str(target.id), None)
            self.stop()
            await interaction.response.edit_message(
                content=f"❌ {target.mention} отказал(а) стать ребёнком.",
                view=None
            )

        async def on_timeout(self):
            pending_child.pop(str(target.id), None)

    view = ChildView()
    await ctx.send(
        f"👶 **{author.mention}** предлагает **{target.mention}** стать их ребёнком!\n"
        f"{target.mention}, согласишься?",
        view=view
    )


@bot.command(name="семья")
async def semya_cmd(ctx):
    uid = str(ctx.author.id)
    partner_id = get_partner(uid)

    lines = [f"👨‍👩‍👦 **Семья {ctx.author.mention}**\n"]

    if partner_id:
        lines.append(f"💕 Партнёр: <@{partner_id}>")
    else:
        lines.append("💔 Партнёра нет")

    lines.append(f"💖 Очки любви: **{get_love(uid)}**")

    kids = children.get(uid, [])
    if kids:
        lines.append(f"👶 Дети: {', '.join(f'<@{k}>' for k in kids)}")
    else:
        lines.append("👶 Детей пока нет")

    if uid in pregnancy:
        preg = pregnancy[uid]
        lines.append(
            f"\n🤰 **Беременность:**\n"
            f"  УЗИ: {preg['uzi']}/2\n"
            f"  Анализы: {preg['tests']}/3\n"
            f"  Шанс на рождение: **{max(0, 100 - (2 - preg['uzi'] + 3 - preg['tests']) * 20)}%**"
        )

    await ctx.send("\n".join(lines))


@bot.command(name="любовьтоп")
async def love_top_cmd(ctx):
    if not love_points:
        return await ctx.send("❌ Нет данных об очках любви!")

    sorted_love = sorted(love_points.items(), key=lambda x: x[1], reverse=True)
    lines = ["💖 **Топ по очкам любви:**\n"]

    for i, (uid, pts) in enumerate(sorted_love[:10], 1):
        member = ctx.guild.get_member(int(uid))
        name = member.mention if member else f"<@{uid}>"
        lines.append(f"{i}. {name} — {pts} 💖")

    await ctx.send("\n".join(lines))


# =========================
# 🚀 ЗАПУСК БОТА
# =========================

@bot.event
async def on_ready():
    load_data()
    await bot.tree.sync()
    print(f"Bot ready: {bot.user}")


# Получаем токен из переменной окружения
TOKEN = os.getenv("TOKEN", "")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ОШИБКА: Токен бота не найден в переменной окружения TOKEN")
    print("❌ Добавь TOKEN в .env файл!")
