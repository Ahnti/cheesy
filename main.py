import aiohttp
import discord
from discord.app_commands.models import app_command_option_factory
from discord.ext import commands
from discord import app_commands
import yt_dlp
import logging
from dotenv import load_dotenv
import os
import requests
import json
import smtplib
from email.message import EmailMessage
import random
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import google.generativeai as genai

from keep_alive import keep_alive
import asyncio

# hi im cheesecake
#hell yeah lol
load_dotenv()
gmail_user = os.getenv("GMAIL_USER")
gmail_pass = os.getenv("GMAIL_PASS")
unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

keep_alive()

token = os.getenv('DISCORD_TOKEN')
if not token:
    raise ValueError("DISCORD_TOKEN environment variable not set.")

handler = logging.FileHandler('discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(commands.when_mentioned_or("@Cheesecake "), intents=intents)
#initial commit parallel universe render test
def ImActiveHaha():
    active = "yep i'm active"
    return active

@bot.event
async def on_ready():
    guild = discord.Object(id=1126180305229848647)
    await bot.tree.sync(guild=guild)
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    print('------')
    # Load memories for all servers on startup
    load_all_memories()

class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self,mapping):
        embed = discord.Embed(
            title="command list",
            color=discord.Color.red()
        )

        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list, sort=True)
            command_names = list({f"`{command.name}`" for command in filtered})
            if command_names:
                name = cog.qualified_name if cog else "General"
                value = ", ".join(command_names)
                embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text="Use @Cheesecake help [command]")
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"{command.name}",
            description=command.help or "No desc",
            color=discord.Color.yellow()
        )
        if command.aliases:
            aliases = ", ".join(f"`{alias}`" for alias in command.aliases)
            embed.add_field(name="Aliases", value=aliases, inline=False)
        embed.add_field(name="Usage", value=f"`@Cheesecake {command.qualified_name} {command.signature}`", inline=False)
        await self.get_destination().send(embed=embed)

bot.help_command = CustomHelpCommand()

# ass
@bot.command(name='image', help="searches the interwebs for an image", usage="[query]")
async def image(ctx, *, query):
    url = f"https://api.unsplash.com/search/photos?query={query}&client_id={unsplash_access_key}&per_page=20"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            results = data.get("results")

            if not results:
                await ctx.send("No images found.")
                return

            image_url = random.choice(results)["urls"]["regular"]
            await ctx.send(image_url)

@bot.command(name='ask', help="this command is very dead")
async def ask(ctx, *, prompt: str):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer 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"
            },
            data=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        answer = response.choices[0].message.content
        await ctx.reply(answer)
    except Exception as e:
        logging.exception("deepseek bugging ToT")
        await ctx.reply("What?")

#@bot.command(name='ping', help="returns bot latency", usage="")
#async def ping(ctx):
#    ping = int(round(bot.latency*1000, -2))
#    await ctx.send(f"Idk, {ping} something ms")

ball8 = ["yeah thats crazy", "ok", "<:true:1340351233877082167>", "???", "idonknow....", "maybe", "hell no",
             "fuck you", "hii :3", "this is why i love you", "oh", "does that make u smart now", "lmao", "lol",
             "stupid...",
             "oh my god i dont care", "true true true!!", "i agree", "what the hell ToT", "shut up", "me when i lie",
             "lalalala", "ill put it on everyone's lives", "what?", "ngl...", "can u repeat that",
             "meow meow meow meow :3", "HELL no", "okay okay yeah", "beats me", "undisputed fact!", "money called and you hung up",
         "very so", "zzzz", "um hmmmmm real thinker here", "mmmm", "beat it", "nononono", "yeah yeah yeah", "yeah and pigs fly", "the sky is blue", "i ran out of tokens please give my creator ahn money"]


def eight_ball():
    answer = random.choice(ball8)
    return answer

conversation_logs = {}
MAX_MEMORY = 20
last_response_time = {}
COOLDOWN_SECONDS = 15

# FIXED: Now memories are stored per-server (guild)
# Format: "memories/guild_{guild_id}_users.json" and "memories/guild_{guild_id}_topics.json"
user_memories = {}  # Structure: {guild_id: {user_id: memory_data}}
topic_memories = {}  # Structure: {guild_id: {topic_key: topic_data}}

