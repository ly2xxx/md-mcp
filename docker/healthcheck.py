"""Container healthcheck — transport-aware.

In HTTP transports the server opens a TCP port, so we probe it. In stdio mode
there is no listening port (the server talks over stdin/stdout), so a port probe
would always fail and wrongly mark the container "unhealthy" — there we just
report healthy.
"""

import os
import socket
import sys


def main() -> int:
    transport = os.environ.get("MD_TRANSPORT", "http").lower()
    if transport == "stdio":
        return 0  # no port to probe; stdio containers are healthy by definition

    port = int(os.environ.get("MD_PORT", "8000"))
    sock = socket.socket()
    sock.settimeout(3)
    try:
        return 0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1
    finally:
        sock.close()


if __name__ == "__main__":
    sys.exit(main())
