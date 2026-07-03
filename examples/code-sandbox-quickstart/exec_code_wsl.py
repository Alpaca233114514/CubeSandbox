# Copyright (c) 2024 Tencent Inc.
# SPDX-License-Identifier: Apache-2.0

"""WSL2-friendly variant of exec_code.py.

The official sandbox-code image starts an envd agent immediately, but the
Jupyter kernel gateway on :49999 can take a few seconds to become ready after
the MicroVM boots. This script polls the gateway /health endpoint before
calling run_code(), so it works reliably on a fresh local WSL2 deployment.
"""

import os

from e2b_code_interpreter import Sandbox
from env_utils import load_local_dotenv
from wsl_compat import wait_for_code_interpreter

load_local_dotenv()

template_id = os.environ["CUBE_TEMPLATE_ID"]

python_code = """
print("hello cube")
x = sum(range(1, 101))
print(f"sum(1..100) = {x}")
"""

with Sandbox.create(template=template_id) as sandbox:
    wait_for_code_interpreter(sandbox)
    print(sandbox.run_code(python_code, on_stdout=lambda data: print(data)))
