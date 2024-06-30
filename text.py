
from enum import StrEnum, Enum

# https://en.wikipedia.org/wiki/ANSI_escape_code

class STYLE(StrEnum):
    # https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_(Select_Graphic_Rendition)_parameters
    NONE =          '\033[0m'
    BOLD =          '\033[1m'
    ITALICS =       '\033[3m'
    UNDERLINE =     '\033[4m'
    HIGHLIGHT =     '\033[7m'
    STRIKETHROUGH = '\033[9m'

    # https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
    FG_BLACK =   '\033[30m'
    FG_RED =     '\033[31m'
    FG_GREEN =   '\033[32m'
    FG_YELLOW =  '\033[33m'
    FG_BLUE =    '\033[34m'
    FG_MAGENTA = '\033[35m'
    FG_CYAN =    '\033[36m'
    FG_WHITE =   '\033[37m'
    FG_BRIGHT_BLACK =   '\033[90m'
    FG_BRIGHT_RED =     '\033[91m'
    FG_BRIGHT_GREEN =   '\033[92m'
    FG_BRIGHT_YELLOW =  '\033[93m'
    FG_BRIGHT_BLUE =    '\033[94m'
    FG_BRIGHT_MAGENTA = '\033[95m'
    FG_BRIGHT_CYAN =    '\033[96m'
    FG_BRIGHT_WHITE =   '\033[97m'
    BG_BLACK =   '\033[40m'
    BG_RED =     '\033[41m'
    BG_GREEN =   '\033[42m'
    BG_YELLOW =  '\033[43m'
    BG_BLUE =    '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN =    '\033[46m'
    BG_WHITE =   '\033[47m'
    BG_BRIGHT_BLACK =   '\033[100m'
    BG_BRIGHT_RED =     '\033[101m'
    BG_BRIGHT_GREEN =   '\033[102m'
    BG_BRIGHT_YELLOW =  '\033[103m'
    BG_BRIGHT_BLUE =    '\033[104m'
    BG_BRIGHT_MAGENTA = '\033[105m'
    BG_BRIGHT_CYAN =    '\033[106m'
    BG_BRIGHT_WHITE =   '\033[107m'

def style(text: str, start: STYLE | str, end:STYLE | str = STYLE.NONE) -> str:
    '''
    It is also valid to concatenate multiple STYLE str together
    '''
    return start + text + end

if __name__ == '__main__':
    for item in STYLE:
        # print(style_text(f'VALUE: {i:2}', f'\033[{i}m'))
        text = style(f'{item.name}', item)
        print(text)
        print()