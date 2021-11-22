class Logger:
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
        self.good = f"{self.style_list.get('dim')}[{self.style_list.get('reset')}{self.style_list.get('green')}*{self.style_list.get('reset')}{self.style_list.get('dim')}]{self.style_list.get('reset')}"
        self.bad = f"{self.style_list.get('dim')}[{self.style_list.get('reset')}{self.style_list.get('red')}!{self.style_list.get('reset')}{self.style_list.get('dim')}]{self.style_list.get('reset')}"
        self.maybe = f"{self.style_list.get('dim')}[{self.style_list.get('reset')}{self.style_list.get('yellow')}?{self.style_list.get('reset')}{self.style_list.get('dim')}]{self.style_list.get('reset')}"
        
    def info(self, msg: str):
        print(self.good + ' ' + msg)
        
    def error(self, msg: str):
        print(self.bad + ' ' + msg)
        
    def warn(self, msg: str):
        print(self.maybe + ' ' + msg)
        
    def neutral(self, msg: str):
        print(msg)

logger = Logger()
