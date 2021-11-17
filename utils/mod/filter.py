import discord
import string
from typing import List
from fold_to_ascii import fold
from data.model.filterword import FilterWord
from data.services.guild_service import guild_service
from utils.permissions.permissions import permissions

def find_triggered_filters(input, member: discord.Member) -> List[FilterWord]:
    """
    BAD WORD FILTER
    """
    symbols = (u"абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
               u"abBrdeex3nnKnmHonpcTyoxu4wwbbbeoRABBrDEEX3NNKNMHONPCTyOXU4WWbbbEOR")

    tr = {ord(a): ord(b) for a, b in zip(*symbols)}

    input_lowercase = fold(input.translate(tr).lower()).lower()
    folded_without_spaces = "".join(input_lowercase.split())
    folded_without_spaces_and_punctuation = folded_without_spaces.translate(
        str.maketrans('', '', string.punctuation))

    db_guild = guild_service.get_guild()

    if not input_lowercase:
        return []
    # reported = False

    words_found = []
    for word in db_guild.filter_words:
        if permissions.has(member.guild, member, word.bypass):
            continue

        filter_word_without_spaces = "".join(word.word.lower().split())
        if (word.word.lower() in input_lowercase) or \
            (not word.false_positive and word.word.lower() in folded_without_spaces) or \
                (not word.false_positive and word.word.lower() in folded_without_spaces_and_punctuation or \
                    (not word.false_positive and filter_word_without_spaces in folded_without_spaces_and_punctuation)):

            # remove all whitespace, punctuation in message and run filter again
            if word.false_positive and word.word.lower() not in input_lowercase.split():
                continue

            if word.notify:
                return [word]

            words_found.append(word)
    return words_found
