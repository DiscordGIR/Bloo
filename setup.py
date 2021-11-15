import asyncio
import os

import mongoengine
from dotenv import find_dotenv, load_dotenv

from data.model.guild import Guild

load_dotenv(find_dotenv())

async def setup():
    print("STARTING SETUP...")
    guild = Guild()
    
    # you should have this setup in the .env file beforehand
    guild._id          = int(os.environ.get("MAIN_GUILD_ID"))
    
    guild.case_id      = 1
    
    guild.role_administrator = 123  # put in the role IDs for your server here
    guild.role_birthday      = 123  # put in the role IDs for your server here
    guild.role_dev           = 123  # put in the role IDs for your server here
    guild.role_genius        = 123  # put in the role IDs for your server here
    guild.role_member        = 123  # put in the role IDs for your server here
    guild.role_memberone     = 123  # put in the role IDs for your server here
    guild.role_memberedition = 123  # put in the role IDs for your server here
    guild.role_memberplus    = 123  # put in the role IDs for your server here
    guild.role_memberpro     = 123  # put in the role IDs for your server here
    guild.role_moderator     = 123  # put in the role IDs for your server here
    guild.role_mute          = 123  # put in the role IDs for your server here
    guild.role_sub_mod       = 123  # put in the role IDs for your server here
    guild.role_sub_news      = 123  # put in the role IDs for your server here
    
    guild.channel_applenews      = 123  # put in the channel IDs for your server here
    guild.channel_booster_emoji  = 123  # put in the channel IDs for your server here
    guild.channel_botspam        = 123  # put in the channel IDs for your server here
    guild.channel_common_issues  = 123  # put in the channel IDs for your server here
    guild.channel_development    = 123  # put in the channel IDs for your server here
    guild.channel_emoji_log      = 123  # put in the channel IDs for your server here
    guild.channel_general        = 123  # put in the channel IDs for your server here
    guild.channel_private        = 123  # put in the channel IDs for your server here
    guild.channel_public         = 123  # put in the channel IDs for your server here
    guild.channel_reaction_roles = 123  # put in the channel IDs for your server here
    guild.channel_reports        = 123  # put in the channel IDs for your server here
    guild.channel_subnews        = 123  # put in the channel IDs for your server here
    guild.channel_music          = 123  # put in the channel IDs for your server here
    
    guild.logging_excluded_channels = []  # put in a channel if you want (ignored in logging)
    guild.filter_excluded_channels  = []  # put in a channel if you want (ignored in filter)
    guild.filter_excluded_guilds    = []  # put guild ID to whitelist in invite filter if you want
    
    guild.nsa_guild_id = 123 # you can leave this as is if you don't want Blootooth
                       # (message mirroring system)
    guild.save()

    print("DONE")

if __name__ == "__main__":
        if os.environ.get("DB_CONNECTION_STRING") is None:
            mongoengine.register_connection(
                host=os.environ.get("DB_HOST"), port=int(os.environ.get("DB_PORT")), alias="default", name="botty")
        else:
            mongoengine.register_connection(
                host=os.environ.get("DB_CONNECTION_STRING"), alias="default", name="botty")
        res = asyncio.get_event_loop().run_until_complete( setup() )
