import glob
import logging
import os
import select
import shutil
import socket
import struct

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Inhibitor:
    inhibitions = {}

    @staticmethod
    def get_nodes(hidraw: int) -> list[str]:
        return glob.glob(f'/sys/class/hidraw/hidraw{hidraw}/device/input/input*/inhibited')

    @classmethod
    def inhibit(cls, hidraw: int):
        if hidraw in cls.inhibitions:
            cls.inhibitions[hidraw] += 1
            return

        for node in cls.get_nodes(hidraw):
            with open(node, 'w') as f:
                f.write('1\n')
        cls.inhibitions[hidraw] = 1

    @classmethod
    def uninhibit(cls, hidraw: int):
        i = cls.inhibitions.get(hidraw)
        if i is None:
            return
        i -= 1
        if i:
            cls.inhibitions[hidraw] = i
            return

        del cls.inhibitions[hidraw]
        for node in cls.get_nodes(hidraw):
            with open(node, 'w') as f:
                f.write('0\n')


class InhibitionServer:
    CMD_INHIBIT = 1
    CMD_UNINHIBIT = 2
    CMD_SHUTDOWN = 0xFF

    SOCKPATH = '/tmp/ds-inhibit'

    def __init__(self):
        self._server = None
        self.sockets = {}
        self._parse = struct.Struct('IB')

    def _start(self):
        logger.info('Starting server')
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.SOCKPATH)
        os.chmod(self.SOCKPATH, 0o660)
        shutil.chown(self.SOCKPATH, group='input')
        self._server.listen()
        self.sockets[self._server.fileno()] = 'server'
        self._poll = select.poll()
        self._poll.register(self._server.fileno(), select.POLLIN)
        self.running = True

    def _stop(self):
        logger.info('Stopping server')
        for fd, hidraws in self.sockets.items():
            if hidraws == 'server':
                continue
            os.close(fd)
            for hidraw in hidraws:
                Inhibitor.uninhibit(hidraw)
        self._server.close()
        self.sockets = {}
        self._server = None
        self._poll = None
        os.unlink(self.SOCKPATH)

    def poll(self):
        ev = self._poll.poll()
        for fd, event in ev:
            inhibitions = self.sockets.get(fd)
            if inhibitions is None:
                continue

            if inhibitions == 'server':
                sock, addr = self._server.accept()
                self.register_client(sock.detach())
                continue

            logger.debug(f'Got events {event:X} on {fd}')
            if event & select.POLLHUP:
                self.unregister_client(fd)
                continue
            if event & select.POLLIN:
                message = os.read(fd, 5)
                if len(message) < 5:
                    logger.warning(f'Got truncated message from {fd}, discarding')
                else:
                    self.process_message(fd, message)

    def register_client(self, fd):
        logger.info(f'Registering client on socket {fd}')
        self.sockets[fd] = set()
        self._poll.register(fd, select.POLLIN | select.POLLHUP)

    def unregister_client(self, fd):
        logger.info(f'Unregistering client on socket {fd}')
        try:
            os.close(fd)
        except OSError:
            pass
        for hidraw in self.sockets[fd]:
            Inhibitor.uninhibit(hidraw)
        self._poll.unregister(fd)
        del self.sockets[fd]

    def process_message(self, fd, message):
        id, cmd = self._parse.unpack(message)
        logger.debug(f'Got message {id:08X}:{cmd:02X} on {fd}')
        if cmd == self.CMD_INHIBIT:
            logger.debug(f'Got INHIBIT {id} on {fd}')
            self.do_inhibit(fd, id)
        elif cmd == self.CMD_UNINHIBIT:
            logger.debug(f'Got UNINHIBIT {id} on {fd}')
            self.do_uninhibit(fd, id)
        elif cmd == self.CMD_SHUTDOWN:
            logger.debug(f'Got SHUTDOWN on {fd}')
            self.do_shutdown()

    def serve(self):
        self._start()

        while self.running:
            try:
                self.poll()
            except (KeyboardInterrupt, OSError):
                self.running = False

        self._stop()

    def do_inhibit(self, fd, id):
        if id in self.sockets[fd]:
            return
        self.sockets[fd].add(id)
        Inhibitor.inhibit(id)

    def do_uninhibit(self, fd, id):
        if id not in self.sockets[fd]:
            return
        self.sockets[fd].remove(id)
        Inhibitor.uninhibit(id)

    def do_shutdown(self):
        self.running = False


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    server = InhibitionServer()
    server.serve()
