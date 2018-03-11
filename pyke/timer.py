import time
from terminal import terminal as t


class task_timer():
    def __init__(self, on = True):
        self.is_timer_on = on
        self.timer_marks = []
        self.timer_marks.append(("start", time.perf_counter()))
    

    def reset(self):
        if self.is_timer_on == False:
            self.is_timer_on = True
            self.timer_marks = []
            self.timer_marks.append(("start", time.perf_counter()))
        

    def mark(self, mark):
        tm = time.perf_counter()
        self.timer_marks.append((mark, tm))
        print ("{0}Mark '{1}': Time since last mark: {2:.3f} s{3}".format(
            t.push_state({ 'fg-color' : 'system-dk-magenta', 'bold' : 'off' }),
            t.make_timer_mark(mark),
            tm - self.timer_marks[-2][1],
            t.pop_states()))


    def report(self):
        print (t.push_state({ 'fg-color' : 'system-dk-magenta', 'bold' : 'off' }))
        print ("{0:>40}  {1}".format("Operation", "Time"))
        print ("{0:>40}  {1}".format("---------", "----"))
        print (t.push_state({ 'fg-color' : 'system-lt-magenta', 'bold' : 'off' }))
        for i in range(1, len(self.timer_marks)):
            print ("{0:>40}  {1:.3f} s".format(self.timer_marks[i][0],
                self.timer_marks[i][1] - self.timer_marks[i - 1][1]))
        print (t.pop_states())
        print ("{0:>40}  {1}".format("---------", "----"))
        print ("{0:>40}  {1:.3f} s".format("Total time:",
            self.timer_marks[-1][1] - self.timer_marks[0][1]))
        print (t.pop_states())
    

timer = task_timer()

