import asyncio
import json
import pprint
import random
import time
from shutil import copy2

import discord
from discord.ext import commands

import parser


def sucks_to_be_you_message():
    opts = ["That was a toughie.", "You'll do better next time.", "I believe in you.",
            "Shucks.", "Not quite.", "Close, but no cigar.",
            "You're doing great, but"]
    return random.choice(opts)


def youre_smart_message():
    opts = ["Correct!", "Awesome!", "Right on.", "Nice!", "Good work."]
    return random.choice(opts)


def get_questions():
    try:
        with open('questions.json') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print("Error loading questions file!")
        return [["There was an error loading the questions file. This is a programming problem or a you problem.  In "
                 "the latter case, you can solve it by rewriting the file with the `save_questions` command",
                 "there actually wasn't one lol"]]


async def privileged_person(ctx):
    staff = discord.utils.get(ctx.guild.roles, name="Staff")
    host = discord.utils.get(ctx.guild.roles, name="Trivia Host")
    manager = discord.utils.get(ctx.guild.roles, name="Trivia Manager")
    for roll in (staff, host, manager):
        if roll is None:
            await ctx.send("I didn't find the rolls (`Staff`, `Trivia Host` and `Trivia Manager`) that are allowed "
                           "to run commands, so you'll have problems running stuff")
            return False
    return ctx.author.top_role >= staff or host in ctx.author.roles or manager in ctx.author.roles


