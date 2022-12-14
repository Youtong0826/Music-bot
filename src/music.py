from youtube_dl import YoutubeDL
from lib import get_video_info
import datetime
import discord
import ctypes.util

try:
    find_opus = ctypes.util.find_library('opus')
    discord.opus.load_opus(find_opus)

except:
    print("may not have opus..")

class Music(discord.Cog):
    def __init__(self, bot:discord.Bot):
        self.bot = bot
        self.icon_url = "https://cdn.discordapp.com/avatars/1019973538905604127/be1001af52ba74cd2895ea45b7b292c1.png?size=1024"

        self.voice_clients = {}

        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}

        self.FFMPEG_OPTIONS = {
            'executable':"C:\\ffmpeg\\bin\\ffmpeg.exe",
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    def setup_status(self,id:discord.Guild.id):
        if id not in self.voice_clients.keys():

            default = {
                "is_playing" : False,
                "is_paused" : False,
                "music_queue" : [],
                "vc" : None
            }

            self.voice_clients[id] = default
    
    def get_status(self,id:discord.Guild.id):
        return self.voice_clients[id]

    def search_yt(self, item):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try: 
                data = ydl.extract_info("ytsearch:%s" % item, download=False,)
                info = data['entries'][0]
                url = info['webpage_url']
                
            except Exception: 
                return False

        return {'source': info['formats'][0]['url'], 'title': info['title'],'url':url}

    def play_next(self,id:discord.Guild.id):
        self.setup_status(id)
        vc_status = self.get_status(id)

        if len( vc_status["music_queue"]) > 0:

            vc_status["is_playing"] = True

            vc_status["music_queue"].pop(0)

            if vc_status["music_queue"] != []:
                m_url = vc_status["music_queue"][0][0]['source']

                vc_status["vc"].play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(id))

            else:
                vc_status["is_playing"] = False
            
        else:
            vc_status["is_playing"] = False
    
    async def play_music(self, ctx, id:discord.Guild.id,check=False):
        self.setup_status(id)
        vc_status = self.get_status(id)

        if check:
            if len(vc_status["music_queue"]) <= 1:
                vc_status["is_playing"] = False
                return False

        if len(vc_status["music_queue"]) > 0:
            vc_status["is_playing"] = True

            m_url = vc_status["music_queue"][0][0]['source']
            
            if vc_status["vc"] == None or not vc_status["vc"].is_connected():
                vc_status["vc"] = await vc_status["music_queue"][0][1].connect()
                
                if vc_status["vc"] == None:
                    await ctx.respond("???????????????????????????");return
            else:
                await vc_status["vc"].move_to(vc_status["music_queue"][0][1])

            
            vc_status["vc"].play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(id))

        else:
            vc_status["is_playing"] = False
            return False

    def music_embed(self,url:str, id:discord.Guild.id, ctx) -> dict:
        data = get_video_info(url)
        description = data['description']

        embed = discord.Embed(
            title=f"???????????? {data['title']}",
            description=description[:50] + f' ...[????????????]({url})',
            color=discord.Colour.nitro_pink(),
            timestamp=datetime.datetime.utcnow()
        )

        udt = data.get("upload_date")
        udt = udt[:-4] + "/" + udt[4:6] + "/" + udt[6:8]

        tags = ""
        tag_limit = 0

        for n in data.get('tags'):
            if tag_limit < 3:
                tag_limit += 1
                tags += "#" + str(n).replace("'","") + " "

        duration_min = str(data.get('duration')//60)
        duration_sec = str(data.get('duration')%60)

        if int(duration_min) < 10:
            duration_min = "0" + duration_min 

        if int(duration_sec) < 10:
            duration_sec = "0" + duration_sec

        fields = {
            "???? ????????????" : data.get("view_count"),
            "???? ??????": data.get("like_count"),
            "???? ??????": f"{duration_min}:{duration_sec}",
            "???? ????????????" : udt,
            "???? ?????????": data["uploader"],
            "???? ??????" : tags
        }

        for n in fields:
            embed.add_field(
                name=n,
                value=fields[n],
                inline=True
            )

        embed.set_image(url=data["thumbnail"])
        embed.set_footer(text="name",icon_url=self.icon_url)

        control_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="??????/??????",
            custom_id="control",
            emoji="??????",
            row=0
        )

        skip_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            custom_id="skip",
            label="?????????",
            emoji="???",
            row=0
        )

        queue_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            custom_id="queue",
            label="??????????????????",
            emoji="????",
            row=0
        )

        dc_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            custom_id="dc",
            label="????????????",
            emoji="????",
            row=1
        )

        buttons = [control_button,skip_button,queue_button,dc_button]

        async def button_callback(interaction:discord.Interaction):
            self.setup_status(id)
            vc_status = self.get_status(id)
            if interaction.custom_id == "control":
                if vc_status["is_playing"]:
                    vc_status["is_playing"] = False
                    vc_status["is_paused"] = True
                    vc_status["vc"].pause()

                    await interaction.response.send_message(f"`{interaction.user}` ???????????????!")

                else:
                    vc_status["is_playing"] = True
                    vc_status["is_paused"] = False
                    vc_status["vc"].resume()

                    await interaction.response.send_message(f"`{interaction.user}` ???????????????!")

            elif interaction.custom_id == "skip":
                if await self.play_music(ctx,ctx.author.guild.id,check=True) != False:
                    if vc_status["vc"] != None and vc_status["vc"]:
                        vc_status["vc"].stop()

                    await interaction.response.send_message(f"`{interaction.user}` ???????????????!")

                else: await interaction.response.send_message("????????????????????????")

            elif interaction.custom_id == "queue":
                embed = self.queue_embed(ctx.author.guild.id)

                if isinstance(embed,bool):
                    await interaction.response.send_message("???????????????????????????")
                else:
                    await interaction.response.send_message(embed=embed)

            elif interaction.custom_id == "dc":
                self.setup_status(ctx.author.guild.id)
                vc_status = self.get_status(ctx.author.guild.id)

                vc_status["is_playing"] = False
                vc_status["is_paused"] = False

                await vc_status["vc"].disconnect()
                await ctx.response.send_message("???????????????????????????~")
        
        view = discord.ui.View(timeout=None)

        for btn in buttons:
            view.add_item(btn)
            btn.callback = button_callback        

        return {"embed":embed,"view":view}

    def queue_embed(self,id:discord.Guild.id):
        self.setup_status(id)
        queue = self.get_status(id)["music_queue"]
        description = "???????????? - "

        for n in range(len(queue)):
            if n > 10:break
            description += f'**{queue[n][0]["title"]}**'

            if n == 0:
                description += "\n"

                for i in range(len(description)):
                    description += "???"
                

            if n+1 != len(queue):
                description += f"\n{n+1}. "

        if len(queue) == 1:
            description += "\n`???????????????`"

        embed = discord.Embed(
            title="????????????",
            description=description,
            color = discord.Colour.nitro_pink(),
        )

        if description == "???????????? - ":return False
        
        else:return embed

    @discord.application_command(description="??????or????????????")
    async def play(self, ctx:discord.ApplicationContext ,query:discord.Option(str,description="??????????????????(????????????????????????????????????)")):
        self.setup_status(ctx.author.guild.id)
        vc_status = self.get_status(ctx.author.guild.id)
        
        if ctx.author.voice is None:
            
            await ctx.respond("???????????????????????????!")
            
        elif vc_status["is_paused"]:
             vc_status["vc"].resume()

        else:
            voice_channel = ctx.author.voice.channel
            song = self.search_yt(query)
            if type(song) == type(True):
                await ctx.respond("???????????????????????? ????????????????????????")
            else:
                await ctx.respond("??????????????????????????????!")
                vc_status["music_queue"].append([song, voice_channel])

                msg = self.music_embed(song['url'],ctx.author.guild.id,ctx)

                embed = msg["embed"]
                view = msg["view"]
                
                if  vc_status["is_playing"] == False:
                    await self.play_music(ctx,ctx.author.guild.id)
                    await ctx.send(embed=embed, view=view)

    @discord.application_command(description="????????????")
    async def pause(self, ctx:discord.ApplicationContext,):
        self.setup_status(ctx.author.guild.id)
        vc_status = self.get_status(ctx.author.guild.id)
        if vc_status["is_playing"]:
            vc_status["is_playing"] = False
            vc_status["is_paused"] = True
            vc_status["vc"].pause()
            await ctx.respond(f"`{ctx.author}` ???????????????!")

        elif vc_status["is_paused"]:
            vc_status["is_paused"] = False
            vc_status["is_playing"] = True
            vc_status["vc"].resume()
            await ctx.respond(f"`{ctx.author}` ???????????????!")

        elif vc_status["music_queue"] == []:await ctx.respond("????????????????????????")

    @discord.application_command(description="??????????????????")
    async def resume(self, ctx:discord.ApplicationContext,):
        self.setup_status(ctx.author.guild.id)
        vc_status = self.get_status(ctx.author.guild.id)
        if  vc_status["is_paused"]:
            vc_status["is_paused"] = False
            vc_status["is_playing"] = True
            vc_status["vc"].pause()
            await ctx.respond(f"`{ctx.author}` ???????????????!")

        elif vc_status["is_playing"]: await ctx.respond(f"?????????????????????!")

        elif vc_status["music_queue"] == []:await ctx.respond("????????????????????????")

    @discord.application_command(description="??????")
    async def skip(self, ctx:discord.ApplicationContext):
        self.setup_status(ctx.author.guild.id)
        vc_status = self.get_status(ctx.author.guild.id)

        if await self.play_music(ctx,ctx.author.guild.id,check=True) != False:

            if vc_status["vc"] != None and vc_status["vc"]:
                vc_status["vc"].stop()
            
                await ctx.respond(f"`{ctx.author}` ???????????????!")
                await ctx.send("?????????????????????...")

                msg = self.music_embed(vc_status["music_queue"][0][0]["url"],ctx.author.guild.id,ctx)

                embed = msg["embed"]
                view = msg["view"]

                await ctx.send(embed=embed, view=view)

        else: await ctx.respond("????????????????????????")

    @discord.application_command(description="??????????????????")
    async def queue(self, ctx:discord.ApplicationContext):
        embed = self.queue_embed(ctx.author.guild.id)

        if isinstance(embed,bool):
            await ctx.respond("???????????????????????????")
        else:
            await ctx.respond(embed=embed)

    @discord.application_command(description="??????????????????")
    async def clearqueue(self, ctx:discord.ApplicationContext):
        self.setup_status(ctx.author.guild.id)
        vc_status = self.get_status(ctx.author.guild.id)
        if vc_status["vc"] != None and vc_status["is_playing"]:
            vc_status["vc"].stop()

        if vc_status["music_queue"] == []:await ctx.respond("???????????????????????????")

        else:
            vc_status["music_queue"] = []
            await ctx.respond(f"{ctx.author} ???????????????????????????????????????")

    @discord.application_command(description="????????????")
    async def dc(self, ctx:discord.ApplicationContext):
        self.setup_status(ctx.author.guild.id)
        vc_status = self.get_status(ctx.author.guild.id)

        vc_status["is_playing"] = False
        vc_status["is_paused"] = False

        await vc_status["vc"].disconnect()
        await ctx.respond("???????????????????????????~")

    @discord.application_command(description="?????????????????????????????????")
    async def np(self,ctx:discord.ApplicationContext):
        self.setup_status(ctx.author.guild.id)
        vc_status = self.get_status(ctx.author.guild.id)

        if vc_status["music_queue"] != []:

            url = vc_status["music_queue"][0][0]["url"]

            msg = self.music_embed(url,ctx.author.guild.id,ctx)

            embed = msg["embed"]
            view = msg["view"]

            await ctx.respond(embed=embed, view=view)

        else: await ctx.respond("???????????????????????????")

def setup(bot):
    bot.add_cog(Music(bot))
