# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | ✅ Active          |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in
agentix, please **do not** open a public issue. Instead, send a private
report to **security@agentix.dev**.

Please include the following details in your report:

- A clear description of the vulnerability
- Steps to reproduce the issue
- The affected version(s) and environment
- Any potential impact or exploit scenarios

You should receive a response within **48 hours**. If you don't, please
follow up to ensure we received your message.

## Disclosure Policy

Once a vulnerability is confirmed:

1. We will work on a fix and verify it resolves the issue.
2. We will release a patched version and notify you.
3. After the fix is published, we will publicly disclose the vulnerability
   with credit to the reporter (unless anonymity is requested).

We ask that you refrain from public disclosure until a fix is released.

## Scope

The following are **in scope**:
- The agentix Python package (`agentix/` directory)
- CLI interface (`agentix.cli`)
- Build and packaging configuration

The following are **out of scope**:
- Third-party dependencies (report to their respective projects)
- Infrastructure of agentix.dev or GitHub repositories
- End-user applications built with agentix
