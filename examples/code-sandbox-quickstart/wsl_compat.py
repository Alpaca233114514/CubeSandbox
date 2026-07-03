# Copyright (c) 2024 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

"""WSL2 compatibility helpers for the CubeSandbox SDK demos.

On a fresh local WSL2 deployment the sandbox MicroVM boots quickly, but the
Jupyter kernel gateway inside the sandbox-code image (port 49999) can take a
few seconds to become ready. The upstream examples call run_code() immediately,
which produces a 502 Bad Gateway on slower systems. Import and call
wait_for_code_interpreter() before the first run_code() call to avoid this.
"""

import ssl
import time
import urllib.request

from e2b_code_interpreter import Sandbox

_poll_ctx = ssl.create_default_context()
_poll_ctx.check_hostname = False
_poll_ctx.verify_mode = ssl.CERT_NONE


def wait_for_code_interpreter(sandbox: Sandbox, timeout: int = 60) -> None:
    """Poll the sandbox kernel gateway /health until it responds.

    Trusts the certificate configured via SSL_CERT_FILE for normal SDK traffic,
    but skips verification for the readiness probe itself so the helper works
    even when the local mkcert root is not yet trusted.
    """
    sid = sandbox.get_info().sandbox_id
    host = f"49999-{sid}.cube.app"
    url = f"https://{host}/health"
    print(f"waiting for code interpreter at {host}")
    for i in range(timeout):
        try:
            with urllib.request.urlopen(url, timeout=2, context=_poll_ctx):
                print(f"ready after {i}s")
                return
        except Exception as exc:
            if i % 5 == 0:
                print(f"  not ready ({i}s): {exc}")
            time.sleep(1)
    raise TimeoutError(f"code interpreter on {host} did not become ready")
