import discord
import os
from discord.ext import commands

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is now online!')
    print('🔵🔴 Barcelona bot is ready!')
    await bot.change_presence(activity=discord.Game(name="!barca for match info"))

@bot.command()
async def barca(ctx):
    embed = discord.Embed(
        title="🔵🔴 Barcelona FC",
        description="Match information and scores",
        color=0x004b98
    )
    embed.add_field(name="Next Match", value="Barcelona vs Real Madrid", inline=False)
    embed.add_field(name="Date", value="Saturday, 8:00 PM", inline=True)
    embed.add_field(name="Competition", value="La Liga", inline=True)
    embed.add_field(name="Status", value="⚽ Coming soon with live data!", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def hello(ctx):
    await ctx.send(f'👋 Hello {ctx.author.mention}!')

@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! {round(bot.latency * 1000)}ms')

bot.run(os.getenv('DISCORD_TOKEN'))