class Trivia(commands.Cog):
    """For hosting Spacecord Trivia sessions"""
    def __init__(self, bot):
        self.bot = bot
        self.questions = get_questions()
        self.score = 0
        self.question_num = 0
        self.runTask = None
        self.channel = None
        self.msgtask = None

        self.max_time = 20  # seconds

    def __unload(self):
        self.kill_run_task()

    @commands.check(privileged_person)
    @commands.command(aliases=['purge_channel', 'clear'])
    async def clear_channel(self, ctx):
        """Clear all messages in a channel that aren't pinned
        Max 500 messages."""
        def isnt_pinned(m):
            return not m.pinned
        deleted = await ctx.channel.purge(limit=500, check=isnt_pinned)
        await ctx.send(f"Cleared {len(deleted)} messages", delete_after=3)

    @commands.check(privileged_person)
    @commands.command(aliases=['resume'])
    async def start(self, ctx):
        """Begin or resume a trivia session"""
        self.channel = ctx.channel
        if self.question_num is 0:
            await ctx.send("Starting trivia!")
        else:
            await ctx.send("Resuming trivia!")
        self.start_run_task()

    @commands.check(privileged_person)
    @commands.command(aliases=['grant_point', 'grant', 'addpoint', 'add', 'yes'])
    async def add_point(self, ctx):
        self.score += 1
        await ctx.send("Added a point.")

    @commands.check(privileged_person)
    @commands.command(aliases=['subtract_point', 'removepoint', 'subtract', 'remove', 'nope', 'no'])
    async def remove_point(self, ctx):
        self.score -= 1
        await ctx.send("Removed a point.")

    @commands.check(privileged_person)
    @commands.command()
    async def pause(self, ctx):
        """Temporarily suspend a trivia session"""
        self.kill_run_task()
        await ctx.send("Trivia paused.")

    @commands.check(privileged_person)
    @commands.command(hidden=True)
    async def stop(self, ctx):
        """Stop all questioning and forget where we were"""
        await ctx.send("Trivia halted.  Use the `start` command to start anew.")
        self.reset()

    @commands.check(privileged_person)
    @commands.command()
    async def save_questions_old(self, ctx):
        """
        Input questions from old spacedoc format into a format I remember
        Don't use double quotes, please.  Multiple questions at a time is fine.
        """
        def check(msg):
            return msg.author == ctx.message.author

        await ctx.send("Type one or more questions per message, in spacedoc format. "
                       "When you're done, say `done` (or `nvm` to abort)")
        out = []
        done = False
        while not done:
            msg = await self.bot.wait_for("message", check=check)
            for content in msg.content.split('\n'):
                if content.lower() == 'exit' or content.lower() == 'done':
                    done = True
                    break
                if content.lower() == 'nvm':
                    await ctx.send("Aborting `save_questions`")
                    return
                par = content.split('`')
                if len(par) < 2:
                    await ctx.send("Oops, that didn't look like a legit question to me.  "
                                   "The format I expect  is Question\\`answer\\`alternate answer`another answer..."
                                   "Make sure you didn't cut off a question halfway through because of the character "
                                   "limit :eyes:")
                elif len(content) > 1:  # silently skip over inputted empty newlines
                    await ctx.send(f"Added question `{par[0]}` with  the following answers:")
                    await ctx.send("\n".join(ans for ans in par[1:]))
                    out.append(par)
        await ctx.send("Processed {} questions :thumbsup:".format(len(out)))
        # copy file as backup
        try:
            copy2("questions.json", "questions.json.old")
        except FileNotFoundError:
            print("No previous questions file so skipping attempt to back it up")
        # write file
        with open('questions.json', 'w') as f:
            json.dump(out, fp=f)
        await ctx.send("Written!")
        self.questions = get_questions()

    async def run_task(self):
        """Main task of running trivia.  This can be cancelled."""
        pprint.pprint(self.questions)
        while self.question_num < len(self.questions):
            await self.channel.trigger_typing()
            await asyncio.sleep(2)

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
                    await asyncio.sleep(3)  # give extra pause for participant to process the correct answer.
                await asyncio.sleep(.07)

            self.question_num += 1
        if self.score is 0:
            await self.channel.send("You got 0 questions right.  Better luck next time!")
        elif self.score is 1:
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
            if msg.content.lower() == "idk" or msg.content == '¯\\_(ツ)_/¯':
                await self.channel.send("Then guess!")

    def correct(self, ans):
        """Return whether an answer is correct"""
        q = self.questions[self.question_num]
        return any(ans.lower() == response.lower() for response in q[1:])

    def reset(self):
        """Reset everything to beginning state"""
        self.question_num = 0
        self.score = 0
        self.kill_run_task()

    def kill_run_task(self):
        if self.runTask is not None:
            self.runTask.cancel()
            self.runTask = None
        if self.msgtask is not None and not self.msgtask.done():
            self.msgtask.cancel()

    def start_run_task(self):
        if self.runTask is not None:
            self.kill_run_task()
        self.runTask = self.bot.loop.create_task(self.run_task())

    @commands.is_owner()
    @commands.command(hidden=True)
    async def say(self, ctx, chan: int, *, content):
        await self.bot.get_channel(chan).send(content)

    @commands.check(privileged_person)
    @commands.command(hidden=True)
    async def save_questions(self, ctx):
        """
        Input questions from new spacedoc format into a format I remember
        """

        def check(msg):
            return msg.author == ctx.message.author

        await ctx.send("Paste an even number of lines at a time, in spacedoc format. "
                       "When you're done, say `done` (or `nvm` to abort)")
        out = []
        done = False
        while not done:
            msg = await self.bot.wait_for("message", check=check)
            if msg.content.lower() == 'exit' or msg.content.lower() == 'done':
                done = True
                break
            if any(msg.content.lower() == word for word in ('nvm', 'abort', 'stop')):
                await ctx.send("Aborting `save_questions`")
                return
            chunky = await parser.parse_block(ctx, msg.content)
            if chunky:  # sometimes the parse_block won't return anything if user do stuff well
                out.extend(chunky)
        await ctx.send("Processed {} questions :thumbsup:".format(len(out)))
        # copy file as backup
        try:
            copy2("questions.json", "questions.json.old")
        except FileNotFoundError:
            print("No previous questions file so skipping attempt to back it up")
        # write file
        with open('questions.json', 'w') as f:
            json.dump(out, fp=f)
        await ctx.send("Written!")
        self.questions = get_questions()


def setup(bot):
    bot.add_cog(Trivia(bot))
