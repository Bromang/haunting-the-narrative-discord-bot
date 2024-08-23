import discord
from nrclex import NRCLex
from os import environ
import nltk
from collections import defaultdict
import math
from nltk.corpus import wordnet
from random import randint, choice
nltk.download('punkt')
nltk.download('wordnet')

# Your bot token
TOKEN = environ['botToken']

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Synonym dictionary for emotions
emotion_synonyms = {
    'anticipation': [
        'expectation', 'eagerness', 'anticipatory', 'hopefulness', 'excitement'
    ],
    'happy': [
        'joyful', 'content', 'cheerful', 'pleased', 'delighted', 'ecstatic', 'elated'
    ],
    'positive': [
        'optimistic', 'upbeat', 'encouraging', 'hopeful', 'constructive', 'favorable'
    ],
    'surprise': [
        'astonishment', 'amazement', 'shock', 'wonder', 'stunned', 'bewildered'
    ],
    'trust': [
        'confidence', 'faith', 'reliance', 'dependence', 'belief', 'assurance'
    ],
    'anger': [
        'rage', 'fury', 'irritation', 'outrage', 'resentment', 'annoyance'
    ],
    'disgust': [
        'revulsion', 'distaste', 'repulsion', 'aversion', 'displeasure', 'nausea'
    ],
    'fear': [
        'terror', 'anxiety', 'apprehension', 'dread', 'fright', 'worry'
    ],
    'negative': [
        'pessimistic', 'unfavorable', 'dismal', 'bleak', 'downbeat', 'gloomy'
    ],
    'sadness': [
        'sorrow', 'grief', 'melancholy', 'despair', 'dejection', 'dismay'
    ]
}

def get_related_words(word, start_rank=1, end_rank=10):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name())
    sorted_synonyms = sorted(synonyms)
    if len(sorted_synonyms) >= start_rank:
        end_rank = min(end_rank, len(sorted_synonyms))
        random_index = randint(start_rank-1, end_rank-1)
        return sorted_synonyms[random_index]
    return word  # Return the original word if not enough synonyms found

def get_synonym_based_on_emotion(emotion):
    synonyms = emotion_synonyms.get(emotion, [])
    if synonyms:
        return choice(synonyms)  # Choose a random synonym
    return emotion  # Return the base emotion if no synonyms are found

async def update_channel_topic(channel, mood):
    # Capitalize the mood
    mood = mood.capitalize()
    
    # Fetch current topic
    current_topic = channel.topic or ""
    
    # Check if "Prevailing mood:" exists in the topic
    if "Prevailing mood:" in current_topic:
        # Extract the current mood
        start_index = current_topic.find("Prevailing mood:") + len("Prevailing mood:")
        end_index = current_topic.find("\n", start_index)
        if end_index == -1:
            end_index = len(current_topic)
        current_mood = current_topic[start_index:end_index].strip()
        
        # If the mood is the same, do nothing
        if current_mood.lower() == mood.lower():
            return
        
        # Update the mood value
        new_topic = current_topic[:start_index] + f" {mood}" + current_topic[end_index:]
    else:
        # Append new mood information
        new_topic = f"{current_topic}\nPrevailing mood: {mood}" if current_topic else f"Prevailing mood: {mood}"
    
    # Update the channel's topic
    await channel.edit(topic=new_topic)

async def fetch_recent_messages(channel):
    messages = []
    async for msg in channel.history(limit=18):
        messages.append(msg)
    messages.reverse()
    return messages

def count_author_messages(messages):
    author_message_count = defaultdict(int)
    for msg in messages:
        author_message_count[msg.author.id] += 1
    return author_message_count

def calculate_weight(message_count):
    if message_count <= 1:
        return 1  # Assign a weight of 1 if the author has only one message
    return 1.2 / math.sqrt(message_count)

def analyze_emotions(messages, author_message_count):
    emotions_counter = defaultdict(float)
    for msg in messages:
        # Analyze each message for emotions
        text = NRCLex(msg.content)
        emotions = text.raw_emotion_scores
        
        # Calculate weight based on the number of messages from the author
        weight = calculate_weight(author_message_count[msg.author.id])
        
        # Update the emotion counts with weighted scores
        for emotion, score in emotions.items():
            # Apply a different weight for 'negative' and 'positive'
            if emotion in {'negative', 'positive'}:
                score *= 0.1  # Reduce weight for 'negative' and 'positive'
            
            # Get a random synonym for the emotion
            synonym = get_synonym_based_on_emotion(emotion)
            related_word = get_related_words(synonym)
            
            # Update the emotion counts with weighted scores
            emotions_counter[emotion] += score * weight

    return emotions_counter

def get_prevailing_mood(emotions_counter):
    if emotions_counter:
        return max(emotions_counter, key=emotions_counter.get)
    return None

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

@client.event
async def on_message(message):
    # Check if the message is from a user and not from a bot
    if not message.author.bot:
        print(message.content)  # Print the message content to debug

        # Fetch the last 17 messages along with the current message
        messages = await fetch_recent_messages(message.channel)
        
        # Count the number of messages per author
        author_message_count = count_author_messages(messages)
        
        # Analyze emotions from messages and update the emotion counts with weights
        emotions_counter = analyze_emotions(messages, author_message_count)
        
        # Determine the most prevailing mood
        prevailing_mood = get_prevailing_mood(emotions_counter)
        
        if prevailing_mood:
            # Update the channel topic with the prevailing mood
            related_mood = get_synonym_based_on_emotion(prevailing_mood)
            await update_channel_topic(message.channel, related_mood)
            
            # Print debugging information
            #print(f"Emotions in channel {message.channel.name}: {emotions_counter}")
            print(f"Most prevailing mood: {prevailing_mood}")
            print(f"Related mood: {related_mood}")
        else:
            # If no dominant mood is detected
            pass

# Start the bot
client.run(TOKEN)
