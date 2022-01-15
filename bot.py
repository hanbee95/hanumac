import discord
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import youtube_dl
from youtube_search import YoutubeSearch
import ffmpeg
import pafy
import vlc
import re, requests, subprocess, urllib.parse, urllib.request
from bs4 import BeautifulSoup
import googleapiclient.discovery
from urllib.parse import parse_qs, urlparse
import urllib.parse
import sys
import asyncio
import threading
import random
from time import time
from pytube import YouTube, Playlist
from concurrent.futures import ThreadPoolExecutor, as_completed

class server:
    def __init__(self):
        self.currentSong = {} 
        self.previousSong = {}  
        self.nextSong = {}
        self.songList = {}
        self.loopstatus = 0
servers = {} #server list

load_dotenv()

# Get the API token from the .env file.
DISCORD_TOKEN = os.getenv("discord_token")

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='$', intents=intents)

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl_format_options_list = {'outtmpl': '%(id)s%(ext)s', 'quiet':True}
ytdl_list = youtube_dl.YoutubeDL(ytdl_format_options_list)

ffmpeg_options = {
    'options': '-vn'
}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename, data.get('title')


@bot.event
async def on_ready():
    print("The bot is ready!")
    
    print(f'{bot.user} has connected to Discord!')
    GUILD = []
    async for guild_fetch in bot.fetch_guilds(limit=150):
        GUILD.append(guild_fetch.name)    
    print(f"Allowed servers: {GUILD}")

    for guild in bot.guilds:
    
        print(guild.name)
        servers[guild.name] = server()
        print("Was added to the servers list")
        if not guild.name in GUILD:
            print("being broken")
            break

        print(
            f'{client.user} is connected to the following guild:\n'
            f'{guild.name}(id: {guild.id})\n'
        )

    #currentServer = server()

@bot.command()
async def hello(ctx):
    await ctx.send("Hello!")

@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
        await ctx.send("Now HanUmAc bot is connected to {} channel".format(ctx.message.author.name))
    await channel.connect()

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@bot.command(name='play', aliases=['p','queue','PLAY'], help='To queue up and play songs')
async def play(ctx,*urls):
    url = ' '.join(urls)
    ##Error control
    if url == '' :
        await ctx.send('INVALID ACCESS:: context should be \'play_test <song name>\'')
        return    
    if discord.utils.get(bot.voice_clients, guild=ctx.guild):
        #await ctx.send('Already connected to voice channel')
        print ('Already connected to voice channel')
    else:
        if not ctx.message.author.voice:
            await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
            return
        else:
            channel = ctx.message.author.voice.channel
            await ctx.send("Now HanUmAc bot is connected to {} channel".format(ctx.message.author.name))
        await channel.connect()
    #WORKING ON THIS -- queue up
    server = ctx.message.guild
    voice_channel = server.voice_client
    print(server)

    currentServer = servers[ctx.guild.name]

    if str(server.id) in currentServer.songList:
        currentServer.songList[str(server.id)].append(url)
    else:
        currentServer.songList[str(server.id)] = [url]
    if len(currentServer.currentSong ) == 0:
        currentServer.currentSong = currentServer.songList[str(server.id)][0]
    print (currentServer.currentSong)
    print (currentServer.songList)
    print (currentServer.loopstatus)
    if not voice_channel.is_playing():
        asyncio.run_coroutine_threadsafe(play_test(ctx, currentServer.loopstatus), bot.loop)
    await ctx.send('**Now {} is added in song list:** '.format(url))

