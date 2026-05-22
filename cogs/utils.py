import discord
from discord.ext import commands
import asyncio
import os
import re
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from motor.motor_asyncio import AsyncIOMotorClient

#REMINDER STUFF -------------
MONGODB_URI = os.getenv("MONGODB_URI")
_client: AsyncIOMotorClient = None

#cheesy db
def get_db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client["cheesecake"]

def col_reminders():
    return get_db()["reminders"]

def col_timezones():
    return get_db()["timezones"]

#tz parsing
def parse_tz(tz_str: str):
    s = tz_str.strip()
    m = re.fullmatch(r"([+-])(\d{1,2})(?::(\d{2}))?", s)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        hrs = int(m.group(2))
        mns = int(m.group(3) or 0)
        if hrs > 14 or mns > 59:
            return None, None
        offset = timedelta(hrs=hrs, mns=mns) * sign
        return timezone(offset), f"UTC{s}"

    try:
        tz = ZoneInfo(s)
        return tz, s
    except (ZoneInfoNotFoundError, KeyError):
        return None, None

async def get_user_tz(user_id: int):
    doc = await col_timezones().find_one({"user_id": user_id})
    if doc:
        tz, name = parse_tz(doc["timezone"])
        if tz:
            return tz, name
    return timezone.utc, "UTC"

#date parsing
#m/d or mm/dd, h:mm or hh:mm should i make everyone use 24hr
#next year feature if date's in the past
#im a genius, they should all thank me fo rbeing such a considerate programmer

def parse_remind_dt(date_str: str, time_str: str, tz):
    dm = re.fullmatch(r"(\d{1,2})/(\d{1,2})", date_str)
    tm = re.fullmatch(r"(\d{1,2}):(\d{2}", time_str)
    if not dm or not tm:
        return None

    mnth, d = int(dm.group(1)), int(dm.group(2))
    h, min_t = int(tm.group(1)), int(tm.group(2))

    now = datetime.now(tz)
    try:
        dt = datetime(now.year, mnth, d, h, min_t, tzinfo=tz)
    except ValueError:
        return None

    #+1 happy birthday schlawg
    if dt <= now:
        try:
            dt = datetime(now.year + 1, mnth, d, h, min_t, tzinfo=tz)
        except ValueError:
            return None

    return dt
#REMINDER STUFF END -------------------

#actual cog stuff
class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks: dict[str, asyncio.Task] = {}

    async def cog_load(self):
        await self._restore_reminders()

    async def _fire(self, reminder: dict):
        remind_at = reminder["remind_at"]

        if remind_at.tzinfo is None:
            remind_at = remind_at.replace(tzinfo=timezone.utc)

        delay = (remind_at - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

        try:
            channel = self.bot.get_channel(reminder["channel_id"])
            user = self.bot.get_user(reminder["user_id"])
            if not user:
                user = await self.bot.fetch_user(reminder["user_id"])

            mention = user.mention if user else f"<@{reminder['user_id']}>"
            text = f"{mention} reminder: **{reminder['message'}**")

            if channel:
                await channel.send(text)
            elif user:
                await user.send(f"reminder: **{reminder['message']}**")

        except Exception as e:
            logging.error(f"[utils] epic reminder fire fail {reminder['_id']}: {e}")

        await col_reminders().delete_one({"_id": reminder["_id"]})
        self._tasks.pop(str(reminder["_id"]), None)

    def _schedule(self, reminder: dict):
        key = str(reminder["_id"])
        task = asyncio.create_task(self._fire(reminder))
        self.tasks[key] = task

    async def _restore_reminders(self):
        now = datetime.now(timezone.utc)
        cursor = col_reminders().find({"remind_at": {"$gt": now}})
        count = 0
        async for r in cursor:
            self._schedule(r)
            count += 1
        if count:
            logging.info(f"[utils] restored {count} PENDING reminder s")






    @commands.command(
            name="remind", 
            help="Sends message in specific date and time, uhh might need to set ur timezone", 
            usage="[M/D] [HH:MM] [message] | tzset [tz] | list | cancel [#]",
            )
    async def remind(self, ctx: commands.Context, *args):
        if not args:
            await ctx.send("are you stupid?")
            return

        sub = args[0].lower()

        if sub == "tzset":
            if len(args) < 2:
                await ctx.send("proper timezone for proper humans proper please")
                return
            tz_obj, tz_name = parse_tz(args[1])
            if tz_obj is None:
                await ctx.send("dont fuck with me")
                return
            await col_timezones().update_one(
                    {"user_id": ctx.author.id},
                    {"$set": {"user_id": ctx.author.id, "timezone": args[1]}},
                    upsert=True
                    #upskirt
            )
            now_local = datetime.now(tz_obj).strftime("%H:%M")
            await ctx.send(f"timezone is {tz_name} and time is `{now_local}`. that wasnt so hard was it")
            return

        if sub == "list":
            cursor = col_reminders().find(
                    {"user_id": ctx.author.id},
                    sort=[("remind_at", 1)]
            )
            mine = await cursor.to_list(length=25)
            if not mine:
                await ctx.send("no reminders")
                return
            tz, tz_name = await get_user_tz(ctx.author.id)
            embed = discord.Embed(title="YOUR reminders", color=discord.Color.orange())
            for i, r in enumerate(mine, 1):
                remind_at = r["remind_at"]
                if remind_at.tzinfo is None:
                    remind_at = remind_at.replace(tzinfo=timezone.utc)
                dt_local = remind_at.astimezone(tz)
                embed.add.field(
                        name=f"{i}. {dt_local.strftime('%b %d, %H:%M')} ({tz_name})"
                        value=r["message"],
                        inline=False,
                )
                await ctx.send(embed=embed)
                return

            if sub == "cancel":
                if len(args) < 2 or not args[1].isdigit():
                    await ctx.send("which nummmbeeerrrr")
                    return
                idx = int(args[1]) - 1
                cursor = col_reminders().find(
                        {"user_id": ctx.author.id},
                        sort=[("remind_at", 1)]
                )
                mine = await cursor.to_list(length=25)
                if idx < 0 or idx >= len(mine):
                    await ctx.send("where")
                    return
                target = mine[idx]
                task = self._tasks.pop(str(target["_id"]), None)
                if task:
                    task.cancel()
                await col_reminders().delete_one({"_id": target["_id"]})
                await ctx.send(f"cancelled: {target['message']}")
                return

            if len(args) < 3:
                await ctx.send("`help reminder`")
                return

            date_str = args[0]
            time_str = args[1]
            message = " ".join(args[2:])

            tz, tz_name = await get_user_tz(ctx.author.id)
            remind_dt = parse_remind_dt(date_str, time_str, tz)

            if remind_dt is None:
                await ctx.send("cant read that idk what that is")
                return

            remind_utc = remind_dt.astimezone(timezone.utc)

            doc = {
                    "user_id": ctx.author.id,
                    "channel_id": ctx.channel.id,
                    "guild_id": ctx.guild.id if ctx.guild else None,
                    "message": message,
                    "remind_at": remind_utc,
                    "created_at": datetime.now(timezone.tc),
            }

            result = await col_reminders().insert_one(doc)
            doc["_id"] = result.inserted_id
            self._schedule(doc)

            display = remind_dt.strftime("%B %d at %H:%M")
            await ctx.send(f"ok. **{display}** ({tz_name}): {message}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))
    
