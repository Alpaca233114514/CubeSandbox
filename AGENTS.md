# AGENTS Policy



## AI-Generated Code Policy

AI agents MUST NOT add Signed-off-by tags. Only humans can legally certify the Developer Certificate of Origin (DCO). The human submitter is responsible for:

- Reviewing all AI-generated code
- Ensuring compliance with licensing requirements
- Adding their own Signed-off-by tag to certify the DCO
- Taking full responsibility for the contribution

**MUST FOLLOW THIS**: When performing a `git commit` or submitting a GitHub PR, the commit message or PR description MUST include the following tag — this is required so that agent contributions remain visible and attributable in the project history:

- If the work was **human-assisted by an AI agent**, include:

```
Assisted-by: AGENT_NAME:MODEL_VERSION
```

- If the commit/PR was **fully completed autonomously by an AI agent** (without human authoring), include instead:

```
Autonomously-by: AGENT_NAME:MODEL_VERSION
```

Where:
- `AGENT_NAME` is the name of the AI tool or framework
- `MODEL_VERSION` is the specific model version used



## WSL2 Local Test Environment

This section documents how to run CubeSandbox on a local WSL2 instance for development and SDK demo validation. The changes are guarded as a WSL2 compatibility layer and must not alter the normal Linux control path.

### Prerequisites

- Windows 11 WSL2 with a Linux distribution that has `systemd` support.
- WSL `systemd=true` enabled in `/etc/wsl.conf`:
  ```ini
  [boot]
  systemd=true
  ```
- Run inside WSL as root (many components require creating network devices and mounting eBPF maps).

### 1. Fix bpffs auto-mount

The network agent pins eBPF maps under `/sys/fs/bpf`. On WSL2 this is not mounted as `bpf` by default, causing a fatal error. Add a systemd drop-in:

```bash
mkdir -p /usr/local/services/cubetoolbox/scripts/systemd
mkdir -p /etc/systemd/system/cube-sandbox-network-agent.service.d

cat >/usr/local/services/cubetoolbox/scripts/systemd/ensure-bpffs.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /sys/fs/bpf
if [ "$(stat -fc %T /sys/fs/bpf 2>/dev/null || true)" != "bpf" ]; then
  mount -t bpf bpf /sys/fs/bpf
fi
EOF

chmod 0755 /usr/local/services/cubetoolbox/scripts/systemd/ensure-bpffs.sh

cat >/etc/systemd/system/cube-sandbox-network-agent.service.d/10-bpffs.conf <<'EOF'
[Service]
ExecStartPre=/usr/bin/bash /usr/local/services/cubetoolbox/scripts/systemd/ensure-bpffs.sh
EOF

systemctl daemon-reload
systemctl restart cube-sandbox-network-agent.service
```

Verify with `curl -sS http://127.0.0.1:19090/healthz` returning `ok`.

### 2. Build the WSL2-compatible Cubelet

The following source changes form the WSL2 compatibility layer:

- `Cubelet/pkg/nsenter/nsenter.c`: when `NEED_SET_MNT=wsl2`, skip `setns` into the host mount namespace.
- `Cubelet/cmd/cubelet/main.go`: add `isWSL2()`, `newCubeMntWSL2()` and `ensureWSL2Mounts()` to re-execute the cubelet inside a private mount namespace.
- `Cubelet/network/plugin_tap.go`: retry gateway neighbour resolution up to 5 times and accept `REACHABLE | STALE | PERMANENT | NOARP` states.

Build and install:

```bash
cd Cubelet
make build
install -m 0755 build/cubelet /usr/local/services/cubetoolbox/Cubelet/bin/cubelet
systemctl restart cube-sandbox-cubelet.service
```

Verify with:

```bash
systemctl is-active cube-sandbox-cubelet.service
cubemastercli -a 127.0.0.1 -p 8089 node list
```

`HOST_STATUS` should be `RUNNING` and `HEALTHY` should be `true`.

### 3. DNS setup for `*.cube.app`

SDK traffic reaches proxies via `*.cube.app`. Local HTTPS uses a self-signed certificate, and the domain must resolve through the WSL host.

```bash
mkdir -p /etc/systemd/resolved.conf.d
cat >/etc/systemd/resolved.conf.d/cube.conf <<'EOF'
[Resolve]
DNSStubListener=yes
EOF

systemctl restart systemd-resolved
ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
```

To survive WSL restart, also add to `/etc/wsl.conf`:

```ini
[network]
generateResolvConf=false
```

Then fully restart WSL once.

### 4. Trust the local mkcert root CA

The proxy serves a certificate signed by a local mkcert root. Export and trust it:

```bash
# Example path; adjust to where the root CA was generated.
export SSL_CERT_FILE=/root/.local/share/mkcert/rootCA.pem
```