@bot.command(name='play_test', help='To play song test version')
async def play_test(ctx, loopstatus=0):
    print ("play_test")
    server = ctx.message.guild
    voice_channel = server.voice_client    
    currentServer = servers[ctx.guild.name]
    currentServer.loopstatus = loopstatus
    print (currentServer.loopstatus)

    if not voice_channel.is_playing():
        if len(currentServer.songList[str(server.id)] ) >= 1:
            print (currentServer.songList[str(server.id)])
            async with ctx.typing():  # for downloading I guess
                filename, data = await YTDLSource.from_url(currentServer.currentSong, loop=bot.loop)
                print (filename)
                #if currentServer.loopstatus == 0:
                print ("check point 1")
                voice_channel.play(discord.FFmpegPCMAudio(source=filename), 
                    after = lambda e: asyncio.run_coroutine_threadsafe(play_test(ctx, currentServer.loopstatus), bot.loop))
            await ctx.send('**Now playing:** {}'.format(data))

            if currentServer.loopstatus == 0:
                if len(currentServer.songList[str(server.id)] ) >= 1:
                    currentServer.songList[str(server.id)].pop(0)
                    if len(currentServer.songList[str(server.id)] ) >= 1:
                        currentServer.currentSong = currentServer.songList[str(server.id)][0]  
                    else:
                        print ("No more songs in the song list")
                        currentServer.currentSong = ''
                else:
                    print ("No more songs in the song list2")
                    currentServer.currentSong = ''
            else:
                if len(currentServer.songList[str(server.id)] ) >= 1:
                    currentServer.songList[str(server.id)].append(currentServer.songList[str(server.id)].pop(0))
                    currentServer.currentSong = currentServer.songList[str(server.id)][0]
                    print ("check point for loop")
                    print (currentServer.songList[str(server.id)])
                    print (currentServer.currentSong)
                else:
                    print ("No more songs in the song list2")
                    currentServer.currentSong = ''               
            
@bot.command(name='loop', help='To loop')
async def loop(ctx):
    print ("to make loop")
    server = ctx.message.guild
    voice_channel = server.voice_client    
    currentServer = servers[ctx.guild.name]
    currentServer.loopstatus = 1

@bot.command(name='unloop', help='To unloop')
async def unloop(ctx):
    print ("to make loop")
    server = ctx.message.guild
    voice_channel = server.voice_client    
    currentServer = servers[ctx.guild.name]
    currentServer.loopstatus = 0
    asyncio.run_coroutine_threadsafe(play_test(ctx, currentServer.loopstatus), bot.loop)

@bot.command(name='playlist', aliases=['l','list','LIST'], help='To list')
async def playlist(ctx):
    print ("to show list")
    server = ctx.message.guild
    voice_channel = server.voice_client    
    currentServer = servers[ctx.guild.name]
    await ctx.send('**Song list**')
    for idx, song in enumerate(currentServer.songList[str(server.id)]):
        await ctx.send('\t{}. {}'.format(idx+1, song))
    #await ctx.send('**Now playing:** {}'.format(currentServer.songList[str(server.id)]))




@bot.command(name='shuffle', help='To shuffle the playlist')
async def shuffle(ctx):
    print ("to shuffle list")
    server = ctx.message.guild
    voice_channel = server.voice_client    
    currentServer = servers[ctx.guild.name]
    random.shuffle(currentServer.songList[str(server.id)])
    currentServer.currentSong = currentServer.songList[str(server.id)][0]
    await ctx.send('**Now shuffled the songlist:** {}'.format(currentServer.songList[str(server.id)]))


# @bot.command(name='play_song', help='To play song')
# async def play(ctx,*urls):
#     #try :
#         url = ' '.join(urls)
#         server = ctx.message.guild
#         voice_channel = server.voice_client
#         print (server.voice_client.channel)
#         print (voice_channel)
        
#         currentServer = servers[ctx.guild.name]
#         print (currentServer)
#         currentServer.currentSong = url
#         print (currentServer.currentSong)

#         async with ctx.typing():  # for downloading I guess
#             filename, data = await YTDLSource.from_url(url, loop=bot.loop)
#             print (filename)
#             print (data)
#             voice_channel.play(discord.FFmpegPCMAudio(source=filename))
#         #WORKING ON THIS -- if music is played -- queue up, else -- play
#         #WORKING ON THIS -- changing volume -- it is sooo noisy
#         #voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
#         #voice_channel.source.volume = 0.1
#         await ctx.send('**Now playing:** {}'.format(data))
#     #except:
#     #    await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='play_link', help='To play song without download files')
async def play_link(ctx,*urls):
    url = ' '.join(urls).replace(" ", "+")
    plus = urllib.parse.quote(url)
    server = ctx.message.guild
    voice_channel = server.voice_client
    #html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + url_d)
    #html = urllib.request.urlopen("https://www.youtube.com/results?search_query=고칼로리")
    html = urllib.request.urlopen("https://www.youtube.com/results?search_query="+plus)
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())  
    song = pafy.new(video_ids[0])  # creates a new pafy object
    print (song)
    audio = song.getbestaudio()  # gets an audio source
    source = FFmpegPCMAudio(audio.url, **FFMPEG_OPTIONS)  # converts the youtube audio source into a source discord can use
    voice_channel.play(source)  # play the source
    await ctx.send('**Now playing:** {}'.format(song.title))