# DATABASE i will LERARN HOW TO DATABASE GET OF FMY BACK!!!
def get_memory_dir():
    """Create memories directory if it doesn't exist"""
    os.makedirs("memories", exist_ok=True)
    return "memories"

def get_user_memory_file(guild_id):
    """Get the user memory file path for a specific guild"""
    return os.path.join(get_memory_dir(), f"guild_{guild_id}_users.json")

def get_topic_memory_file(guild_id):
    """Get the topic memory file path for a specific guild"""
    return os.path.join(get_memory_dir(), f"guild_{guild_id}_topics.json")

def load_all_memories():
    """Load memories for all servers on startup"""
    global user_memories, topic_memories
    memory_dir = get_memory_dir()
    
    if not os.path.exists(memory_dir):
        return
    
    # Load all user memory files
    for filename in os.listdir(memory_dir):
        if filename.endswith("_users.json"):
            guild_id = filename.replace("guild_", "").replace("_users.json", "")
            try:
                filepath = os.path.join(memory_dir, filename)
                with open(filepath, 'r') as f:
                    user_memories[guild_id] = json.load(f)
                print(f"Loaded user memories for guild {guild_id}: {len(user_memories[guild_id])} users")
            except Exception as e:
                print(f"Error loading user memories for guild {guild_id}: {e}")
        
        elif filename.endswith("_topics.json"):
            guild_id = filename.replace("guild_", "").replace("_topics.json", "")
            try:
                filepath = os.path.join(memory_dir, filename)
                with open(filepath, 'r') as f:
                    topic_memories[guild_id] = json.load(f)
                print(f"Loaded topic memories for guild {guild_id}: {len(topic_memories[guild_id])} topics")
            except Exception as e:
                print(f"Error loading topic memories for guild {guild_id}: {e}")

def save_memories(guild_id):
    """Save memories for a specific guild"""
    try:
        guild_id = str(guild_id)
        
        # Save user memories
        if guild_id in user_memories:
            with open(get_user_memory_file(guild_id), 'w') as f:
                json.dump(user_memories[guild_id], f, indent=2)
        
        # Save topic memories
        if guild_id in topic_memories:
            with open(get_topic_memory_file(guild_id), 'w') as f:
                json.dump(topic_memories[guild_id], f, indent=2)
    except Exception as e:
        print(f"Error saving memories for guild {guild_id}: {e}")

def get_user_memory(guild_id, user_id):
    """Get user memory for a specific guild"""
    guild_id = str(guild_id)
    user_id = str(user_id)
    
    if guild_id not in user_memories:
        user_memories[guild_id] = {}
    
    if user_id not in user_memories[guild_id]:
        user_memories[guild_id][user_id] = {
            "name": "",
            "facts": [],
            "preferences": {},
            "last_updated": datetime.now().isoformat()
        }
    return user_memories[guild_id][user_id]

def add_user_memory(guild_id, user_id, fact, category="facts"):
    """Add user memory for a specific guild"""
    guild_id = str(guild_id)
    user_id = str(user_id)
    memory = get_user_memory(guild_id, user_id)

    if category == "facts":
        if fact not in memory["facts"]:
            memory["facts"].append(fact)
            memory["last_updated"] = datetime.now().isoformat()
            save_memories(guild_id)
            return True
    elif category == "name":
        memory["name"] = fact
        memory["last_updated"] = datetime.now().isoformat()
        save_memories(guild_id)
        return True
    else:
        memory[category] = fact
        memory["last_updated"] = datetime.now().isoformat()
        save_memories(guild_id)
        return True
    return False

def add_topic_memory(guild_id, topic_key, info, category="general"):
    """Add topic memory for a specific guild"""
    guild_id = str(guild_id)
    
    if guild_id not in topic_memories:
        topic_memories[guild_id] = {}
    
    if topic_key not in topic_memories[guild_id]:
        topic_memories[guild_id][topic_key] = {
            "items": [],
            "category": category,
            "last_updated": datetime.now().isoformat()
        }
    if info not in topic_memories[guild_id][topic_key]["items"]:
        topic_memories[guild_id][topic_key]["items"].append(info)
        topic_memories[guild_id][topic_key]["last_updated"] = datetime.now().isoformat()
        save_memories(guild_id)
        return True
    return False

