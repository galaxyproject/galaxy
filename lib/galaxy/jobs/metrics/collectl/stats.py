""" Primitive module for tracking running statistics without storing values in
memory.
"""


class StatisticsTracker(object):

    def __init__(self):
        self.min = None
        self.max = None
        self.count = 0
        self.sum = 0

    def track(self, value):
        if self.min is None or value < self.min:
            self.min = value
        if self.max is None or value > self.max:
            self.max = value
        self.count += 1
        self.sum += value

    @property
    def avg(self):
        if self.count > 0:
            return self.sum / self.count
        else:
            return None
