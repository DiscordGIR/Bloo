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

        if (word.word.lower() in input_lowercase) or \
            (not word.false_positive and word.word.lower() in folded_without_spaces) or \
                (not word.false_positive and word.word.lower() in folded_without_spaces_and_punctuation):

            # remove all whitespace, punctuation in message and run filter again
            if word.false_positive and word.word.lower() not in input_lowercase.split():
                continue

            if word.notify:
                return [word]

            words_found.append(word)
    return words_found

    # dev_role = message.guild.get_role(self.settings.guild().role_dev)
    # if not (word.piracy and message.channel.id == self.settings.guild().channel_development and dev_role in message.author.roles):
    # ignore if this is a piracy word and the channel is #development and the user has dev role
    # word_found = True
    # await self.delete(message)
    # if not reported:
    #     await self.do_filter_notify(message.author, message.channel, word.word)
    #     await self.ratelimit(message)
    #     reported = True
    # if word.notify:
    #     await self.report.report(message, message.author, word.word)
    #     return True
