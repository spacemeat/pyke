'''
Convenience objects and functions for creating ANSI color codes.
'''

# pylint: disable=invalid-name
# I'm strangely comfortable with it.

off = '\033[0m'

def b24_fg(c: tuple[int, int, int]):
    ''' Creates a foreground color code from r, g, b.'''
    r, g, b = c
    return f'\033[38;2;{r};{g};{b}m'

def b24_bg(c: tuple[int, int, int]):
    ''' Creates a background color code from r, g, b.'''
    r, g, b = c
    return f'\033[48;2;{r};{g};{b}m'

def b8_fg(c):
    ''' Creates a foreground color code for 8bit c.'''
    return f'\033[38;5;{c}m'

def b8_bg(c):
    ''' Creates a foreground color code for 8bit c.'''
    return f'\033[48;5;{c}m'

named_fg = {
    'black': '\033[30m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'white': '\033[37m',

    'bright black': '\033[90m',
    'bright red': '\033[91m',
    'bright green': '\033[92m',
    'bright yellow': '\033[93m',
    'bright blue': '\033[94m',
    'bright magenta': '\033[95m',
    'bright cyan': '\033[96m',
    'bright white': '\033[97m',
}

named_bg = {
    'black': '\033[40m',
    'red': '\033[41m',
    'green': '\033[42m',
    'yellow': '\033[43m',
    'blue': '\033[44m',
    'magenta': '\033[45m',
    'cyan': '\033[46m',
    'white': '\033[47m',

    'bright black': '\033[100m',
    'bright red': '\033[101m',
    'bright green': '\033[102m',
    'bright yellow': '\033[103m',
    'bright blue': '\033[104m',
    'bright magenta': '\033[105m',
    'bright cyan': '\033[106m',
    'bright white': '\033[107m',
}
