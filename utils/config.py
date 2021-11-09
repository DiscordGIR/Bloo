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

        logger.info(f"Bloo will be running in: {self.guild_id}")
        logger.info(f"OWNED BY: {self.owner_id}")

    def setup_error(self, k: str):
        raise Exception(f".env file is not correctly set up! Missing key {k}")

cfg = Config()
