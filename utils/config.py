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
        if self.aaron_id is not None:
            self.aaron_id = int(self.aaron_id)
        
        self.aaron_role = os.environ.get("AARON_ROLE")
        if self.aaron_role is not None:
            self.aaron_role = int(self.aaron_role)

        logger.info(f"Bloo will be running in: {self.guild_id}")
        logger.info(f"OWNED BY: {self.owner_id}")

    def setup_error(self, k: str):
        raise Exception(f".env file is not correctly set up! Missing key {k}")

cfg = Config()
