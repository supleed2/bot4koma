from datetime import datetime
import discord, json, os, re
from textwrap import indent

bot = discord.Client(intents = discord.Intents.default())
listenChannelIDs = [
    250056894335549440, # ICAS - announcements
    960995261570756690, # ICAS - 4koma-archive
]
outputChannelID = 960995261570756690 # ICAS - 4koma-archive
fourKomaRegex = re.compile(r"^(?:[\s\S]*\[4KOMA\] (\d{4}\-(?:0[1-9]|1[012])\-(?:0[1-9]|[12][0-9]|3[01])))\s*([\s\S]*)$")
contentsRegex = re.compile(r"^[\S\s]*[cC]hapter[^\d]*([\w.]+)[\S\s]*$")
contentsMsgIDs = None

with open("conf.json", "r") as conf:
    contentsMsgIDs = json.load(conf)["contentsMsgIDs"]

async def generate_contents():
    global contentsMsgIDs
    if contentsMsgIDs is not None:
        for contentsMsgID in contentsMsgIDs:
            try:
                oldmsg = await outputChannel.fetch_message(contentsMsgID)
            except discord.errors.NotFound:
                print(f"[ ERR ] {datetime.now().ctime()} Old Contents message ({contentsMsgID}) not found, skipping")
            else:
                await oldmsg.delete()
                print(f"[INFO:] {datetime.now().ctime()} Deleted old Contents message ({contentsMsgID})")
    bot_messages = [(contentsRegex.match(message.content).group(1), message.jump_url)
        async for message in outputChannel.history(limit=1000)
        if message.author == bot.user][::-1]
    split_bot_messages = [bot_messages[i:i+10] for i in range(0, len(bot_messages), 10)]
    grouped_bot_messages = [split_bot_messages[i:i+6] for i in range(0, len(split_bot_messages), 6)]
    embed = discord.Embed(title="4Koma Archive",
        description="Hey guys! We have compiled all the past 4Koma here, come check them out and walk down memory lane <:2bhappy:370922383256715265>")
    for msgs in grouped_bot_messages[0]:
        embed.add_field(
            name=f"Chapters {msgs[0][0]} - {msgs[-1][0]}",
            value=", ".join([f"[{msg[0]}]({msg[1]})" for msg in msgs]),
            inline=False)
    newContentsMsgs = [await outputChannel.send(embed=embed)]
    for part, extras in enumerate(grouped_bot_messages[1:]):
        embed = discord.Embed(title=f"4Koma Archive (Part {part + 2})",
            description="Another message for the remaining links *smh Discord with their 6000 character per message limit* <:aquaDismay:1007404394368745634>")
        for msgs in extras:
            embed.add_field(
                name=f"Chapters {msgs[0][0]} - {msgs[-1][0]}",
                value=", ".join([f"[{msg[0]}]({msg[1]})" for msg in msgs]),
                inline=False)
        newContentsMsgs.append(await outputChannel.send(embed=embed))
    contentsMsgIDs = [msg.id for msg in newContentsMsgs]
    print(f"[INFO:] {datetime.now().ctime()} Regenerated Contents with {len(bot_messages)} entries, IDs: {contentsMsgIDs}")
    with open("conf.json", "w") as conf:
        json.dump({"contentsMsgIDs":contentsMsgIDs}, conf)

@bot.event
async def on_ready():
    global outputChannel, listenChannels, committeeRole
    print(f"[INFO:] {datetime.now().ctime()} Logged in as: {bot.user.name}#{bot.user.discriminator}")
    listenChannels = [bot.get_channel(channelID) for channelID in listenChannelIDs]
    if None in listenChannels:
        print(f"[ ERR ] {datetime.now().ctime()} Failed to get input channel(s), ID(s): {[listenChannelIDs[index] for index, channel in enumerate(listenChannels) if channel is None]}")
    print(f"[INFO:] {datetime.now().ctime()} Listening to channel(s): {[channel.name for channel in listenChannels if channel is not None]}")
    outputChannel = bot.get_channel(outputChannelID)
    if outputChannel is not None:
        print(f"[INFO:] {datetime.now().ctime()} Output channel connected: {outputChannel.name}")
        await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="to keep track of 4Koma"))
    else:
        print(f"[ ERR ] {datetime.now().ctime()} Failed to get output channel, ID: {outputChannelID}")
        await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Game(name="Failed to connect output channel"))
    print(f"[INFO:] {datetime.now().ctime()} Contents Message IDs from conf.json: {contentsMsgIDs}")
    committeeRole = bot.get_guild(249891637008793600).get_role(250056298710827008)
    if committeeRole is not None:
        print(f"[INFO:] {datetime.now().ctime()} Committee Role bound")
    else:
        print(f"[ ERR ] {datetime.now().ctime()} Failed to bind Committee Role")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    elif message.channel.id in listenChannelIDs:
        if committeeRole in message.author.roles:
            if message.content.startswith("!contents"):
                print(f"[INFO:] {datetime.now().ctime()} Force regenerate contents messages")
                await message.delete()
                await generate_contents()
                return
        fourKomaPost = fourKomaRegex.match(str(message.content))
        if fourKomaPost is not None:
            fourKomaHeader = "4Koma from " + datetime.strptime(fourKomaPost.group(1), r"%Y-%m-%d").strftime(r"%A, %d %B %Y") + "\n"
            await outputChannel.send(fourKomaHeader + fourKomaPost.group(2), files=[await atch.to_file() for atch in message.attachments])
            print(f"[4KOMA] {datetime.now().ctime()}:")
            print(indent(fourKomaPost.group(1) + ":", "│ "))
            print(indent(fourKomaPost.group(2), "│ "))
            print("└────────────────")
            await generate_contents()

bot.run(os.environ["DISCORD_TOKEN"])
