import logging
import coloredlogs

class Logger:
    def __init__(self):
        logger = logging.getLogger('discord')
        self.logger = logging.getLogger('cfg')
        coloredlogs.install(level='INFO', logger=logger)
        coloredlogs.install(level='INFO', logger=self.logger)

logger = Logger().logger