def get_topic_memory(guild_id, topic_key):
    """Get topic memory for a specific guild"""
    guild_id = str(guild_id)
    if guild_id not in topic_memories:
        return {"items": [], "category": "general"}
    return topic_memories[guild_id].get(topic_key, {"items": [], "category": "general"})

def get_relevant_topics(guild_id, keywords=None, limit=5):
    """Get relevant topics for a specific guild"""
    guild_id = str(guild_id)
    
    if guild_id not in topic_memories or not topic_memories[guild_id]:
        return []
    relevant = []
    if keywords:
        keywords_lower = [k.lower() for k in keywords]
        for topic_key, data in topic_memories[guild_id].items():
            if any(kw in topic_key.lower() for kw in keywords_lower):
                relevant.extend(data["items"][-3:])
    for topic_key, data in list(topic_memories[guild_id].items())[-5:]:
        relevant.extend(data["items"][-2:])
    
    relevant = list(dict.fromkeys(relevant))[:limit]
    return relevant

def get_all_topic_summary(guild_id):
    """Get topic summary for a specific guild"""
    guild_id = str(guild_id)
    
    if guild_id not in topic_memories or not topic_memories[guild_id]:
        return ""
    
    summary = "\n\nGeneral things you remember:\n"
    
    for topic_key, data in list(topic_memories[guild_id].items())[-10:]:
        items = data["items"][-3:]
        if items:
            summary += f"\n{topic_key}:\n"
            summary += "- " + "\n- ".join(items)
        
    return summary

# REMOVED: Auto-memory extraction function completely removed
# The extractmem() function has been deleted

def get_user_memory_summary(guild_id, user_id, username):
    """Get user memory summary for a specific guild"""
    memory = get_user_memory(guild_id, user_id)

    if not memory["facts"] and not memory["preferences"]:
        return ""
    
    summary = f"\nWhat you remember about {username}:\n"
    
    if memory["facts"]:
        summary += "- " + "\n- ".join(memory["facts"][:5])
    if memory["preferences"]:
        prefs = [f"{k}: {v}" for k, v in memory["preferences"].items()]
        if prefs:
            summary += "\n- " + "\n- ".join(prefs[:3])
    return summary



#hold on i need to pee
CHEESECAKE_PERSONA = os.getenv("CHEESECAKE_PERSONA")

def should_respond_randomly():
    return random.random() < 0.01

def get_contextual_prompt(history, message_content, is_mentioned, guild_id, user_id, username):
    recent_messages = history.split('\n')[-5:] if history else []
    has_question = '?' in message_content
    is_continuation = len(recent_messages) > 3

    user_memory_context = get_user_memory_summary(guild_id, user_id, username)

    keywords = message_content.lower().split()[:5]
    topic_context = get_relevant_topics(guild_id, keywords, limit=5)
    
    topic_summary = ""
    if topic_context: 
        topic_summary = "\n\nRelevant things you remember:\n- " + "\n- ".join(topic_context)
    
    
    if is_mentioned:
        prompt = f"{CHEESECAKE_PERSONA}\n\n"

        if user_memory_context:
            prompt += user_memory_context + "\n"
        if topic_summary:
            prompt += topic_summary + "\n"
        if history:
            prompt += f"\nRecent conversation:\n{history}\n\n"
        #prompt += f"Recent conversation:\n{history}\n\n"
        prompt += f"Someone just mentioned you: {message_content}\n\n"
        
        if has_question:
            prompt += "They asked you a question. Answer it naturally and conversationally.\n"
        else:
            prompt += "React naturally to what they said. Keep it short and casual."
        
        prompt += "Respond as Cheesecake:"
    else:
        prompt = f"{CHEESECAKE_PERSONA}\n\n"

        if user_memory_context:
            prompt += user_memory_context + "\n"
        if topic_summary:
            prompt += topic_summary + "\n"
        
        if history:
            prompt += f"Recent conversation:\n{history}\n\n"
            prompt += "You're reading this conversation. Chime in naturally with a brief comment or reaction. "
            prompt += "Don't force it - just add to the conversation like you're part of the group chat.\n"
        else:
            prompt += "Join the conversation. Say something brief.\n"
        prompt += "Respond as Cheesecake:"
    
    return prompt