For Python SDK demos, put this in `examples/code-sandbox-quickstart/.env` (see next section).

### 5. Register a template

```bash
cubemastercli -a 127.0.0.1 -p 8089 tpl create-from-image \
  --image cube-sandbox-cn.tencentcloudcr.com/cube-sandbox/sandbox-code:latest \
  --writable-layer-size 1G \
  --expose-port 49999 \
  --expose-port 49983 \
  --probe 49983 \
  --probe-path /health
```

Note: use port `49983 /health` for the probe. Port `49999` is the Jupyter kernel gateway and will connection-refuse until the sandbox boots.

### 6. Configure SDK demo environment

```bash
apt-get install -y python3-pip python3-venv
python3 -m venv /root/csb-sdk-venv
source /root/csb-sdk-venv/bin/activate
pip install -r examples/code-sandbox-quickstart/requirements.txt
pip install -r examples/e2b-dev-sidecar/requirements.txt
```

Create `examples/code-sandbox-quickstart/.env`:

```ini
E2B_API_URL=http://127.0.0.1:3000
CUBE_TEMPLATE_ID=<template-id-from-step-5>
SSL_CERT_FILE=/root/.local/share/mkcert/rootCA.pem
```

### 7. Run demos

Standard demos that only use `commands.run()` work immediately:

```bash
cd examples/code-sandbox-quickstart
python cmd.py
python create.py
python read.py
```

Demos that call `run_code()` need to wait for the kernel gateway on `49999` to be ready. Use the WSL2 compatibility variants:

```bash
python exec_code_wsl.py
python pause_wsl.py
```

These import `wsl_compat.wait_for_code_interpreter()` to poll `https://49999-<sandbox-id>.cube.app/health` before invoking the interpreter.

Network policy demos can be run for smoke testing:

```bash
python network_denylist.py
python network_allowlist.py
python network_no_internet.py
```

Notes on network policy behavior:

- Private RFC1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`) are always denied by CubeVS, regardless of any user `allow_out` entries.
- `allow_out` supports both CIDR/IP targets and domain targets. Domain targets trigger DNS learning and automatically allow the resolved IPs.
- The original `network_no_internet.py` detection logic was fixed to avoid a false negative caused by combining `curl -w '%{http_code}'` with `|| echo`.
- The original `network_allowlist.py` was updated to use a public domain target (`example.com`) instead of private CIDRs, which are always denied.

### 8. Keep WSL alive

Long-running services stop when the last WSL session exits. To keep the environment alive between Windows tool calls, either enable a keepalive service inside WSL:

```bash
cat >/etc/systemd/system/wsl-keepalive.service <<'EOF'
[Unit]
Description=Keep WSL2 alive

