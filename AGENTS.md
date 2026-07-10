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

## Cursor Cloud specific instructions

These notes cover non-obvious caveats for developing in the Cursor Cloud VM. For full deployment/build docs see `README.md`, `CONTRIBUTING.md`, `docs/guide/dev-environment.md`, and the root `Makefile`.

### Environment limitations (important)
- **No `/dev/kvm` and no Docker** in the Cloud VM. The core product (booting hardware-isolated MicroVM sandboxes) **cannot run end-to-end** here — the data plane (`Cubelet`, `CubeShim`, `hypervisor`, `CubeVS`/`network-agent`) needs KVM, and the standard `make builder-image` / `make all` build path needs Docker. Use a bare-metal / nested-virt host (see `docs/guide/`) for the full stack.
- What **does** run in the Cloud VM: the `web/` dashboard (with a mock backend), the `CubeAPI` Rust binary, and the Go/Python SDK test suites.

### Web dashboard (`web/`) — primary runnable app
- Dev server: `npm run dev --prefix web` (or `make web-dev`), served on `http://localhost:5173`. Lint: `npm run lint --prefix web` (`tsc -b --noEmit`). Build: `npm run build --prefix web`.
- To run **without a backend**, enable the MSW mock: start with `VITE_USE_MOCK=1` (or append `?mock=1` to the URL). In dev, `/cubeapi` is proxied to a backend on `:3000` that is not running.
- Non-obvious auth gotcha: `/auth/session` is **not** mocked, so the `AuthGuard` redirects to `/login` (login is also unmocked). To browse the mocked UI, set `sessionStorage.setItem('cube.authStatus','allowed')` (and `localStorage.setItem('cube.useMock','1')`) in the browser console, then navigate to `/`.

### CubeAPI (Rust)
- `CubeAPI/rust-toolchain.toml` pins Rust **1.85**; the VM's default `rustc` (1.83) fails to build it (a dependency requires `edition2024`). `rustup` is installed and auto-selects 1.85 when you run `cargo` **from inside `CubeAPI/`** (or run `rustup default 1.85`).
- `cargo run -- --export-openapi <file>` runs the binary and regenerates the OpenAPI contract; this backs `npm run api:sync` in `web/`.

### SDK tests
- Go: `cd sdk/go && go test ./...`. Integration tests are behind `//go:build integration` and are skipped by default (they need a live CubeAPI).
- Python: `sdk/python` — run `pytest -m "not e2e"` (the `e2e` marker needs a live CubeAPI). Creating a venv requires the `python3.12-venv` apt package.