#def should_skip_response(message_content, channel_id):
#    if len(message_content.strip()) < 3:
#        return True
#    if channel_id in last_response_time:
#        time_since_last = (datetime.now() - last_response_time[channel_id]).seconds
#        if time_since_last < COOLDOWN_SECONDS:
#            return True
#
#    return False

@bot.command(name="memories", help="see what i remember about you")
async def memories(ctx):
    memory = get_user_memory(ctx.guild.id, ctx.author.id)
    
    if not memory["facts"] and not memory["preferences"]:
        await ctx.send("who even you lol")
        return
    embed = discord.Embed(
        title=f"what i remember about {ctx.author.display_name}",
        color=discord.Color.purple()
    )
    
    if memory["facts"]:
        facts_text = "\n".join(f"* {fact}" for fact in memory["facts"])
        embed.add_field(name="Facts", value=facts_text, inline=False)
    if memory["preferences"]:
        prefs_text = "\n".join(f"* {k}: {v}" for k, v in memory["preferences"].items())
        embed.add_field(name="Preferences", value=prefs_text, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="topics", help="see what topics i remember")
async def topics(ctx):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in topic_memories or not topic_memories[guild_id]:
        await ctx.send("i forgor")
        return
    
    embed = discord.Embed(
        title="topics i rember",
        color=discord.Color.blue()
    )
    
    for topic_key, data in list(topic_memories[guild_id].items())[-10:]:
        items = data["items"][-5:]
        if items:
            value = "\n".join(f"* {item}" for item in items)
            embed.add_field(name=topic_key, value=value, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="forget", help="makes me forget everything about you")
async def forget(ctx):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if guild_id in user_memories and user_id in user_memories[guild_id]:
        del user_memories[guild_id][user_id]
        save_memories(guild_id)
        await ctx.send("wait who are u again")
    else:
        await ctx.send("i alr forgot about u")

@bot.command(name="remember", help="tell me something to remember", usage="[thing to remember]")
async def remember(ctx, *, fact: str):
    added = add_user_memory(ctx.guild.id, ctx.author.id, fact, "facts")
    if added:
        responses = ["ok", "noted :noted:", "ill try to remmember that", "stored in the brane"]
        await ctx.send(random.choice(responses))
    else:
        await ctx.send("i already know that dummy")
    
@bot.command(name="note", help="tell me a general fact to remember (not about you)", usage="[category] [fact]")
async def note(ctx, category: str, *, fact:str):
    added = add_topic_memory(ctx.guild.id, category, fact)
    if added:
        await ctx.send(f"ok :noted: under {category}")
    else:
        await ctx.send("i already have that written down")

@bot.command(name="cleartopics", help="clears all topic memories (ahn only)")
async def clear_topics(ctx):
    if ctx.author.id != 597433737126477826:
        await ctx.send("youre not my mommy")
        return
    
    guild_id = str(ctx.guild.id)
    if guild_id in topic_memories:
        topic_memories[guild_id] = {}
        save_memories(guild_id)
    await ctx.send("now im just a nobody...")
    

def log_message(channel_id, author_name, content, is_bot=False):
    if channel_id not in conversation_logs:
        conversation_logs[channel_id] = []
        
    log = conversation_logs[channel_id]
    timestamp = datetime.now().strftime("%H:%M")
    log.append(f"[{timestamp}] {author_name}: {content}")
    
    if len(log) > MAX_MEMORY:
        log.pop(0)

        
def clean_response(text):
    text = re.sub(r'^(Sure,?|Okay,?|Alright,?)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^As (an AI|Cheesecake),?\s+', '', text, flags=re.IGNORECASE)
    
    if text.count('*') > 2:
        text = re.sub(r'\*[^*]+\*', '', text)
    return text.strip()

@bot.event
async def on_message(message):
    logging.info(f"on_message triggered for message: {message.content}")
    
    if message.author == bot.user:
        return
    author_name = message.author.display_name
    log_message(message.channel.id, author_name, message.content)
    #log = conversation_logs.setdefault(message.channel.id, [])
    #author_name = "Cheesecake" if message.author == bot.user else message.author.display_name
    #log.append(f"{author_name}: {message.content}")
    is_mentioned = bot.user.mentioned_in(message)
    
    # Added line 577
    mention_at_start = message.content.strip().startswith(f'<@{bot.user.id}>') or message.content.strip().startswith(f'<@!{bot.user.id}>')

