import os
from dotenv.main import load_dotenv
from utils.logger import logger

class Config:
    def __init__(self):
        load_dotenv()

        self.guild_id = int(os.environ.get("MAIN_GUILD_ID"))
        self.owner_id = int(os.environ.get("OWNER_ID"))

        if self.guild_id is None:
            self.setup_error("MAIN_GUILD_ID")

        if self.owner_id is None:
            self.setup_error("OWNER_ID")
            
        self.aaron_id = os.environ.get("AARON_ID")
        if self.aaron_id is None:
            self.setup_error("AARON_ID")
        self.aaron_id = int(self.aaron_id)
        
        self.aaron_role = os.environ.get("AARON_ROLE")
        if self.aaron_role is not None:
            self.aaron_role = int(self.aaron_role)
        else:
            self.setup_warning("AARON_ROLE")

        self.dev = os.environ.get("DEV") is not None

        logger.info(f"Bloo will be running in: {self.guild_id} in \033[1m{'DEVELOPMENT' if self.dev else 'PRODUCTION'}\033[0m mode")
        logger.info(f"Bot owned by: {self.owner_id}")

    def setup_warning(self, k: str):
        logger.warn('.env file does not have key {}. Some features may not function as intended.'.format(k))
        
    def setup_error(self, k: str):
        logger.error('.env file is not correctly set up! Missing key {}'.format(k))
        exit(1)

cfg = Config()
