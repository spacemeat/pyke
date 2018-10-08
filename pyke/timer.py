import time
from .terminal import terminal as t


class taskTimer():
    def __init__(self):
        self.is_timer_on = False
        self.timer_marks = []
        self.depth = 0
        self.running_timers = []
    

    def start(self, label):
        tm = time.perf_counter()
        self.running_timers.append((label, tm))
        self.depth += 1


    def done(self):
        tm = time.perf_counter()
        if len(self.running_timers) == 0:
            raise RuntimeError('done() called with no tiers running.')

        label, st = self.running_timers.pop()
        self.depth -= 1
        self.timer_marks.append((label, st, tm - st, self.depth))


    def report(self):
        print (t.push_state({ 'fg-color' : 'system-dk-magenta', 'bold' : 'off' }))
        print ("{0:>40}  {1}".format("Operation", "Time"))
        print ("{0:>40}  {1}".format("---------", "----"))
        print (t.push_state({ 'fg-color' : 'system-lt-magenta', 'bold' : 'off' }))
        for i in range(0, len(self.timer_marks)):
            label, start, duration, depth = self.timer_marks[i]
            label = ''.join([label, ' .' * depth])
            print ("{0:>40}  {1:.3f} s".format(label, duration))
        print (t.pop_states())
        print ("{0:>40}  {1}".format("---------", "----"))
        print ("{0:>40}  {1:.3f} s".format("Total time:",
            self.timer_marks[-1][2]))
        print (t.pop_states())

timer = taskTimer()
