import logging
import coloredlogs

class Logger:
    def __init__(self):
        discord_logger = logging.getLogger('discord')
        ap_logger = logging.getLogger('apscheduler')
        self.logger = logging.getLogger('cfg')
        coloredlogs.install(level='INFO', logger=discord_logger)
        coloredlogs.install(level='INFO', logger=ap_logger)
        coloredlogs.install(level='INFO', logger=self.logger)

logger = Logger().logger
