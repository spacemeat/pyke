### Begin WIP

import os

class Terminal:
    pass
    
class ColorTerminal(Terminal):
    dk_black_fg = '\033[30m'
    dk_red_fg = '\033[31m'
    dk_green_fg = '\033[32m'
    dk_yellow_fg = '\033[33m'
    dk_blue_fg = '\033[34m'
    dk_magenta_fg = '\033[35m'
    dk_cyan_fg = '\033[36m'
    dk_white_fg = '\033[37m'
    
    lt_black_fg = '\033[90m'
    lt_red_fg = '\033[91m'
    lt_green_fg = '\033[92m'
    lt_yellow_fg = '\033[93m'
    lt_blue_fg = '\033[94m'
    lt_magenta_fg = '\033[95m'
    lt_cyan_fg = '\033[96m'
    lt_white_fg = '\033[97m'

    dk_black_bg = '\033[40m'
    dk_red_bg = '\033[41m'
    dk_green_bg = '\033[42m'
    dk_yellow_bg = '\033[43m'
    dk_blue_bg = '\033[44m'
    dk_magenta_bg = '\033[45m'
    dk_cyan_bg = '\033[46m'
    dk_white_bg = '\033[47m'

    lt_black_bg = '\033[100m'
    lt_red_bg = '\033[101m'
    lt_green_bg = '\033[102m'
    lt_yellow_bg = '\033[103m'
    lt_blue_bg = '\033[104m'
    lt_magenta_bg = '\033[105m'
    lt_cyan_bg = '\033[106m'
    lt_white_bg = '\033[107m'

    all_off = '\033[0m'
    bold = '\033[1m'
    italic = '\033[3m'
    underline = '\033[4m'
    blink = '\033[5m'
    inverse = '\033[7m'
    hidden = '\033[8m'
    strike = '\033[9m'
    
    unbold = '\033[22m'
    unitalic = '\033[23m'
    ununderline = '\033[24m'
    unblink = '\033[25m'
    uninverse = '\033[27m'
    unhidden = '\033[28m'
    unstrike = '\033[29m'
    
    @staticmethod
    def system_color(color_value, foreground):
        if color_value.startswith("dk-"):
            is_light = False
        elif color_value.startswith("lt-"):
            is_light = True
        else:
            raise Exception("Color format incorrect: \"%s\"" % color_value)
            
        if foreground:
            if not is_light:
                selector = '3'
            else:
                selector = '9'
        else:
            if not is_light:
                selector = '4'
            else:
                selector = '10'
            
        color_value = color_value[3:]
        if color_value == "black":
            color = '0'
        elif color_value == "red":
            color = '1'
        elif color_value == "green":
            color = '2'
        elif color_value == "yellow":
            color = '3'
        elif color_value == "blue":
            color = '4'
        elif color_value == "magenta":
            color = '5'
        elif color_value == "cyan":
            color = '6'
        elif color_value == "white":
            color = '7'
        
        return "%s%s" % (selector, color)

    @staticmethod
    def rgb_color_fg(r, g, b, foreground):
        """Returns the ANSI/VT100 256-color escape code, in the RGB color range. 
        r, g, and b can have values of 0-5."""
        num = 16    # the rgb numbers start at 16
        num += 36 * r
        num += 6 * g
        num += b
        if foreground:
            return "38;5;%d" % num
        else:
            return "48;5;%d" % num

    @staticmethod
    def gray_color_fg(gray, foreground):
        """Returns the ANSI/VT1oo 256-color escape code, in the grayscale range.
        gray can have a value of 0-24."""
        if foreground:
            return "38;5;%d" % gray + 232
        else:
            return "48;5;%d" % gray + 232
        
    @staticmethod
    def get_default_states():
        return {
            'fg-color' : 'system-lt-white',
            'bg-color' : 'system-dk-black',
            'bold' : 'off',
            'italic' : 'off',
            'under' : 'off',
            'blink' : 'off',
            'inverse' : 'off',
            'hidden' : 'off',
            'strike' : 'off'
        }
    
    def __init__(self):
        # stores escape strings for rollling back operations.
        self.undo_stack = []
        self.states = ColorTerminal.get_default_states()
    
    def push_state(self, states):
        """ states is a list of 2-tuples, each specifying like ('fg-color', 'light-red')
        Each attribute is added to a changelist, which is then applied and pushed to
        the stack. Repeated attribute names override.
        Returns the escape string which activates the state change.
        """
        changelist, undolist = self._make_diff_from_self(states)
        # undos are done later
        self.undo_stack.append(undolist)
        
        do_strings = []

        # make undo string, and push it
        # make do string, and return it
        for doer in changelist:
            if self.states[doer[0]] != doer[1]:
                self.states[doer[0]] = doer[1]
                do_strings.append(self._make_commandlet(doer))

        do_string = ""
        if len(do_strings) > 0:
            do_string = self._make_command(do_strings)

        # return the action
        return do_string
        
    def push_reset_states(self, states):
        """ states is a list of 2-tuples, each specifying like ('fg-color', 'dark-yellow')
        This effectively resets all colors and attributes, and then applies the profile
        elements as in push_states().
        Returns the escape string which activates the state change.
        """
        return push_states(ColorTerminal.get_default_states() + states)
        
    def pop_states(self, num_states = 1):
        """
        This reverts state to how it was before the corresponding push.
        Returns the escape string which activates the state change.
        """
        do_string = ''
        
        changes = {}

        # Here, later pops override earlier states, which is approps.        
        for i in range(0, num_states):
            assert len(self.undo_stack) > 0
            for cmd in self.undo_stack.pop():
                self.states[cmd[0]] = cmd[1]
                changes[cmd[0]] = cmd[1]

        do_strings = []

        for state_type, state_value in changes.items():
            cmdlet = self._make_commandlet( (state_type, state_value) )
            if cmdlet != None:
                do_strings.append(cmdlet)

        do_string = ""
        if len(do_strings) > 0:
            do_string = self._make_command(do_strings)

        return do_string
        
    def fmt(self, string, states):
        return "%s%s%s" % (self.push_state(states), string, self.pop_states())

    def fmt_r(self, string, states):
        return "%s%s%s" % (self.push_reset_state(states), string, self.pop_states())

    def _make_diff_from_self(self, states):
        changelist = [] # holds ('fg-color', 'system-dk-blue') tuples, at most one for each state type.
        undolist = [] # holds like changelist
        seen = set() # holds like 'fg-color'
        state_types = set(self.states) # 'fg-color', 'bg-color', 'underline', 'bold'...

        # For each state setting, if we haen't encountered its state type yet, and if it is
        # different than the current state, then record its action and how to undo it.
        for state_type, state_value in states.items():
            if (state_type in state_types and
                not state_type in seen):
                if state_value != self.states[state_type]:
                    changelist.append( (state_type, state_value) )
                    undolist.append( (state_type, self.states[state_type]) )
                seen.add(state_type)

        return changelist, undolist

    def _make_commandlet(self, state):
        state_type, state_value = state
        if state_type == "fg-color":
            color = True
            foreground = True
        elif state_type == "bg-color":
            color = True
            foreground = False
        elif state_type == "bold":
            color = False
            bold = True
        elif state_type == "italic":
            color = False
            italic = True
        elif state_type == "underline":
            color = False
            underline = True
        elif state_type == "blink":
            color = False
            blink = True
        elif state_type == "inverse":
            color = False
            inverse = True
        elif state_type == "hidden":
            color = False
            hidden = True
        elif state_type == "strike":
            color = False
            strike = True
            
        def binary_state(state_value, on, off):
            if state_value == "on":
                return on
            elif state_value == 'off':
                return off
            else:
                raise Exception("Binary format incorrect: \"%s\"" % state_value)
                
        if color:
            if state_value.startswith("system-"):
                color = state_value[7:]

                if foreground:
                    return self.system_color(color, foreground)
                else:
                    return self.system_color(color, background)
            
            elif state_value.startswith("rgb-"):
                rgb_value = state_value[4:]
                r, g, b = [int(c) for c in rgb_value[0:3]]
                for c in [r, g, b]:
                    if c < 0 or c > 6:
                        raise Exception("Color format incorrect: \"%s\"" % state_value)

                if foreground:
                    return rgb_color(r, g, b, foreground)
                else:
                    return rgb_color(r, g, b, foreground)
            
            elif state_value.startswith("gs-"):
                gray_value = state_value[3:]
                gray = int(gray_value)
                if gray < 0 or gray > 24:
                    raise Exception("Color format incorrect: \"%s\"" % state_value)
                if foreground:
                    return gray_color(r, g, b, foreground)
                else:
                    return gray_color(r, g, b, foreground)

        elif bold:
            return binary_state(state_value, '1', '22')

        elif italic:
            return binary_state(state_value, '3', '23')

        elif underline:
            return binary_state(state_value, '4', '24')

        elif blink:
            return binary_state(state_value, '5', '25')

        elif inverse:
            return binary_state(state_value, '7', '27')

        elif hidden:
            return binary_state(state_value, '8', '28')

        elif strike:
            return binary_state(state_value, '9', '29')

        else:
            raise Exception("Invalid state \"%s\"" % state_type)

    # TODO: Make this static
    def _make_command(self, commandlets):
        cmd = ";".join(str(cmdl) for cmdl in commandlets)
        return "\033[%sm" % cmd
        
    
    def make_file_name(self, s):
        d, f = os.path.split(str(s))
        if len(d) == 0:
            return self.fmt(s, { 'fg-color' : 'system-dk-cyan', 'bold' : 'on' })
        else:
            return "%s%s/%s%s%s" % (
                self.push_state( { 'fg-color' : 'system-dk-cyan' } ), d,
                self.push_state( { 'bold' : 'on' } ), f,
                self.pop_states(2))
            
    
    def print_title(self, title, title_length):
        print ('-' * 79)