@bot.command(name='listplay', help='To play list from youtube')
async def listplay(ctx, list):
    print ("listplay")
    server = ctx.message.guild
    voice_channel = server.voice_client    
    currentServer = servers[ctx.guild.name]
    #currentServer.loopstatus = loopstatus    
    video_links = Playlist(list).video_urls

    def get_video_title(link):
        title = YouTube(link).title
        return title

    processes = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for url in video_links:
            processes.append(executor.submit(get_video_title, url))

    video_titles = []
    for task in as_completed(processes):
        video_titles.append(task.result())
        print(task.result())
        asyncio.run_coroutine_threadsafe(play(ctx, task.result()), bot.loop)
        await ctx.send('**{}** is queued now:'.format(task.result())) 
        #print (task)
    #await ctx.send('**titles:** {}'.format(video_titles))    

@bot.command(name='play_stream',  help='To play song without download files')
async def play_stream(ctx,*urls):
    url = ' '.join(urls).replace(" ", "+")
    print (url)
    server = ctx.message.guild
    voice_channel = server.voice_client
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    playlist_id = query["list"][0]    
    print(f'get all playlist items links from {playlist_id}')
    #WORKING ON THIS - HAN : Need to get API Key from google client
    devkey = "AIzaSyDSTQfcKw8SkVGOg06P-Mjp8e5BKxeFpUw"
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey = devkey)
    request = youtube.playlistItems().list(
        part = "snippet",
        playlistId = playlist_id,
        maxResults = 50
    )
    response = request.execute()
    
    playlist_items = []
    while request is not None:
        response = request.execute()
        playlist_items += response["items"]
        request = youtube.playlistItems().list_next(request, response)
    
    print(f"total: {len(playlist_items)}")
    print([ 
        f'https://www.youtube.com/watch?v={t["snippet"]["resourceId"]["videoId"]}&list={playlist_id}&t=0s'
        for t in playlist_items
    ])    
    #song = pafy.get_playlist2(url)
    #print (song)
    #audio = song.getbestaudio()  # gets an audio source
    #source = FFmpegPCMAudio(audio.url, **FFMPEG_OPTIONS)  # converts the youtube audio source into a source discord can use
    #voice_channel.play(source)  # play the source
    #await ctx.send('**Now playing:** {}'.format(song.title))

@bot.command(name='volume', help='To change volume')
async def volume(ctx,newvolume):
    print (newvolume)
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
    voice_channel.source.volume = float(newvolume)
    print (voice_channel.source.volume) #this value changed, but bot voice volume doesn't change multiple times
    await ctx.send('volume changed to  {}'.format(newvolume))


@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("The bot is paused.")
    else:
        await ctx.send("The bot is not playing anything at the moment.")
    
@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send("The bot is resumed.")
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

#bot.run(DISCORD_TOKEN)

@bot.command(help = "Prints details of Server")
async def where_am_i(ctx):
    owner=str(ctx.guild.owner)
    region = str(ctx.guild.region)
    guild_id = str(ctx.guild.id)
    memberCount = str(ctx.guild.member_count)
    icon = str(ctx.guild.icon_url)
    desc=ctx.guild.description
    
    embed = discord.Embed(
        title=ctx.guild.name + " Server Information",
        description=desc,
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=icon)
    embed.add_field(name="Owner", value=owner, inline=True)
    embed.add_field(name="Server ID", value=guild_id, inline=True)
    embed.add_field(name="Region", value=region, inline=True)
    embed.add_field(name="Member Count", value=memberCount, inline=True)

    await ctx.send(embed=embed)

    members=[]
    async for member in ctx.guild.fetch_members(limit=10) :
        await ctx.send('Name : {}\t Status : {}\n Joined at {}'.format(member.display_name,str(member.status),str(member.joined_at)))

@bot.command()
async def tell_me_about_yourself(ctx):
    text = "My name is WallE!\n I was built by Kakarot2000. At present I have limited features(find out more by typing !help)\n :)"
    await ctx.send(text)

if __name__ == "__main__" :
    bot.run(DISCORD_TOKEN)
