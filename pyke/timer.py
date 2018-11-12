import time
from .terminal import terminal
from ansiTerm.ansiTerm import ansiTerm as t


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


  def report(self, verbose=False):
    if verbose:
      print (t.pushState('timerReportDark'))
      print ("{0:>40}  {1}".format("Operation", "Time"))
      print ("{0:>40}  {1}".format("---------", "----"))
      print (t.pushState('timerReportLight'))
      for i in range(0, len(self.timer_marks)):
        label, start, duration, depth = self.timer_marks[i]
        label = ''.join([label, ' .' * depth])
        print ("{0:>40}  {1:.3f} s".format(label, duration))
      print (t.popStates())
      print ("{0:>40}  {1}".format("---------", "----"))
    print (t.pushState('timerReportLight'))
    print ("{0:>40}  {1:.3f} s".format("Total time:",
      self.timer_marks[-1][2]))
    print (t.popStates())
    if verbose:
      print (t.popStates())

timer = taskTimer()
