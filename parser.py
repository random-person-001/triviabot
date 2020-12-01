"""
Sample Question input format:

Question: What do you get when you multiply six by nine?
Answer: 42` the answer` the answer to life, the universe, and everything
Question: Does Gary Johnson know what a "leppo" is?
Answer: No` n
"""


def parse_next(lines):
    """Parse the next two lines of `lines` for the next question and answer"""
    data = [lines[0][len('Question: '):].strip()]
    data.extend(answer.strip() for answer in lines[1][len('Answer: '):].split(','))
    lines.pop(0)
    lines.pop(0)  # we work from the front; this is easier than a pointer
    return data


def display(out):
    """Transform the data structure of questions into a legible string to read back"""
    s = ""
    for qa in out:
        s += "\n" + qa[0] + "\n   " + "\n   ".join(a for a in qa[1:])
    return s


async def parse_block(ctx, block):
    """Given a partial block of text that was pasted in from the trivia doc, parse it and read back to the user"""
    # some questions are inputted from macs and have weird apostrophes.  Kill them, and empty newlines
    # also escape underscores so when shown as a question in discord, they do not format, and normalize iOS apostrophes
    rawlines = block.replace('´', '\'').replace('\n\n', '\n').replace('_', '\\_').replace('´', '\'').split('\n')
    lines = []
    for line in rawlines:
        if not line.lower().startswith('source:'):
            lines.append(line)
    print(lines)
    # check validity of input
    try:
        if len(lines) % 2:
            raise UserWarning('Ope, I didn\'t get that. Try not to separate any questions from their answers')
        for i in range(len(lines)):
            if i % 2 and not lines[i].startswith('Answer: '):
                raise UserWarning('Answer did not start with "Answer: "\n```' + lines[i] + '```')
            if (1 + i) % 2 and not lines[i].startswith('Question: '):
                raise UserWarning('Question did not start with "Question: "\n```' + lines[i] + '```')
    except UserWarning as e:
        await ctx.send(e)
        return

    out = []
    while lines:
        out.append(parse_next(lines))

    await ctx.send(display(out))
    return out
