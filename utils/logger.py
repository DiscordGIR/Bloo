import argparse
import logging
import sys


class Formatter(logging.Formatter):
    def __init__(self):
        self.style_list = {
            'bright': '\x1b[1m',
            'dim': '\x1b[2m',
            'underscore': '\x1b[4m',
            'blink': '\x1b[5m',
            'reverse': '\x1b[7m',
            'hidden': '\x1b[8m',
            'black': '\x1b[30m',
            'red': '\x1b[31m',
            'green': '\x1b[32m',
            'yellow': '\x1b[33m',
            'blue': '\x1b[34m',
            'magenta': '\x1b[35m',
            'reset': '\x1b[0m',
            'cyan': '\x1b[36m',
            'white': '\x1b[37m',
            'bgBlack': '\x1b[40m',
            'bgRed': '\x1b[41m',
            'bgGreen': '\x1b[42m',
            'bgYellow': '\x1b[43m',
            'bgBlue': '\x1b[44m',
            'bgMagenta': '\x1b[45m',
            'bgCyan': '\x1b[46m',
            'bgWhite': '\x1b[47m'
        }
        self.err_fmt = f"{self.style_list.get('dim')}[{self.style_list.get('reset')}{self.style_list.get('red')}!{self.style_list.get('reset')}{self.style_list.get('dim')}]{self.style_list.get('reset')} %(message)s"
        self.dbg_fmt = f"{self.style_list.get('dim')}[{self.style_list.get('reset')}{self.style_list.get('yellow')}#{self.style_list.get('reset')}{self.style_list.get('dim')}]{self.style_list.get('reset')} (m:'%(module)s', l:%(lineno)s) %(message)s"
        self.warn_fmt = f"{self.style_list.get('dim')}[{self.style_list.get('reset')}{self.style_list.get('yellow')}?{self.style_list.get('reset')}{self.style_list.get('dim')}]{self.style_list.get('reset')} (m:'%(module)s', l:%(lineno)s) %(message)s"
        self.info_fmt = f"{self.style_list.get('dim')}[{self.style_list.get('reset')}{self.style_list.get('green')}*{self.style_list.get('reset')}{self.style_list.get('dim')}]{self.style_list.get('reset')} %(message)s"

        super().__init__(fmt=self.info_fmt, datefmt=None, style='%')

    def format(self, record):
        format_orig = self._style._fmt

        if record.levelno == logging.DEBUG:
            self._style._fmt = self.dbg_fmt
            
        elif record.levelno == logging.INFO:
            self._style._fmt = self.info_fmt

        elif record.levelno == logging.WARNING:
            self._style._fmt = self.warn_fmt
            
        elif record.levelno == logging.ERROR:
            self._style._fmt = self.err_fmt

        result = logging.Formatter.format(self, record)

        self._style._fmt = format_orig

        return result

class Logger:
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--disable-discord-logs', help='Disables Discord logging.', action='store_true')
        parser.add_argument('--disable-scheduler-logs', help='Disables scheduler logs.', action='store_true')

        args = parser.parse_args()

        self.HNDLR = logging.StreamHandler(sys.stdout)
        self.HNDLR.formatter = Formatter()
        if not args.disable_discord_logs:
            discord_logger = logging.getLogger('discord')
            discord_logger.setLevel(logging.INFO)
            discord_logger.addHandler(self.HNDLR)
        if not args.disable_scheduler_logs:
            ap_logger = logging.getLogger('apscheduler')
            ap_logger.setLevel(logging.INFO)
            ap_logger.addHandler(self.HNDLR)
        self.logger = logging.Logger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.HNDLR)
        
logger = Logger().logger
