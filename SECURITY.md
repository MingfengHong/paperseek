# Security Policy

## Supported Versions

PaperSeek is currently in alpha. Security fixes target the latest `main` branch and the latest published package version, if any.

## Reporting a Vulnerability

Please report security issues privately to:

```text
hongmingfeng24@mails.ucas.ac.cn
```

Do not open a public issue for leaked credentials, account access problems, or vulnerabilities involving API keys.

## Secrets Handling

- Web UI session values are temporary and are not written to disk by PaperSeek.
- CLI user configuration is stored locally and masks secrets when listed.
- `.env`, `.env.*`, user config files, build output, and caches should not be committed.
- Agent Skill files must not contain real API keys.

PaperSeek does not bypass paywalls, download protected PDFs, or manage publisher/database login sessions.