[Service]
Type=simple
ExecStart=/bin/sleep infinity
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable --now wsl-keepalive.service
```

Or hold a foreground WSL process open from Windows:

```powershell
wsl -u root -- bash -c "while true; do sleep 30; done"
```

### What changed

New/updated files specific to WSL2 compatibility:

- `Cubelet/pkg/nsenter/nsenter.c`
- `Cubelet/cmd/cubelet/main.go`
- `Cubelet/network/plugin_tap.go`
- `examples/code-sandbox-quickstart/wsl_compat.py`
- `examples/code-sandbox-quickstart/exec_code_wsl.py`
- `examples/code-sandbox-quickstart/pause_wsl.py`

Also fixed demo detection/selection issues discovered during WSL2 validation:

- `examples/code-sandbox-quickstart/network_no_internet.py`
- `examples/code-sandbox-quickstart/network_allowlist.py`

None of the above change the normal Linux execution path except under WSL2 detection or via explicit helper scripts.



## CubeSandbox Project Overview

CubeSandbox is a MicroVM-based code sandbox platform. It registers container images as **templates**, then launches isolated MicroVM sandboxes from those templates. Each sandbox gets its own TAP network interface, eBPF/XDP-based egress policy, and SDK access via Python/Go clients.

### Core components

| Component | Role | Typical host |
|-----------|------|--------------|
| `CubeMaster` | Control plane: template management, sandbox scheduling, node registry | Master node / K8s |
| `Cubelet` | Node agent: creates/destroys MicroVMs, attaches network, reports health | Every worker node |
| `network-agent` | Manages TAP devices, SNAT, eBPF maps (`allow_out_v2`, `deny_out`, `dns_allow`) | Every worker node |
| `CubeNet` | eBPF/XDP data plane (`cubevs`) | Loaded by network-agent |
| `CubeProxy` | Reverse proxy for `*.cube.app` sandbox domains | Edge / LB |
| `hypervisor` | MicroVM VMM (Firecracker/Cloud Hypervisor fork) | Worker node |
| `agent` / `CubeShim` | In-guest agent and containerd shim | Inside MicroVM |
| `CubeAPI` | Public API gateway | Master node |

### Key source locations

- Cubelet: `Cubelet/`
- Network agent: `network-agent/`
- eBPF data plane: `CubeNet/cubevs/` and `CubeNet/src/*.bpf.c`
- SDK demos: `examples/code-sandbox-quickstart/`
- One-click deploy: `deploy/one-click/`



## Production Deployment

For production, use `deploy/one-click/` or a custom orchestration on physical machines/VMs. WSL2 is **not** a supported production environment.

### one-click path

```bash
cd deploy/one-click
# Read README.md / README_zh.md, fill in env, then:
./install.sh
```

This typically installs and wires together:

- CubeMaster + MySQL/Redis
- Cubelet + network-agent
- CubeProxy + CubeAPI
- Hypervisor binary and guest image

### Production configuration checklist

| Area | What to configure |
|------|-------------------|
| Network | TAP bridge, SNAT IP pool, node DNS, `*.cube.app` certificates |
| Images | Push sandbox images to an accessible registry |
| Templates | `cubemastercli tpl create-from-image ...` for each image |
| Certificates | Real CA or internal trust chain for `*.cube.app` |
| Storage | Snapshot store, writable-layer backend |
| Monitoring | network-agent healthz, Cubelet metrics, Master API logs |

### Register a production template

```bash
cubemastercli -a <master-ip> -p 8089 tpl create-from-image \
  --image your-registry.example.com/your-sandbox:latest \
  --writable-layer-size 10G \
  --expose-port 49999 \
  --expose-port 49983 \
  --probe 49983 \
  --probe-path /health
```

### Use the production SDK

```bash
export E2B_API_URL=https://your-cube-api.example.com
export CUBE_TEMPLATE_ID=<tpl-xxx>
export SSL_CERT_FILE=/path/to/trusted-ca.pem

python your_script.py
```



## Daily Operation Commands

### Check services

```bash
systemctl is-active cube-sandbox-network-agent cube-sandbox-cubelet
curl -sS http://127.0.0.1:19090/healthz
```

### Master CLI

```bash
# Nodes
cubemastercli -a 127.0.0.1 -p 8089 node list

# Templates
cubemastercli -a 127.0.0.1 -p 8089 tpl list
cubemastercli -a 127.0.0.1 -p 8089 tpl delete --template-id <id>

# Sandboxes
cubemastercli -a 127.0.0.1 -p 8089 sandbox list
```

### Logs

```bash
journalctl -u cube-sandbox-cubelet -f
journalctl -u cube-sandbox-network-agent -f
```

### Inspect network state

```bash
# TAP devices created by Cubelet/network-agent
ip link show | grep '^[0-9]*: z'

# Pinned eBPF maps
ls /sys/fs/bpf/

# Active eBPF programs
bpftool prog show
bpftool map show
```



## Development & Debug Workflow

### Modifying Cubelet

```bash
cd Cubelet
make build
install -m 0755 build/cubelet /usr/local/services/cubetoolbox/Cubelet/bin/cubelet
systemctl restart cube-sandbox-cubelet.service
```

Relevant test packages:

```bash
cd Cubelet
go test ./network/... ./cmd/cubelet/...
```

### Modifying network policy

Source files:

- `CubeNet/cubevs/netpolicy.go` — Go side: map management, allow/deny/DNS logic
- `CubeNet/src/mvmtap.bpf.c` — BPF side: egress policy enforcement (`check_net_policy`)
- `Cubelet/network/plugin_tap.go` — Cubelet → network-agent request translation

After changing BPF C code, rebuild and restart `network-agent`. After changing Go code in `CubeNet/`, rebuild `network-agent` (and Cubelet if the API changed).

### Modifying SDK demos

Files under `examples/code-sandbox-quickstart/` can be edited directly. No service restart is required; just re-run the demo script.

### Common failure patterns

| Symptom | Likely cause | Check |
|---------|--------------|-------|
| `network-agent` healthz fails | `/sys/fs/bpf` not mounted | `stat -fc %T /sys/fs/bpf` |
| Cubelet fails to start | mount namespace / gateway MAC issue | `journalctl -u cube-sandbox-cubelet` |
| Sandbox `run_code()` 502 | kernel gateway not ready yet | poll `49999-<sid>.cube.app/health` |
| DNS timeout in sandbox | `allow_internet_access=false` blocks DNS | use domain `allow_out` or allow DNS server CIDR |
| Private IP unreachable | CubeVS always denies RFC1918 ranges | use public IPs/domains in allowlists |
