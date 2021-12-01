import os
import requests
import argparse
import logging
import sys
from time import sleep
from dotenv.main import load_dotenv

load_dotenv()

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

        if record.levelname == 'DEBUG':
            self._style._fmt = self.dbg_fmt
        if record.levelname == 'ingo':
            self._style._fmt = self.info_fmt
        if record.levelname == 'WARNING':
            self._style._fmt = self.warn_fmt
        if record.levelname == 'ERROR':
            self._style._fmt = self.err_fmt

        result = logging.Formatter.format(self, record)

        self._style._fmt = format_orig

        return result


class WebhookFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()
        
    def prefixcalc(self, levelname: str):
        if levelname == 'DEBUG':
            return '===| '
        if levelname == 'INFO':
            return '+  | '
        if levelname == 'WARNING':
            return 'W  | '
        if levelname == 'ERROR':
            return '!  | '
        if levelname == 'CRITICAL':
            return '-!! | '

    def format(self, record: logging.LogRecord):
        msg = logging.Formatter.format(self, record)
        return "```diff\n{}{}```".format(self.prefixcalc(record.levelname), msg)

class WebhookLogger(logging.Handler):
    def __init__(self):
        self.level = logging.INFO
        super().__init__(self.level)
        self.webhook_url = os.environ.get("WEBHOOK_URL")

    def emit(self, record: logging.LogRecord):
        self.send(WebhookFormatter().format(record), record)
            
    def send(self, formatted, record):
        if self.webhook_url is None:
            return
        
        parts = [formatted[i:i+2000] for i in range(0, len(formatted), 2000)]
        for i, part in enumerate(parts):
            if i == 0:
                content = f'{part}```'
                if part == parts[-1]:
                    content = part
                    if record.levelname == 'ERROR' or record.levelname == 'CRITICAL':
                        content += f'<@{os.environ.get("OWNER_ID")}>'
                requests.post(self.webhook_url, json={'content':content})
                
            else:
                content = f'```diff\n{part}```'
                if part == parts[-1]:
                    content = f'```diff\n{part}'
                    if record.levelname == 'ERROR' or record.levelname == 'CRITICAL':
                        content += f'<@{os.environ.get("OWNER_ID")}>'
                requests.post(self.webhook_url, json={'content':content})

class Logger:
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--disable-discord-logs', help='Disables Discord logging.', action='store_true')
        parser.add_argument('--disable-scheduler-logs', help='Disables scheduler logs.', action='store_true')
        parser.add_argument('--disable-webhook-logging', help='Disables logging to the webhook.', action='store_true')

        args = parser.parse_args()

        self.HNDLR = logging.StreamHandler(sys.stdout)
        self.HNDLR.formatter = Formatter()
        if not args.disable_discord_logs:
            discord_logger = logging.getLogger('discord')
            discord_logger.setLevel(logging.INFO)
            discord_logger.addHandler(self.HNDLR)
            if not args.disable_webhook_logging:
                discord_logger.addHandler(WebhookLogger())
        if not args.disable_scheduler_logs:
            ap_logger = logging.getLogger('apscheduler')
            ap_logger.setLevel(logging.INFO)
            ap_logger.addHandler(self.HNDLR)
            if not args.disable_webhook_logging:
                ap_logger.addHandler(WebhookLogger())
        self.logger = logging.Logger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.HNDLR)
        if not args.disable_webhook_logging:
            self.logger.addHandler(WebhookLogger())
        
logger = Logger().logger