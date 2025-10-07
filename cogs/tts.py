import discord
from discord.ext import commands
from gtts import gTTS
import asyncio
import os
import random

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Maps guild_id → voice_client

    # --- JOIN COMMAND ---
    @commands.slash_command(name="join_tts", description="Join your current voice channel for auto TTS.")
    async def join_tts(self, ctx: discord.ApplicationContext):
        if ctx.author.voice is None:
            await ctx.respond("You need to be in a voice channel first!")
            return

        voice_channel = ctx.author.voice.channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client is None:
            vc = await voice_channel.connect()
            self.voice_clients[ctx.guild.id] = vc
            await ctx.respond(f"Joined {voice_channel.name} and ready to speak automatically!")
        else:
            await ctx.respond("I'm already connected!")

    # --- LEAVE COMMAND ---
    @commands.slash_command(name="leave_tts", description="Leave the voice channel and stop TTS.")
    async def leave_tts(self, ctx: discord.ApplicationContext):
        voice_client = self.voice_clients.get(ctx.guild.id)
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            del self.voice_clients[ctx.guild.id]
            await ctx.respond("Disconnected and TTS stopped.")
        else:
            await ctx.respond("I'm not in a voice channel!")

    # --- MESSAGE LISTENER ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages or DMs
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        voice_client = self.voice_clients.get(guild_id)

        # Only speak if connected
        if not voice_client or not voice_client.is_connected():
            return

        # Create temporary filename
        text = message.content.strip()
        if not text:
            return

        # Limit very long messages
        if len(text) > 300:
            text = text[:300] + " ..."

        filename = f"tts_{random.randint(1000,9999)}.mp3"

        try:
            # Generate TTS
            tts = gTTS(text=text, lang='en')
            tts.save(filename)

            # Play the audio
            if not voice_client.is_playing():
                audio_source = discord.FFmpegPCMAudio(filename)
                voice_client.play(audio_source)

                # Wait for playback to finish
                while voice_client.is_playing():
                    await asyncio.sleep(0.5)
            else:
                # Wait until current audio finishes
                while voice_client.is_playing():
                    await asyncio.sleep(0.5)
                audio_source = discord.FFmpegPCMAudio(filename)
                voice_client.play(audio_source)

        except Exception as e:
            print(f"Error generating or playing TTS: {e}")

        finally:
            # Clean up
            if os.path.exists(filename):
                os.remove(filename)


def setup(bot):
    bot.add_cog(TTS(bot))
