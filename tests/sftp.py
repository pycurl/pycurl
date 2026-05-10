import logging
import socket
import threading

import pytest

paramiko = pytest.importorskip('paramiko')

logging.getLogger('paramiko').setLevel(logging.CRITICAL)


class SFTPServerInterface(paramiko.ServerInterface):
    """SSH server that rejects all authentication, used to exercise key callbacks."""

    def check_auth_none(self, username):
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


class LocalSFTPServer:
    """Minimal SSH/SFTP server for testing SSH key callbacks."""

    def __init__(self):
        self._host_key = paramiko.RSAKey.generate(2048)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._sock.bind(('127.0.0.1', 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(5)
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        self._sock.settimeout(0.5)
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()

    def _handle_conn(self, conn):
        transport = paramiko.Transport(conn)
        transport.add_server_key(self._host_key)
        try:
            transport.start_server(server=SFTPServerInterface())
            transport.join(5)
        except Exception:
            pass
        finally:
            try:
                transport.close()
            except Exception:
                pass

    def stop(self):
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass
        if self._thread:
            self._thread.join(2)
