import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime
import os

SESSIONS_FILE = "sessions.json"

# --- Helper functions ---
def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_sessions(sessions):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)

def generate_session_id(channel_id):
    return f"{channel_id}-{int(datetime.utcnow().timestamp())}"

def create_session_embed(session, host_tag):
    drivers = session.get("drivers", [])
    staff = session.get("juniorstaff", [])
    trainees = session.get("trainees", [])

    # Format time nicely
    time_display = session["time"]
    try:
        timestamp = int(datetime.fromisoformat(session["time"]).timestamp())
        time_display = f"<t:{timestamp}:f> (<t:{timestamp}:R>)"
    except Exception:
        pass

    embed = discord.Embed(
        title="📢 This is a scheduled POP driving session. Sign up below! 🚗",
        color=discord.Color.blue(),
        description=(
            f"**Host**\n<@{session['host_id']}> ({host_tag})\n"
            f"**Time**\n{time_display}\n"
            f"**Duration**\n{session['duration']}\n"
            f"**Channel**\n<#${session['channel_id']}>\n\n"
            f"**— — — Roster Signups — — —**"
        )
    )
    embed.add_field(
        name=f"🏎️ Drivers ({len(drivers)})",
        value="\n".join(f"<@{u['id']}>" for u in drivers) or "No drivers signed up yet.",
        inline=False
    )
    embed.add_field(
        name=f"🛠️ Staff ({len(staff)})",
        value="\n".join(f"<@{u['id']}>" for u in staff) or "No staff members signed up yet.",
        inline=False
    )
    embed.add_field(
        name=f"📚 Trainees ({len(trainees)})",
        value="\n".join(f"<@{u['id']}>" for u in trainees) or "No trainees signed up yet.",
        inline=False
    )
    embed.set_footer(text=f"Session ID: {session['id']}")
    embed.timestamp = datetime.utcnow()
    return embed

def create_session_buttons(session_id):
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Sign up as Driver", style=discord.ButtonStyle.primary, custom_id=f"SIGNUP_{session_id}_driver"))
    view.add_item(discord.ui.Button(label="Sign up as Staff", style=discord.ButtonStyle.secondary, custom_id=f"SIGNUP_{session_id}_juniorstaff"))
    view.add_item(discord.ui.Button(label="Sign up as Trainee", style=discord.ButtonStyle.success, custom_id=f"SIGNUP_{session_id}_trainee"))
    view.add_item(discord.ui.Button(label="Close Session", style=discord.ButtonStyle.danger, custom_id=f"CLOSE_{session_id}_close"))
    return view

# --- Cog Definition ---
class SessionBook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sessionbook", description="Book a new driving session")
    @app_commands.describe(
        time="Time and date of the session (e.g., 2025-10-07T18:30)",
        duration="Expected duration (e.g., 1 hour)"
    )
    async def sessionbook(self, interaction: discord.Interaction, time: str, duration: str):
        await interaction.response.defer(ephemeral=True)
        host_id = interaction.user.id
        channel_id = interaction.channel.id

        session_id = generate_session_id(channel_id)
        session = {
            "id": session_id,
            "time": time,
            "duration": duration,
            "channel_id": channel_id,
            "host_id": host_id,
            "drivers": [],
            "juniorstaff": [],
            "trainees": [],
            "message_id": None
        }

        embed = create_session_embed(session, interaction.user.name)
        view = create_session_buttons(session_id)

        message = await interaction.channel.send(embed=embed, view=view)
        session["message_id"] = message.id

        sessions = load_sessions()
        sessions[session_id] = session
        save_sessions(sessions)

        await interaction.followup.send(f"✅ Session booked for **{time}** in <#{channel_id}>.", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        if not custom_id:
            return

        parts = custom_id.split("_")
        action, session_id = parts[0], parts[1]
        role = parts[2] if len(parts) > 2 else None

        sessions = load_sessions()
        session = sessions.get(session_id)
        if not session:
            return await interaction.response.send_message("❌ Session no longer active.", ephemeral=True)

        member = interaction.user
        roster_map = {"driver": "drivers", "juniorstaff": "juniorstaff", "trainee": "trainees"}

        if action == "CLOSE":
            if member.id != session["host_id"]:
                return await interaction.response.send_message("❌ Only the host can close this session.", ephemeral=True)
            del sessions[session_id]
            save_sessions(sessions)
            embed = discord.Embed(title="Session Closed", description=f"The session hosted by <@{session['host_id']}> has been closed.", color=discord.Color.red())
            await interaction.message.edit(embed=embed, view=None)
            return await interaction.response.send_message("✅ Session closed.", ephemeral=True)

        if action == "SIGNUP" and role in roster_map:
            role_key = roster_map[role]

            # Remove user from all roles
            for key in roster_map.values():
                session[key] = [u for u in session[key] if u["id"] != member.id]

            # Add to chosen role
            session[role_key].append({"id": member.id, "tag": str(member)})

            sessions[session_id] = session
            save_sessions(sessions)

            embed = create_session_embed(session, (await self.bot.fetch_user(session["host_id"])).name)
            await interaction.message.edit(embed=embed)
            await interaction.response.send_message(f"✅ You signed up as **{role.capitalize()}**.", ephemeral=True)

# --- Setup function ---
async def setup(bot):
    await bot.add_cog(SessionBook(bot))
