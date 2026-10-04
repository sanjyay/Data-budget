"""Private, atomic, locked local state. Never recover corrupt state by overwriting it."""
import fcntl
import json
import os
from pathlib import Path
import secrets
import stat

from model import validate_state

LIMIT = 262144


class Store:
    def __init__(self, base=None):
        if base is None:
            base = os.environ.get('XDG_STATE_HOME') or str(Path.home() / '.local/state')
        base = Path(base)
        if not base.is_absolute():
            raise ValueError('XDG_STATE_HOME must be absolute.')
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / 'hotspot-budget'
        try:
            self.path.mkdir(mode=0o700)
        except FileExistsError:
            pass
        self.directory = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        s = os.fstat(self.directory)
        if s.st_uid != os.getuid() or s.st_mode & 0o077:
            os.close(self.directory)
            raise ValueError('State directory must be owned by you with mode 0700.')
        try:
            self.lock = self.open_file('lock', os.O_RDWR | os.O_CREAT)
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.close()
            raise ValueError('Another Data Budget tracker is already running.') from None
        except Exception:
            self.close()
            raise

    def open_file(self, name, flags):
        fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.directory)
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_nlink != 1 or s.st_mode & 0o077:
            os.close(fd)
            raise ValueError('State file must be a private, owned regular file.')
        return fd

    def load(self):
        try:
            fd = self.open_file('state.json', os.O_RDONLY)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, 'rb') as stream:
            data = stream.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError('Saved state exceeds its size limit.')
        return validate_state(json.loads(data))

    def save(self, state):
        validate_state(state)
        data = json.dumps(state, ensure_ascii=True, separators=(',', ':')).encode()
        if len(data) > LIMIT:
            raise ValueError('State exceeds its size limit.')
        name = '.state-' + secrets.token_hex(12)
        fd = self.open_file(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, 'state.json', src_dir_fd=self.directory, dst_dir_fd=self.directory)
            os.fsync(self.directory)
        finally:
            try:
                os.unlink(name, dir_fd=self.directory)
            except FileNotFoundError:
                pass

    def close(self):
        for field in ('lock', 'directory'):
            fd = getattr(self, field, None)
            if fd is not None:
                os.close(fd)
                setattr(self, field, None)
