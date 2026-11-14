"""pytest plugin that keeps a test run on the machine it runs on.

Loaded with `-p reach_offline` by every pytest call of the study (PROTOCOL.md,
section 4, "Outside connections") and by the offline check of the selection
(SELECTION.md, criterion I5); this folder holds no other module, so that
putting it on the module search path adds nothing else to a run.

Every attempt to connect a socket to an address that is neither a loopback
address nor a Unix socket, and every name lookup of a host that is neither
`localhost` nor an address literal, is refused with an error and counted. The
count, the first 20 attempts and the number of attempts per test are written
to the file named by the environment variable OFFLINE_OUT when the session
ends. An attempt made while no test runs is counted under an empty test name;
an attempt made by a thread that outlives its test is counted under the test
that runs at that moment.

Only `socket.socket.connect`, `socket.socket.connect_ex` and
`socket.getaddrinfo` are replaced. A lookup through `socket.gethostbyname` and
its variants, and a datagram sent without a connection, are neither refused
nor counted.

When the environment variable OUTCOMES_OUT names a file, the module also
writes there, when the session ends, the node id of every test of which a
report failed (in its setup, its body, its teardown or a subtest) and of every
collector that failed. It only listens: it changes nothing in the run. The
runner reads the expected baseline failures from that file (PROTOCOL.md,
section 4, "Baseline").
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket

ATTEMPTS: list[str] = []
TESTS: dict[str, int] = {}
FAILED_TESTS: set[str] = set()
FAILED_COLLECTORS: set[str] = set()
_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex
_GETADDRINFO = socket.getaddrinfo


def _text(host) -> str:
    return host.decode("ascii", "replace") if isinstance(host, bytes) else str(host)


def _local_host(host) -> bool:
    if host is None:
        return True
    name = _text(host).split("%")[0]
    if name in ("", "localhost"):
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def _literal(host) -> bool:
    try:
        ipaddress.ip_address(_text(host).split("%")[0])
        return True
    except ValueError:
        return False


def _local(address) -> bool:
    if isinstance(address, (str, bytes)):  # the path of a Unix socket
        return True
    return isinstance(address, tuple) and bool(address) and _local_host(address[0])


def _refused(what: str) -> None:
    ATTEMPTS.append(what)
    test = os.environ.get("PYTEST_CURRENT_TEST", "").rsplit(" (", 1)[0]
    TESTS[test] = TESTS.get(test, 0) + 1


def _connect(self, address):
    if not _local(address):
        _refused(f"connect {address!r}")
        raise OSError(f"offline check: connection to {address!r} refused")
    return _CONNECT(self, address)


def _connect_ex(self, address):
    if not _local(address):
        _refused(f"connect_ex {address!r}")
        raise OSError(f"offline check: connection to {address!r} refused")
    return _CONNECT_EX(self, address)


def _getaddrinfo(host, *args, **kwargs):
    if not (_local_host(host) or _literal(host)):
        _refused(f"getaddrinfo {_text(host)!r}")
        raise socket.gaierror(f"offline check: lookup of {_text(host)!r} refused")
    return _GETADDRINFO(host, *args, **kwargs)


def pytest_configure(config) -> None:
    socket.socket.connect = _connect
    socket.socket.connect_ex = _connect_ex
    socket.getaddrinfo = _getaddrinfo


def pytest_collectreport(report) -> None:
    if report.failed:
        FAILED_COLLECTORS.add(report.nodeid)


def pytest_runtest_logreport(report) -> None:
    if report.failed:
        FAILED_TESTS.add(report.nodeid)


def pytest_sessionfinish(session, exitstatus) -> None:
    out = os.environ.get("OFFLINE_OUT")
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            json.dump({"attempts": len(ATTEMPTS), "first": ATTEMPTS[:20],
                       "tests": {k: TESTS[k] for k in sorted(TESTS)}}, handle, indent=1)
            handle.write("\n")
    outcomes = os.environ.get("OUTCOMES_OUT")
    if outcomes:
        with open(outcomes, "w", encoding="utf-8") as handle:
            json.dump({"failed_tests": sorted(FAILED_TESTS),
                       "failed_collectors": sorted(FAILED_COLLECTORS)}, handle, indent=1)
            handle.write("\n")
