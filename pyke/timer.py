import time
from .terminal import terminal as t


class task_timer():
    def __init__(self, startingLabel = "start", on = True):
        self.startingLabel = startingLabel
        self.is_timer_on = on
        self.timer_marks = []
        self.depth = 0
        self.running_timers = []
        if on:
            self.start(self.startingLabel)
    

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

#    def mark(self, label):
#        tm = time.perf_counter()
#        self.timer_marks.append((self.label, tm))
#        self.label = label
#        print ("{0}Mark '{1}': Time since last mark: {2:.3f} s{3}".format(
#            t.push_state({ 'fg-color' : 'system-dk-magenta', 'bold' : 'off' }),
#            t.make_timer_mark(mark),
#            tm - self.timer_marks[-2][1],
#            t.pop_states()))


    def report(self):
        print (t.push_state({ 'fg-color' : 'system-dk-magenta', 'bold' : 'off' }))
        print ("{0:>40}  {1}".format("Operation", "Time"))
        print ("{0:>40}  {1}".format("---------", "----"))
        print (t.push_state({ 'fg-color' : 'system-lt-magenta', 'bold' : 'off' }))
        for i in range(0, len(self.timer_marks)):
            label, start, duration, depth = self.timer_marks[i]
            print ("{0:>40}  {1:.3f} s".format(label, duration))
        print (t.pop_states())
        print ("{0:>40}  {1}".format("---------", "----"))
        print ("{0:>40}  {1:.3f} s".format("Total time:",
            self.timer_marks[0][2]))
        print (t.pop_states())

