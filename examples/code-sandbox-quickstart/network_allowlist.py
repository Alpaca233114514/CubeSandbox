# Copyright (c) 2024 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
network_allowlist.py — Allow only specific destinations; block all other outbound traffic.

Use case:
    The sandbox needs to reach specific external services (e.g. package
    repositories, internal APIs exposed via public domains) while all other
    destinations are blocked to prevent data exfiltration.

How it works:
    network.allow_out sets an allowlist passed to CubeVSContext.AllowOut.
    The Cubelet tap network layer only forwards traffic whose destination
    matches one of the listed CIDRs or learned DNS domains; all other outbound
    packets are dropped.

Note:
    Private RFC1918 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
    127.0.0.0/8, 169.254.0.0/16) are always denied by CubeVS regardless of the
    user allowlist, so this demo uses a public domain instead of internal IPs.
"""

import os
from e2b.sandbox.commands.command_handle import CommandExitException
from e2b_code_interpreter import Sandbox
from env_utils import load_local_dotenv

load_local_dotenv()

template_id = os.environ["CUBE_TEMPLATE_ID"]

# Allow only example.com; everything else is blocked because
# allow_internet_access=False sets deny_out to 0.0.0.0/0.
ALLOWED_TARGETS = [
    "example.com",
]

with Sandbox.create(
    template=template_id,
    allow_internet_access=False,
    network={
        "allow_out": ALLOWED_TARGETS,
    },
) as sandbox:
    # Allowed domain is reachable
    result = sandbox.commands.run(
        "curl -s --max-time 5 https://example.com -o /dev/null -w '%{http_code}'",
        timeout=15,
    )
    print("allowed domain reachable:", result.stdout.strip())

    # Address outside allowlist is blocked
    blocked = False
    try:
        sandbox.commands.run(
            "curl -s --max-time 3 https://1.1.1.1 -o /dev/null",
            timeout=10,
        )
    except CommandExitException:
        blocked = True
    print("external IP blocked:", blocked)

    result = sandbox.commands.run("echo 'allowlist network ok'")
    print(result.stdout.strip())
