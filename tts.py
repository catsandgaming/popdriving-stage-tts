import discord
from discord.ext import commands
from discord import app_commands
from gtts import gTTS
import os

VOICE_FOLDER = "voice_files"
if not os.path.exists(VOICE_FOLDER):
    os.makedirs(VOICE_FOLDER)

class StageTTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Keep track of which guilds the bot is connected to

    # --- Slash command: /stagetts ---
    @app_commands.command(name="stagetts", description="Join your voice channel and start TTS")
    async def stagetts(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)

        channel = interaction.user.voice.channel

        if interaction.guild.id in self.voice_clients and self.voice_clients[interaction.guild.id].is_connected():
            return await interaction.response.send_message("✅ Already connected to a voice channel.", ephemeral=True)

        vc = await channel.connect()
        self.voice_clients[interaction.guild.id] = vc
        await interaction.response.send_message(f"🎙️ Joined {channel.name}. I will read messages automatically!", ephemeral=True)

    # --- Slash command: /leavetts ---
    @app_commands.command(name="leavetts", description="Leave the voice channel and stop TTS")
    async def leavetts(self, interaction: discord.Interaction):
        vc = self.voice_clients.get(interaction.guild.id)
        if vc and vc.is_connected():
            await vc.disconnect()
            self.voice_clients.pop(interaction.guild.id)
            await interaction.response.send_message("✅ Disconnected and TTS stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not connected to a voice channel.", ephemeral=True)

    # --- Listen to messages and read them ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return  # Ignore other bots

        vc = self.voice_clients.get(message.guild.id)
        if not vc or not vc.is_connected():
            return  # Only read if connected to voice

        text = message.content
        if not text.strip():
            return

        # Generate TTS file
        filename = os.path.join(VOICE_FOLDER, f"{message.id}.mp3")
        tts = gTTS(text=text, lang="en")
        tts.save(filename)

        # Play audio
        if not vc.is_playing():
            vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=filename), after=lambda e: os.remove(filename))

# --- Setup function ---
async def setup(bot):
    await bot.add_cog(StageTTS(bot))