# Modified line 580
    should_respond = (is_mentioned and not mention_at_start) or should_respond_randomly()
    #should_respond = is_mentioned or should_respond_randomly()
    
    #if message.author == bot.user:
    #    return
    
    if should_respond:
        history = "\n".join(conversation_logs.get(message.channel.id, []))
        try:
            async with message.channel.typing():
                model = genai.GenerativeModel("gemini-flash-lite-latest")
                
                prompt = get_contextual_prompt(
                    history, 
                    message.content, 
                    is_mentioned, 
                    message.guild.id,
                    message.author.id, 
                    message.author.display_name
                )
                
                generation_config = {
                    "temperature": 0.9,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 300,
                }
                
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                response_text = response.text.strip()
                response_text = clean_response(response_text)

                if "|||" in response_text:
                    messages = [msg.strip() for msg in response_text.split("|||")]
                    messages = [msg for msg in messages if msg]
                else:
                    messages = [response_text]

                for i, msg in enumerate(messages):
                    if msg and len(msg) > 0:
                        await message.channel.send(msg)
                        log_message(message.channel.id, "Cheesecake", msg, is_bot=True)
                        if i < len(messages) - 1:
                            await asyncio.sleep(random.uniform(0.5,1.5))
                #response_text = clean_response(response_text)
                #if response_text and len(response_text) > 0:
                #    await message.channel.send(response_text)

                #    log_message(message.channel.id, "Cheesecake", response_text, is_bot=True)
                last_response_time[message.channel.id] = datetime.now()
                
                # REMOVED: Auto-memory extraction completely removed
                # These lines have been deleted:
                # await extractmem(
                #     message.channel.id,
                #     message.author.id,
                #     message.author.display_name,
                #     conversation_logs.get(message.channel.id, [])
                # )
        except Exception as e:
            logging.error(f"AI response ewwow :( : {e}")
            if is_mentioned:
                fallback_responses = [
                    "someone tell ahn there is a problem with my ai",
                    "uhhhmmmm thinking emoji",
                    "im lagging ddddd",
                    "i just blew a fuse",
                    "Ive ran out of tokens lmaooooooooooo"
                ]
                await message.channel.send(random.choice(fallback_responses))
    
    # REMOVED: Auto-memory extraction after every message
    # await extractmem(
    #     message.channel.id,
    #     message.author.id,
    #     message.author.display_name,
    #     conversation_logs.get(message.channel.id, [])
    # )
    
    #if len(log) > MAX_MEMORY:
    #    log.pop(0)
    
    
    #if bot.user.mentioned_in(message) and not message.content.startswith((f"<@{bot.user.id}>", f"<@!{bot.user.id}> help")):
    #    history = "\n".join(conversation_logs[message.channel.id])
    #    try:
    #        model = genai.GenerativeModel("gemini-flash-lite-latest")
    #        prompt = f"{CHEESECAKE_PERSONA}" \
    #                f"Here is the recent conversation:\n{history}\n" \
    #                f"What do you want to say? Respond accordingly with a one-liner. Match the people's tone."
    #        prompt += f"\nUser: {message.content}\nCheesecake:"
    #        response = model.generate_content(prompt)
