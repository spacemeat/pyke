import string
from terminal import terminal as t

class command():
    def __init__(self, name = "root", parent = None):
        self.name = name
        self.parent = parent
        self.children = list()
        
    def _repr_rec(self, depth):
        parent = "<none>"
        if self.parent != None:
            parent = self.parent.name
        s =  "{0}({1}, {2}, [{3}])".format(
            "  " * depth,
            t.make_command(self.name),
            t.make_command(parent),
            len(self.children))
        for cmd in self.children:
            if cmd != None:
                s += "\n" + cmd._repr_rec(depth + 1)
            else:
                s += "\nChild is None"
        
        return s

    def __repr__(self):
        return self._repr_rec(0)
    
class parser():
    def __init__(self):
        pass
    
    @staticmethod
    def _is_token_char(ch):
        return (ch in string.ascii_letters or
                ch in string.digits or
                ch in "-_+./")
    
    def _eat_one(self):
        self.idx += 1
        if self.idx >= len(self.args):
            self.end_of_line = True
    
    def _eat_ws(self):
        if self.idx >= len(self.args):
            self.end_of_line = True
            return
        
        while self.args[self.idx] == ' ':
            self.idx += 1
            if self.idx >= len(self.args):
                self.end_of_line = True
                break

    def _read_token(self):
        self.found_token = False
        self.current_token = ""

        self._eat_ws()
        if self.end_of_line:
            return
        
        while self.end_of_line == False:
            if not parser._is_token_char(self.args[self.idx]):
                break

            self.current_token = ''.join([self.current_token, self.args[self.idx]])
            self.found_token = True
                
            self.idx += 1
            if self.idx >= len(self.args):
                self.end_of_line = True
            
    def _match(self, ch):
        self._eat_ws()
        if not self.end_of_line:
            if self.args[self.idx] == ch:
                self.idx += 1
                if self.idx == len(self.args):
                    self.end_of_line = True
                return True
        return False
        
    def _parse_list(self, parent):
        end_of_list = False
        while (self.end_of_line == False and 
            end_of_list == False):
            
            def _parse_key_value(parent):
                self._eat_ws()
                if self.end_of_line:
                    return
                    
                self._read_token()
                if self.found_token:
                    new_command = command(self.current_token, parent)
                    parent.children.append(new_command)
                
                    if self._match(':'):
                        if not self.end_of_line:
                            self._parse_list(new_command)
                else:
                    raise ValueError("Expected token at column {0}.".format(self.idx))
            
            _parse_key_value(parent)
            if self.end_of_line:
                end_of_list = True

            if self._match(','):
                pass
            
            if self._match(';'):
                end_of_list = True

    def _parse(self, parent):
        if len(self.args) > 0:
            self._parse_list(parent)

    def parse_args(self, args):
        self.args = args
        self.idx = 0
        self.current_token = ""
        self.end_of_line = False

        self.root = command()

        self._parse(self.root)
        return self.root

