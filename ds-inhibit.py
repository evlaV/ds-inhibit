import glob
import logging
import os
import pyinotify
import re

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Inhibitor:
    @classmethod
    def get_nodes(cls, id: int) -> list[str]:
        devs = glob.glob(f'/sys/class/hidraw/hidraw{id}/device/input/input*')
        return [f'{d}/inhibited' for d in devs if glob.glob(f'{d}/mouse*')]

    @classmethod
    def can_inhibit(cls, id: int) -> bool:
        for node in cls.get_nodes(id):
            if not os.access(node, os.W_OK):
                return False
        return True

    @classmethod
    def inhibit(cls, id: int):
        for node in cls.get_nodes(id):
            with open(node, 'w') as f:
                f.write('1\n')

    @classmethod
    def uninhibit(cls, id: int):
        for node in cls.get_nodes(id):
            with open(node, 'w') as f:
                f.write('0\n')


class InhibitionServer:
    MATCH = re.compile(r'^/dev/hidraw(\d+)$')

    def __init__(self):
        self.running = False

    def watch(self, hidraw):
        match = self.MATCH.match(hidraw)
        if not match:
            return
        if not Inhibitor.can_inhibit(match.group(1)):
            return
        logger.info(f'Adding {hidraw} to watchlist')
        self._inotify.add_watch(hidraw, pyinotify.IN_DELETE_SELF |
                                pyinotify.IN_OPEN |
                                pyinotify.IN_CLOSE_NOWRITE |
                                pyinotify.IN_CLOSE_WRITE,
                                proc_fun=self._hidraw_process)
        self._check(hidraw)

    def _start(self):
        logger.info('Starting server')
        self._inotify = pyinotify.WatchManager()
        self._inotify.add_watch('/dev', pyinotify.IN_CREATE,
                                proc_fun=self._node_added)
        for hidraw in glob.glob('/dev/hidraw*'):
            self.watch(hidraw)
        self.running = True

    def _stop(self):
        logger.info('Stopping server')
        for watch in self._inotify.watches.values():
            match = self.MATCH.match(watch.path)
            if not match:
                continue
            Inhibitor.uninhibit(match.group(1))

    def _node_added(self, ev):
        self.watch(ev.path)

    def _hidraw_process(self, ev):
        if ev.mask & pyinotify.IN_DELETE_SELF:
            self._inotify.del_watch(ev.wd)
            return
        self._check(ev.path)

    def _check(self, hidraw: str):
        open_procs = []
        match = self.MATCH.match(hidraw)
        if not match:
            return
        for proc in os.listdir('/proc'):
            if not proc.isnumeric():
                continue
            if not os.access(f'/proc/{proc}/fd', os.R_OK):
                continue
            for fd in os.listdir(f'/proc/{proc}/fd'):
                try:
                    path = os.readlink(f'/proc/{proc}/fd/{fd}')
                except FileNotFoundError:
                    continue
                if not path or path != hidraw:
                    continue
                open_procs.append(proc)
        steam = False
        for proc in open_procs:
            with open(f'/proc/{proc}/comm') as f:
                procname = f.read()
            if not procname:
                continue
            if procname.rstrip() == 'steam':
                steam = True
        if steam:
            logger.info(f'Inhibiting {hidraw}')
            Inhibitor.inhibit(match.group(1))
        else:
            logger.info(f'Uninhibiting {hidraw}')
            Inhibitor.uninhibit(match.group(1))

    def poll(self):
        notifier = pyinotify.Notifier(self._inotify)
        notifier.loop()

    def serve(self):
        self._start()

        try:
            self.poll()
        except (KeyboardInterrupt, OSError):
            pass

        self._stop()


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    server = InhibitionServer()
    server.serve()
