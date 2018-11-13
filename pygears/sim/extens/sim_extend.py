import atexit

from pygears.conf import reg_inject, Inject


class SimExtend:
    @reg_inject
    def __init__(self, top=None, sim=Inject('sim/simulator')):
        self.sim = sim
        for name, event in self.sim.events.items():
            try:
                event.append(getattr(self, name))
            except AttributeError:
                pass

        try:
            atexit.register(self.at_exit, sim=None)
        except AttributeError:
            pass