#
    #        await message.channel.send(response.text)
    #    except Exception as e:
    #        await message.channel.send("Ive ran out of tokens lmaooooooooooo")
    #if re.search(r'\bhey\b', message.content, re.IGNORECASE):
        #print(ImActiveHaha())
        #await message.channel.send("Hey is for horses")
    if "time" in message.content.lower() and "restart" in message.content.lower():
        await message.channel.send("hope i dont die this time")
    #if "force" in message.content.lower():
        #await message.add_reaction("🐴")
    if "cheesecake" in message.content.lower():
        print(ImActiveHaha())
        await message.channel.send(random.choice(["yeah?", "what", "thats me", "hi"]))

    if "miku" in message.content.lower():
        print(ImActiveHaha())
        await message.channel.send("miku miku ni shite ageru!")

    if "kill" in message.content.lower() and "hammers" in message.content.lower():
        await message.channel.send("https://tenor.com/view/nba-gif-15687325833433865178")
    chance = 0.001
    other_chance = 0.01
    if random.random() < chance:
        print(ImActiveHaha())
        await message.channel.send("*flies past*")
    
    #if random.random() < 0.01:
       # history = "\n".join(conversation_logs[message.channel.id])
        #prompt = f"{CHEESECAKE_PERSONA}" \
               # f"Here is the recent conversation:\n{history}\n" \
               # f"What do you want to say? Respond accordingly with a one-liner."
        #model = genai.GenerativeModel("gemini-flash-lite-latest")
       # response = model.generate_content(prompt)
       # await message.channel.send(response.text)


    #if random.random() < other_chance:
        #print(ImActiveHaha())
        #await message.channel.send(eight_ball())


    if "back me up" in message.content.lower():
        print(ImActiveHaha())
        await message.channel.send(eight_ball())



    if "lime perfect" in message.content.lower():
        noon_id = 736566304898678894
        noon = message.guild.get_member(noon_id)
        if noon:
            await message.channel.send(noon.mention)

    if message.guild.id == 1138608920529735682:
        if "elsie" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/1138608922249416716/1252479938561310730/elsie.mp4?ex=6952ac17&is=69515a97&hm=da130953dd232fb7a1bbcf4273390a39d005288eb6b264e91d423546593eebdf&")
        if "haqua" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/1138608922249416716/1252480306242519110/haqua.mp4?ex=6952ac6e&is=69515aee&hm=2606d612d77b98bd77b78b90d5c579d0a881d54db1dc485a20a1cef3748f6829&")
        if "coke" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/1138608922249416716/1252480295538659338/yokkyun.mp4?ex=6952ac6c&is=69515aec&hm=865c0ead5d106ea610c825f036ea2a68189bf376d4c25688bca31cf485133002&")
        if "?care" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/1070575358535016458/1072380850714456104/care.mp4?ex=6952b33e&is=695161be&hm=5c6ebd1245df10ae215ce003fa2ec2e588c99c11ea4b6fe8ca8eecbe34586bec&")
        if "despair" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/1138608922249416716/1280299053447647296/why_he_tweaking_-_Made_with_Clipchamp.mp4?ex=69525d29&is=69510ba9&hm=2e2bc2a215d01126aa58d88bb3b2699b69063f6f0e364ef4497a7ff4cef17768&")
        if "?rumbling" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/1249091056729981139/1249091141077307503/ki-7062464868909108486_QuickVids.win.mp4?ex=69523587&is=6950e407&hm=88824d476a8e9da136cf01877fbd2001cff9b244db49f78119f720d3b551ab95&")
        if "hew bomb" in message.content.lower():
            await message.channel.send("https://cdn.discordapp.com/attachments/1138608922249416716/1425318846780280932/Jerry_Twerk.mp4?ex=6952995e&is=695147de&hm=f0bf1a633910308808aa9c892032bb3030295edc4729b8a0b22b6948b34a4322&")

    async def russian_roulette(channel):
        bullet = random.randint(1,6)
        await message.channel.send("Russian Roulette time!")
        await message.channel.send(f"Bullet is in chamber {bullet}!")
        for i in range(1,6):
            await message.channel.send(random.randint(1,6))
        slot = random.randint(1,6)
        await message.channel.send(slot)
        if slot == bullet:
            await message.channel.send("Noon is dead :P")
        else:
            await message.channel.send("Rats! I mean,,, woaw! lucky noon! You live for another day")
    muted = False
    if "hi cheesy" in message.content.lower():
        ahn_id = 597433737126477826
        brox_id = 1015440723606241422
        denz_id = 481608668966813697
        noon_id = 736566304898678894
        bryaby_id = 244397251177218048
        ahn = message.guild.get_member(ahn_id)
        if message.author.id == ahn_id:
            print(ImActiveHaha())
            await message.channel.send("omg hi mom!!!!!")
        elif message.author.id == denz_id:
            print(ImActiveHaha())
            await message.channel.send(random.choice(["hewwo denz-sama… how are u… ACCCHHHOO!! doing on this sniffles fine day…",
                                                        "omiGAHHH!!! denz-sama needs my assistance… w-what is it? w-what is it…!!!!!!???",
                                                        "hai OwO dis Is cheesy your server bot teehee!! >~< do you want cheese on your cheesecake!", 
                                                        "its [time]! get to wrok dummy owner…! hmph.. you’re gonna get me mad.. >:C",
                                                        "can you be my onii-sama denz-sama >~< i can play anwy whythm gwame you want…!!",
                                                        "the number one nanahira fan is here..?.???? UWAHHH IM SO GLAD TO BE IN YOUR PRESENCE DENZ-SAMA!!!!!",
                                                        "yorushiku~ hai domo watashi wa cheezu desu yo."]))
        elif message.author.id == noon_id:
            await message.channel.send(russian_roulette(message.channel))
        elif message.author.id == brox_id:
            await message.channel.send("die")
        else:
            print(ImActiveHaha())
            await message.channel.send("who tf are you")


    await bot.process_commands(message)


