import discord
import os
import aiohttp
import asyncio
from discord.ext import commands, tasks
from datetime import datetime, timedelta

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Football API configuration
FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
BARCELONA_TEAM_ID = 81

# Store match notifications to avoid duplicates
notified_matches = set()

class BarcelonaTracker:
    def __init__(self):
        self.current_matches = []
    
    async def get_barcelona_matches(self):
        """Fetch Barcelona matches from API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'X-Auth-Token': FOOTBALL_API_KEY}
                async with session.get(
                    f'https://api.football-data.org/v4/teams/{BARCELONA_TEAM_ID}/matches',
                    headers=headers
                ) as response:
                    data = await response.json()
                    return data['matches']
        except:
            return self.get_manual_matches()
    
    def get_manual_matches(self):
        """Manual match data as fallback"""
        return [
            {
                'id': 1,
                'homeTeam': {'name': 'Barcelona'},
                'awayTeam': {'name': 'Olympiacos'},
                'competition': {'name': 'Champions League'},
                'status': 'SCHEDULED',
                'utcDate': '2024-11-05T20:00:00Z',
                'score': {'fullTime': {'home': None, 'away': None}}
            }
        ]
    
    def format_match_embed(self, match):
        """Create beautiful embed for each match"""
        home_team = match['homeTeam']['name']
        away_team = match['awayTeam']['name']
        competition = match['competition']['name']
        status = match['status']
        date = match['utcDate'][:10]
        
        status_info = {
            'SCHEDULED': ('🟢', 'UPCOMING'),
            'LIVE': ('🔴', 'LIVE'),
            'IN_PLAY': ('🔴', 'LIVE'),
            'PAUSED': ('🟡', 'HALFTIME'),
            'FINISHED': ('✅', 'FINAL')
        }
        
        emoji, status_text = status_info.get(status, ('⚫', status))
        
        embed = discord.Embed(
            title=f"🔵🔴 {home_team} vs {away_team} 🔴⚪",
            color=0x004b98 if 'Barcelona' in home_team else 0xa50044
        )
        
        embed.add_field(name="🏆 Competition", value=competition, inline=True)
        embed.add_field(name="📅 Date", value=date, inline=True)
        embed.add_field(name="📊 Status", value=f"{emoji} {status_text}", inline=True)
        
        if match['score']['fullTime']['home'] is not None:
            home_score = match['score']['fullTime']['home']
            away_score = match['score']['fullTime']['away']
            embed.add_field(name="🎯 Score", value=f"{home_score} - {away_score}", inline=False)
        
        if status in ['LIVE', 'IN_PLAY'] and match.get('minute'):
            embed.add_field(name="⏰ Minute", value=f"{match['minute']}'", inline=True)
        
        return embed

tracker = BarcelonaTracker()

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is now online!')
    print('🔵🔴 Barcelona LIVE tracker is ready!')
    await bot.change_presence(activity=discord.Game(name="!barca for live matches"))
    check_matches.start()
    check_match_starts.start()

@tasks.loop(minutes=5)
async def check_matches():
    """Background task to check for match updates"""
    try:
        tracker.current_matches = await tracker.get_barcelona_matches()
    except Exception as e:
        print(f"Error updating matches: {e}")

@tasks.loop(minutes=1)
async def check_match_starts():
    """Check if any matches have just started"""
    try:
        for match in tracker.current_matches:
            match_id = match.get('id')
            status = match['status']
            
            if status in ['LIVE', 'IN_PLAY'] and match_id not in notified_matches:
                await send_match_start_notification(match)
                notified_matches.add(match_id)
                
    except Exception as e:
        print(f"Error checking match starts: {e}")

async def send_match_start_notification(match):
    """Send notification to SPECIFIC channel from environment variable"""
    home_team = match['homeTeam']['name']
    away_team = match['awayTeam']['name']
    competition = match['competition']['name']
    
    embed = discord.Embed(
        title="🚨 **MATCH STARTED!** 🚨",
        description=f"**{home_team} vs {away_team}**\n🏆 {competition}",
        color=0x00ff00
    )
    embed.add_field(name="📊 Status", value="🔴 **LIVE**", inline=True)
    embed.add_field(name="⏰ Started", value="Just now!", inline=True)
    embed.add_field(name="📺 Watch", value="Check your sports app!", inline=False)
    embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/en/thumb/4/47/FC_Barcelona_%28crest%29.svg/1200px-FC_Barcelona_%28crest%29.svg.png")
    
    # Get channel ID from environment variable
    CHANNEL_ID = int(os.getenv('NOTIFICATION_CHANNEL_ID'))
    
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            print(f"✅ Match notification sent to channel: {channel.name}")
        else:
            print("❌ Could not find the specified channel")
    except Exception as e:
        print(f"❌ Error sending notification: {e}")

# 🔵 BARCELONA COMMANDS
@bot.command()
async def barca(ctx):
    """Show ONLY upcoming Barcelona matches"""
    if not tracker.current_matches:
        await ctx.send("🔵🔴 Fetching Barcelona matches...")
        tracker.current_matches = await tracker.get_barcelona_matches()
    
    if not tracker.current_matches:
        embed = discord.Embed(
            title="🔵🔴 No Matches Found",
            description="Check back later for upcoming matches!",
            color=0x004b98
        )
        await ctx.send(embed=embed)
        return
    
    upcoming_matches = []
    for match in tracker.current_matches:
        status = match['status']
        if status in ['SCHEDULED', 'TIMED']:
            upcoming_matches.append(match)
    
    upcoming_matches.sort(key=lambda x: x['utcDate'])
    upcoming_matches = upcoming_matches[:3]
    
    if not upcoming_matches:
        embed = discord.Embed(
            title="🔵🔴 No Upcoming Matches",
            description="No scheduled matches found. Check back later!",
            color=0x004b98
        )
        await ctx.send(embed=embed)
        return
    
    for match in upcoming_matches:
        embed = tracker.format_match_embed(match)
        await ctx.send(embed=embed)

@bot.command()
async def barca_live(ctx):
    """Show only LIVE Barcelona matches"""
    live_matches = [m for m in tracker.current_matches if m['status'] in ['LIVE', 'IN_PLAY']]
    
    if not live_matches:
        await ctx.send("🔵🔴 No live matches right now. Use `!barca` for upcoming matches.")
        return
    
    for match in live_matches:
        embed = tracker.format_match_embed(match)
        await ctx.send(embed=embed)

# 🛠️ UTILITY COMMANDS
@bot.command()
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Pong! {latency}ms')

@bot.command()
async def hello(ctx):
    """Say hello to the bot"""
    await ctx.send(f'👋 Hello {ctx.author.mention}!')

@bot.command()
async def hi(ctx):
    """Say hi to the bot"""
    await ctx.send(f'👋 Hi {ctx.author.mention}!')

@bot.command()
async def help_bot(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🔵🔴 Barcelona Bot Commands",
        color=0x004b98
    )
    embed.add_field(name="!barca", value="Show upcoming Barcelona matches", inline=False)
    embed.add_field(name="!barca_live", value="Show only LIVE matches", inline=False)
    embed.add_field(name="!ping", value="Check bot latency", inline=False)
    embed.add_field(name="!hello", value="Say hello to the bot", inline=False)
    embed.add_field(name="!hi", value="Say hi to the bot", inline=False)
    embed.add_field(name="!help_bot", value="Show this help message", inline=False)
    
    await ctx.send(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))
