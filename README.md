# Triviabot
A triviabot for spacecord.  Because we needed a third.

## Commands
### Basic
`start` begins or resumes the trivia

`pause` pauses trivia

`stop`    halts trivia

### Once-in-a-while

`clear_channel` removes all nonpinned messages in the channel

`addpoint` adds a point to the current score

`removepoint` removes a point from the current score

### Other

`save_questions` create a trivia list from inputs in spacedoc format

`help`    shows help

## Trivia Sessions
Currently the timeout is 20 seconds per question.

The bot only counts as correct answers that match exactly one of the given answers, discounting capitalization.  

## Hosting
The bot should give relatively useful errors when you try to run it about what it needs, but if you want to be proactive, you'll want a file called `api_keys.json` with a discord token in it, like
```json
{
  "discord": "your-key-here"
}
```
It'll save questions that you input with `save_questions` in the file `questions.json` which is a list of questions, where each question is represented as a list with all but the first element being possible answers.  But you don't really need to know that to run it.