class Mail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gmail_user = gmail_user
        self.gmail_pass = gmail_pass

    @commands.command(name='mail', help="sends a message to ahn's email :D", usage="[message] (type the message inside quotes)")
    async def mail(self, ctx, *, message: str):
        subject = f"Message from Discord user {ctx.author.name}"
        body = message

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = self.gmail_user
        msg['To'] = self.gmail_user

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(self.gmail_user, self.gmail_pass)
            server.send_message(msg)
            server.quit()
            await ctx.send("sent!")
        except smtplib.SMTPAuthenticationError:
            logging.error("This aint smtp authin...")
            await ctx.send("error")
        except Exception as e:
            logging.exception("something fucked up")
            await ctx.send("something fucked up")

@bot.command(name="hi", help="hi")
async def hi(ctx):
    await ctx.send("hi")



major_degrees = ["I", "ii", "iii", "IV", "V", "vi", "vii"]
minor_degrees = ["i", "ii°", "III", "iv", "v", "VI", "VII"]

notes_sharp = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
notes_flat = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']




def get_scale(root, scale_type):
    """Bunch of bullshit"""
    chromatic = notes_sharp if '#' in root or 'E' in root else notes_flat
    start_index = chromatic.index(root)

    if scale_type == 'M':  # major
        steps = [2, 2, 1, 2, 2, 2, 1]
    else:  # minor
        steps = [2, 1, 2, 2, 1, 2, 2]

    scale = [root]
    index = start_index
    for step in steps:
        index = (index + step) % 12
        scale.append(chromatic[index])
    return scale[:-1]  # Remove octave repeat


def get_chord(root, scale_type, degree):
    """Returns the chord at the specified degree in the scale."""
    scale = get_scale(root, scale_type)

    degree_input = degree.lower()
    degree_list = []

    match_found = False
    for deg in major_degrees:
        if deg.lower().startswith(degree_input):
            degree_list = major_degrees
            match_found = True
            break

    if not match_found:
        for deg in minor_degrees:
            if deg.lower().startswith(degree_input):
                degree_list = minor_degrees
                match_found = True
                break

    if scale_type == 'M':
        qualities = ['M', 'm', 'm', 'M', 'M', 'm', 'dim']
        degree_list = major_degrees
    else:
        qualities = ['m', 'dim', 'M', 'm', 'm', 'M', 'M']
        degree_list = minor_degrees

    index = next((i for i, deg in enumerate(degree_list) if deg.lower().startswith(degree_input)), None)
    if index is None:
        return "tf kinda degree is that"

    chord_root = scale[index]
    quality = qualities[index]

    if quality == 'M':
        return f"{chord_root} major"
    elif quality == 'm':
        return f"{chord_root} minor"
    else:
        return f"{chord_root} diminished"


@bot.command(name="chord", help="returns a chord from scale degree", usage="[note][M/m] [degree]")
async def chord(ctx, root_and_type: str, degree: str):
    try:
        # Pars
        if root_and_type[-1] not in ['M', 'm']:
            await ctx.send("put M or m after root note (M = major, m = minor)")
            return
        root = root_and_type[:-1]
        scale_type = root_and_type[-1]
        chord_name = get_chord(root, scale_type, degree)
        await ctx.send(chord_name)
    except Exception as e:
        await ctx.send(f"dumbass {e}")

