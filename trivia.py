import asyncio
import random
import time

import discord
from discord.ext import commands


def sucks_to_be_you_message():
    opts = ["That was a toughie.", "You'll do better next time.", "I believe in you.",
            "Shucks.", "Not quite.", "Close, but no cigar.",
            "You're doing great, but"]
    return random.choice(opts)


def youre_smart_message():
    opts = ["Correct!", "Awesome!", "Right on."]
    return random.choice(opts)


def get_questions():
    qs = [["Is Orion a star?", "no", "n"],
          ["Are clouds evil?", "yes", "y", "definitely"],
          ["Who made this bot?", "locke"]]
    return qs


async def privileged_person(ctx):
    staff = discord.utils.get(ctx.guild.roles, name="Staff")
    host = discord.utils.get(ctx.guild.roles, name="Trivia Host")
    manager = discord.utils.get(ctx.guild.roles, name="Trivia Manager")
    for roll in (staff, host, manager):
        if roll is None:
            await ctx.send("I didn't find normal roll names, so you'll have problems running stuff")
            return False
    return ctx.author.top_role >= staff or host in ctx.author.roles or manager in ctx.author.roles


class Trivia:
    """For hosting Spacecord Trivia sessions"""
    def __init__(self, bot):
        self.bot = bot
        self.questions = get_questions()
        self.score = 0
        self.question_num = 0
        self.runTask = None
        self.channel = None
        self.msgtask = None

        self.max_time = 7  # seconds

    def __unload(self):
        self.kill_run_task()

    @commands.check(privileged_person)
    @commands.command(aliases=['purge_channel'])
    async def clear_channel(self, ctx):
        """Clear all messages in a channel that aren't pinned
        Max 500 messages."""
        def isnt_pinned(m):
            return not m.pinned
        deleted = await ctx.channel.purge(limit=500, check=isnt_pinned)
        await ctx.send(f"Cleared {len(deleted)} messages", delete_after=3)

    @commands.check(privileged_person)
    @commands.command()
    async def start(self, ctx):
        """Begin or resume a trivia session"""
        self.channel = ctx.channel
        if self.question_num is 0:
            await ctx.send("Starting trivia!")
        else:
            await ctx.send("Resuming trivia!")
        self.start_run_task()

    @commands.check(privileged_person)
    @commands.command()
    async def pause(self, ctx):
        """Temporarily suspend a trivia session"""
        self.kill_run_task()
        await ctx.send("Trivia paused.")

    @commands.check(privileged_person)
    @commands.command()
    async def stop(self, ctx):
        """Stop all questioning and forget where we were"""
        await ctx.send("Trivia halted.  Use the `start` command to start anew.")
        self.reset()

    async def run_task(self):
        """Main task of running trivia.  This can be cancelled."""
        while self.question_num < len(self.questions):
            await self.channel.trigger_typing()
            await asyncio.sleep(1.5)

            q = self.questions[self.question_num]
            await self.channel.send("Question {}: {}".format(self.question_num+1, q[0]))
            start = time.time()

            self.msgtask = self.bot.loop.create_task(self.listen_for_message_task())
            while not self.msgtask.done():
                if time.time() > start + self.max_time:
                    print("Time's up!")
                    self.msgtask.cancel()
                    sucks = sucks_to_be_you_message()
                    await self.channel.send(sucks + " The answer was {}".format(q[1]))
                await asyncio.sleep(.07)

            self.question_num += 1
        if self.score == 0:
            await self.channel.send("You got 0 questions right.  Better luck next time!")
        elif self.score == 1:
            await self.channel.send("You got 1 question right!")
        else:
            await self.channel.send(f"Nice work!  You got {self.score} questions right!")
        self.reset()

    async def listen_for_message_task(self):
        """Cancellable task that listens for the victim's response in a channel.
        Returns when they have the right answer"""
        def check(m):
            return m.channel == self.channel
        while True:
            msg = await self.bot.wait_for("message", check=check)

            if self.correct(msg.content):
                await self.channel.send(youre_smart_message())
                self.score += 1
                return True
            if msg.content.lower() == "idk":
                await self.channel.send("Then guess!")

    def correct(self, ans):
        """Return whether an answer is correct"""
        q = self.questions[self.question_num]
        return any(ans.lower() == response for response in q[1:])

    def reset(self):
        """Reset everything to beginning state"""
        self.question_num = 0
        self.score = 0
        self.kill_run_task()

    def kill_run_task(self):
        if self.runTask is None:
            return
        else:
            self.runTask.cancel()
            self.runTask = None
        if self.msgtask is not None and not self.msgtask.done():
            self.msgtask.cancel()

    def start_run_task(self):
        if self.runTask is not None:
            self.kill_run_task()
        self.runTask = self.bot.loop.create_task(self.run_task())


def setup(bot):
    bot.add_cog(Trivia(bot))
