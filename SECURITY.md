# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within the UAV Ground Control Station Simulator, please do not disclose it publicly. Report it directly to the project maintainers by opening a private security advisory on GitHub or emailing the repository owner.

### Security Best Practices Implemented
- **No Remote Code Execution**: Incoming UDP payloads are parsed strictly as standard JSON. No `eval()`, `exec()`, or pickle serialization is permitted.
- **Strict Schema & Range Validation**: All inbound network payloads undergo mandatory schema and physical boundary checks before updating internal telemetry state.
- **Endpoint Binding**: Configurable UDP socket binding to prevent unintended exposure to external networks unless explicitly configured.
- **Data Sanitization**: Logs exclude sensitive network stack headers or unvetted binary data.
