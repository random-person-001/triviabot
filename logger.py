import discord
from discord.ext import commands


class Logger(commands.Cog):
    """For logging Trivia sessions"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.channel.name != 'astro-trivia':
            return
        log = discord.utils.get(msg.guild.channels, name='trivia-logs')
        await log.send(msg.author.name + ':    ' + discord.utils.escape_mentions(msg.content))
        if msg.author.bot and all(x in msg.content for x in ('Cleared', 'messages')):
            await log.send('=' * 25 + '\n' * 3 + '{:-^38}'.format('Channel cleared.') + '\n' * 3 + '=' * 25)


def setup(bot):
    bot.add_cog(Logger(bot))