#        title_bw = "--------[ {} ]".format(title)
        title = "--------[ {} ]".format(title)
        print (''.join((title, '-' * (79 - len("--------[  ]") - title_length))))
        print ('-' * 79)
    
    def make_dir(self, s):
        return self.fmt(s, { 'fg-color' : 'system-dk-cyan' })
            
    def make_include(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-blue', 'bold' : 'on' })
        
    def make_project_name(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-blue', 'bold' : 'on' })
        
    def make_project_path(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-blue', 'bold' : 'off' })
        
    def make_project_type(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-yellow', 'bold' : 'off' })
        
    def make_command(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-blue', 'bold' : 'on' })
        
    def make_command_arg(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-magenta', 'bold' : 'off' })

    def make_command_doc(self, s):
        return self.fmt(s, { 'fg-color' : 'system-dk-blue', 'bold' : 'off' })

    def make_command_arg_doc(self, s):
        return self.fmt(s, { 'fg-color' : 'system-dk-magenta', 'bold' : 'off' })
    
    def make_configuration(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-yellow', 'bold' : 'on' })

    def make_step(self, s):
        return self.fmt(s, { 'fg-color' : 'system-dk-blue', 'bold' : 'off' })
        
    def make_test_name(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-magenta', 'bold' : 'on' })
        
    def make_timer_text(self, s):
        return self.fmt(s, { 'fg-color' : 'system-dk-magenta', 'bold' : 'off' })
        
    def make_timer_mark(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-magenta', 'bold' : 'off' })
        
        
        
    def make_dark(self, s):
        return self.fmt(s, { 'fg-color' : 'system-dk-black', 'bold' : 'on' })

    def make_syscommand(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-black', 'bold' : 'on' })

    def make_warn(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-yellow', 'bold' : 'on' })

    def make_error(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-red', 'bold' : 'on' })

    def make_success(self, s):
        return self.fmt(s, { 'fg-color' : 'system-lt-green', 'bold' : 'on' })
        
    def make_true_false(self, b):
        if b:
            return self.error('false')
        else:
            return self.success('true')

    def make_bold(self, s):
        return self.fmt(s, { 'bold' : 'on' })

    def make_italic(self, s):
        return self.fmt(s, { 'italic' : 'on' })

    def make_underline(self, s):
        return self.fmt(s, { 'underline' : 'on' })

    def make_blink(self, s):
        return self.fmt(s, { 'blink' : 'on' })

    def make_inverse(self, s):
        return self.fmt(s, { 'inverse' : 'on' })

    def make_hidden(self, s):
        return self.fmt(s, { 'hidden' : 'on' })

    def make_strike(self, s):
        return self.fmt(s, { 'strike' : 'on' })
        
# global instance
terminal = ColorTerminal()

### END WIP

def term_file_name(s):
    d, f = os.path.split(str(s))
    return "%s%s/%s%s%s" % (
        term_codes.cyan_fg,
        d,
        term_codes.bold,
        f,
        term_codes.all_off)

def term_project_name(s):
    return "%s%s%s%s" % (
        term_codes.blue_fg,
        term_codes.bold,
        s,
        term_codes.all_off)
        
def term_syscommand(s):
    return "%s%s%s%s" % (
        term_codes.black_fg,
        term_codes.bold,
        s,
        term_codes.all_off)
        
def term_warn(s):
    return "%s%s%s%s" % (
        term_codes.yellow_fg,
        term_codes.bold,
        s,
        term_codes.all_off)

def term_fail(s):
    return "%s%s%s%s" % (
        term_codes.red_fg,
        term_codes.bold,
        s,
        term_codes.all_off)

def term_pass(s):
    return "%s%s%s%s" % (
        term_codes.green_fg,
        term_codes.bold,
        s,
        term_codes.all_off)
        
def term_pass_fail(b):
    if b:
        return term_pass("True")
    else:
        return term_fail("False")
        
def term_bold(s):
    return "%s%s%s" % (
        term_codes.bold,
        s,
        term_codes.all_off)

def term_underline(s):
    return "%s%s%s" % (
        term_codes.underline,
        s,
        term_codes.all_off)

def term_template(s):
    return "%s%s%s%s" % (
        term_codes.black_fg,
        term_codes.bold,
        s,
        term_codes.all_off)

def term_scopes(s):
    return "%s%s%s%s" % (
        term_codes.black_fg,
        term_codes.bold,
        s,
        term_codes.all_off)

