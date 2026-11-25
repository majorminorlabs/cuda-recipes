# Publication checks

Enable the repository hooks after cloning:

```sh
git config core.hooksPath .githooks
```

The commit hook checks staged paths and complete staged file contents. The push hook checks every proposed commit, its metadata, and its file contents, including gzip evidence. Both reject machine paths, private records, personal contact details, allocation identifiers, vendor wording, and credential-shaped values. Localhost listeners, documentation addresses, package versions, and logger timestamps are checked as technical data.

Keep original evidence, operational session notes, drafts, and private provenance in the owning recipe's ignored `_private/` directory. Preserve frozen benchmark prompts and upstream credits. A reviewed content exception must name an exact path, SHA-256, rule, and justification; editing that file invalidates the exception. Never add an exception for a real secret.

Run `python3 scripts/check_sensitive.py staged` to check the index or `python3 scripts/check_sensitive.py history` to audit all reachable history. Check output lists paths and rule names without echoing sensitive values.

Sanitized artifacts differ from private originals. Current checksum manifests describe the published sanitized files; historical manifests can still describe the original evidence and must not be treated as checksums of redacted bytes.