@bot.command(name="remove", help="removes set amount of messages before and including the command (needs admin)", usage="[num]")
@commands.has_permissions(manage_messages=True)
async def remove(ctx, amount:int):
    ctx.send("*shade away...*")
    await asyncio.sleep(1)
    await ctx.channel.purge(limit=amount+2)

@remove.error
async def remove_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("No perms no bitches")

user_timers={}
def parse_time(time_str):
    pattern = re.compile(r"((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s?)?")
    match = pattern.fullmatch(time_str.strip().lower())
    if not match:
        return None
    time_data = match.groupdict(default="0")
    total_seconds = (
        int(time_data["hours"]) * 3600 +
        int(time_data["minutes"]) * 60 +
        int(time_data["seconds"])
    )
    return total_seconds if total_seconds > 0 else None


# hi weewoo
@bot.command(name="timer", help="Pings you after a set time. The note is optional.", usage="[n]h[n]m[n]s [note]")
async def timer(ctx, time_input: str, *, note: str = None):
    user_id = ctx.author.id

    if time_input.lower() == "cancel":
        if user_id in user_timers:
            user_timers[user_id].cancel()
            del user_timers[user_id]
            await ctx.send("ok no more timer :(")
        else:
            await ctx.send("cancel what?")
        return

    if user_id in user_timers:
        await ctx.send("cant have multiple rn sorry my creator is stupid. cancel the other one first")
        return

    total_seconds = parse_time(time_input)
    if total_seconds is None:
        await ctx.send("i don understan...")
        return

    await ctx.send(f"{time_input} it is")

    async def countdown():
        try:
            await asyncio.sleep(total_seconds)
            message = f"{ctx.author.mention}!"
            if note:
                message += f" {note}"
            await ctx.send(message)
        except asyncio.CancelledError:
            pass
        finally:
            user_timers.pop(user_id, None)

    task = asyncio.create_task(countdown())
    user_timers[user_id] = task

@bot.command(name="is", aliases=["did","do","does","are","was","were",
                                 "have","has","had","can","could","will",
                                 "would","shall","should","must","may","might" ],
             help="basically 8ball. use it in a question. DONT be stupid like noon", usage="[str]")

async def iss(ctx):
    await ctx.send(eight_ball())

@bot.command(name="ytmp3", help="Converts yt link to mp3", usage="[link] [filename (Optional)]")
async def ytmp3(ctx, url: str, filename: str = None):
    await ctx.send("hold on")
    logging.info("ytmp3 command triggered.")

    output_name = ""

    try:
        logging.info(f"Starting download for URL: {url}")
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get("title", "output")
            logging.info(f"Video title: {video_title}")

            clean_filename = (filename or video_title).replace(" ", "_").replace("/", "_")
            output_name = f"{clean_filename}.mp3"
            logging.info(f"Output filename: {output_name}")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_name,
                'cookiefile': 'youtube_cookies.txt',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'quiet': True
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        file_size = os.path.getsize(output_name)
        logging.info(f"File downloaded successfully. Size: {file_size} bytes")

        if file_size > 8 * 1024 * 1024:
            logging.warning("File size exceeds 8MB limit.")
            await ctx.send("too big file size!!!!!")
        else:
            logging.info("Sending file to Discord.")
            await ctx.send(file=discord.File(output_name))
            logging.info("File sent successfully.")

    except Exception as e:
        logging.error(f"An error occurred in ytmp3: {e}", exc_info=True)
        await ctx.send("couldnt downloa :<")

    finally:
        if os.path.exists(output_name):
            logging.info(f"Removing temporary file: {output_name}")
            os.remove(output_name)
        else:
            logging.info("Temporary file not found, skipping removal.")

async def load_extensions():
    await bot.add_cog(Mail(bot))

import asyncio
asyncio.run(load_extensions())

@bot.command(name="parrot", help="Parrots back what you say.")
async def parrot(ctx, *, message: str):
    await ctx.send(message)

@bot.command(name="dm", help="Sends a dm to someone.", usage="@recipient [message]")
async def dm(ctx, user: discord.User, *, message: str):
    try:
        await user.send(message)
        await ctx.send("pipe bomb sent")
    except discord.Forbidden:
        await ctx.send("tell them to let me in fiirsssttt.....")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
