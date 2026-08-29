# Secure CI Demo

A Rust API project demonstrating secure software development practices through automated CI security checks.

## Project Overview

This project demonstrates how security checks become part of a CI pipeline during development.

Technology used:

- Rust
- Axum
- SQLite
- SQLx
- GitHub Actions
- Semgrep
- Gitleaks
- Git

The CI pipeline performs:

1. Rust compilation checks
2. Automated tests
3. Semgrep static application security testing
4. Gitleaks secret scanning

## Application

The application is a small Rust HTTP API with:

- Home endpoint
- Health endpoint
- Note creation
- Note retrieval and search
- SQLite database integration
- Input validation

Run locally with:

```powershell
cargo run
```

The server runs at:

`http://127.0.0.1:3000`

Health check:

```powershell
curl.exe http://127.0.0.1:3000/health
```

Expected response:

```text
OK
```

## Testing

The API integration tests verify the home and health endpoints.

The final local test run completed with:

```text
2 passed, 0 failed
```

Run:

```powershell
cargo test
```

## CI Pipeline

The GitHub Actions workflow is stored in `.github/workflows/ci.yml`.

The workflow runs for pushes to `main` and pull requests targeting `main`.

### Build and Test

The job:

- Checks out the repository
- Installs stable Rust
- Runs `cargo check`
- Runs `cargo test`

### Semgrep SAST

Semgrep uses the custom rules in:

```text
security/semgrep/rules.yml
```

The workflow uses `--error`, so blocking findings fail the job.

The custom demonstration rule detects unsafe SQL construction through Rust format strings.

Example:

```rust
let query = format!(
    "SELECT * FROM notes WHERE title = '{}'",
    title
);
```

Semgrep detected this as a possible SQL injection.

### Gitleaks

Gitleaks runs through the CLI in GitHub Actions.

A deterministic custom rule named `demo-api-key` was used for the planted-secret demonstration.

The planted value was:

```text
DEMO_API_KEY=sk-demo-1234567890abcdef1234567890abcdef
```

Gitleaks detected the planted secret and failed the security job.

## Security Demonstrations

### Planted Secret

A separate demonstration branch contained an intentional secret.

Expected result:

```text
Build and Test       PASS
Semgrep SAST         PASS
Gitleaks              FAIL
```

Gitleaks reported:

```text
RuleID: demo-api-key
File: security/demo_secret.txt
Line: 1
```

The planted secret was kept out of the clean `main` branch.

### Planted Semgrep Vulnerability

A separate demonstration branch contained intentionally vulnerable Rust code.

Expected result:

```text
Build and Test       PASS
Gitleaks              PASS
Semgrep SAST         FAIL
```

Semgrep reported:

```text
security.semgrep.rust-sql-format-string
```

The finding identified possible SQL injection caused by constructing SQL with a format string.

The vulnerable demonstration file was kept out of the clean `main` branch.

## Blocking Versus Warning Rules

High-confidence security findings are treated as blocking findings.

Examples:

- Secrets detected by Gitleaks
- SQL injection detected by the custom Semgrep rule

A blocking finding fails CI and prevents a clean merge until the issue is addressed.

Warning rules suit lower-confidence or lower-risk findings. They provide visibility without stopping normal development.

The demonstrated rules focus on high-confidence security problems. This reduces unnecessary CI noise.

## Noise Versus Coverage

Security automation requires a balance between coverage and noise. A scanner needs enough rules to identify meaningful vulnerabilities, while excessive low-confidence findings can create alert fatigue.

This project uses blocking checks for high-confidence security risks. Gitleaks blocks when a secret is detected. Semgrep blocks when the custom SQL injection pattern is detected. Both demonstrations produced findings tied to specific files and lines.

The custom Semgrep rule focuses on unsafe SQL construction rather than broad coding patterns. This keeps the rule focused on a security weakness with a clear remediation path. The Gitleaks configuration includes a deterministic demonstration rule for the planted API key.

The project separates demonstration branches from `main`. This allows the repository to demonstrate security controls against known problems while keeping the main development branch clean.

Lower-risk rules are better suited to warning status. Such rules report potential issues while allowing development to continue. Blocking should focus on findings with enough confidence and impact to justify stopping the pipeline.

This approach provides strong detection for critical threats while limiting unnecessary interruptions during normal development.

## Secret Handling

Local SQLite database files must not enter version control.

The `.gitignore` file contains:

```text
notes.db
```

Demo secrets exist only for security-control demonstrations and do not represent real credentials.

## GitHub Actions Security

Third-party GitHub Actions are pinned to full commit SHAs.

Examples:

```text
actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
```

```text
dtolnay/rust-toolchain@6c977a6ca4077a0ceb28ffbe03f59d46e9ac8772
```

SHA pinning reduces the risk associated with mutable action tags and branches.

## Local Security Commands

Semgrep:

```powershell
semgrep scan --config security/semgrep/rules.yml
```

Gitleaks:

```powershell
gitleaks dir . --config .gitleaks.toml --no-banner
```

Tests:

```powershell
cargo test
```

## Project Structure

```text
secure-ci-demo/
├── .github/
│   └── workflows/
│       └── ci.yml
├── security/
│   └── semgrep/
│       └── rules.yml
├── src/
│   ├── database.rs
│   ├── handlers.rs
│   ├── lib.rs
│   ├── main.rs
│   ├── models.rs
│   └── routes.rs
├── tests/
│   └── api_tests.rs
├── Cargo.toml
├── Cargo.lock
└── .gitignore
```

## Development Workflow

```text
Write code
   ↓
Run tests
   ↓
Run Semgrep
   ↓
Run Gitleaks
   ↓
Commit changes
   ↓
Push branch
   ↓
GitHub Actions
   ↓
Review security results
   ↓
Merge clean changes
```

## AI Usage

AI assistance supported the development process.

AI was used to:

- Brainstorm the project structure
- Plan CI security stages
- Troubleshoot Rust compilation and runtime issues
- Troubleshoot Git branches and commits
- Configure Semgrep rules
- Configure Gitleaks scanning
- Debug GitHub Actions failures
- Explain security scanner findings
- Draft project documentation

Generated guidance was reviewed and tested through local commands and GitHub Actions before changes were accepted.

## Evidence

Main repository:

https://github.com/KahlubDev/secure-ci-demo

Planted secret PR:

https://github.com/KahlubDev/secure-ci-demo/pull/1

Planted Semgrep vulnerability PR:

https://github.com/KahlubDev/secure-ci-demo/pull/3

## What I learnt

The project helped me learn:
- Automated Rust build checks
- Automated Rust tests
- Custom Semgrep security detection
- Gitleaks secret detection
- Blocking security findings
- Security-focused GitHub Actions
- SHA-pinned third-party actions
- Separation of vulnerable demonstrations from the clean main branch
