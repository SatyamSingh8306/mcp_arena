# 🔒 Security Policy

## ✅ Supported Versions

We release security updates for the following versions of mcp_arena:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |
| < 0.1   | :x:                |

## 🚨 Reporting a Vulnerability

We take the security of mcp_arena seriously. If you discover a security vulnerability, please follow these steps:

### 1. **Do Not** Open a Public Issue

Please do not report security vulnerabilities through public GitHub issues. This could put all users at risk.

### 2. 📧 Report Privately

Send an email to [satyamsingh8306@gmail.com](mailto:satyamsingh8306@gmail.com) with:

- **Subject Line:** "SECURITY: [Brief Description]"
- **Description:** A clear description of the vulnerability
- **Impact:** What could an attacker achieve?
- **Steps to Reproduce:** Detailed steps to reproduce the issue
- **Affected Versions:** Which versions are affected?
- **Suggested Fix:** (Optional) If you have suggestions

### 3. ⏳ What to Expect

- **Initial Response:** Within 48 hours, we'll acknowledge receipt of your report
- **Investigation:** We'll investigate the issue and determine its severity
- **Updates:** We'll keep you informed of our progress
- **Fix Timeline:** Critical issues will be addressed within 7 days; others within 30 days
- **Credit:** With your permission, we'll credit you in the security advisory

## 🔐 Security Best Practices

When using mcp_arena, we recommend:

### 🔑 API Keys and Tokens

- **Never commit** API keys, tokens, or credentials to version control
- Use **environment variables** for sensitive data
- Rotate credentials regularly
- Use different credentials for development and production

```python
import os

# Good: Use environment variables
github_token = os.getenv("GITHUB_TOKEN")
server = GithubMCPServer(token=github_token)

# Bad: Hardcoded credentials
server = GithubMCPServer(token="ghp_xxxxxxxxxxxxx")
```

### ✅ Input Validation

- Always validate user inputs before processing
- Use type hints and validation for tool parameters
- Sanitize inputs that interact with external systems

### 📦 Dependencies

- Keep mcp_arena and its dependencies up to date
- Review security advisories for dependencies
- Use tools like `pip-audit` or `safety` to check for vulnerabilities

```bash
# Check for known vulnerabilities
pip install pip-audit
pip-audit

# Or using safety
pip install safety
safety check
```

### 🌐 Network Security

- Use HTTPS for all external API calls
- Verify SSL certificates
- Implement rate limiting to prevent abuse
- Use timeouts for network requests

### 🤖 Agent Security

- Limit agent permissions to necessary operations only
- Implement proper error handling to avoid information leakage
- Log security-relevant events
- Validate and sanitize agent outputs before use

## 📢 Disclosure Policy

When a security issue is reported:

1. We'll investigate and validate the issue
2. Develop a fix and test it thoroughly
3. Prepare a security advisory
4. Release a patched version
5. Publish the security advisory with:
   - Description of the vulnerability
   - Affected versions
   - Fixed versions
   - Mitigation steps
   - Credit to the reporter (with permission)

## 🔄 Security Updates

Security updates are released as:
- **Patch versions** for minor security issues (e.g., 0.2.1 → 0.2.2)
- **Minor versions** for moderate issues (e.g., 0.2.x → 0.3.0)
- **Emergency patches** for critical vulnerabilities

Subscribe to our [GitHub releases](https://github.com/SatyamSingh8306/mcp_arena/releases) to stay informed about security updates.

## ⚠️ Known Security Considerations

### 🤖 LLM Integration

When integrating with Large Language Models:
- Be aware that LLMs can be prompt-injected
- Validate and sanitize LLM outputs
- Don't grant unrestricted system access to LLM-controlled agents
- Implement appropriate guardrails and monitoring

### 🔧 Tool Execution

- Tools execute with the permissions of the running process
- Limit file system access where possible
- Be cautious with tools that modify system state
- Implement proper authentication and authorization

### 🖥️ MCP Server Exposure

- MCP servers should not be exposed directly to the internet without authentication
- Use secure transport mechanisms (TLS/SSL)
- Implement proper access controls
- Monitor for unusual activity

## 📚 Security Resources

- **OpenSSF Best Practices:** https://bestpractices.coreinfrastructure.org/
- **Python Security:** https://python.readthedocs.io/en/latest/library/security_warnings.html
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/

## 🎖️ Acknowledgments

We'd like to thank the following security researchers for responsibly disclosing vulnerabilities:

*(None yet - be the first!)*

---

## 🔗 Related Documentation

- 📖 **[README](README.md)** - Project overview and quick start
- 🤝 **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- ⚖️ **[Code of Conduct](CODE_OF_CONDUCT.md)** - Community guidelines

---

Thank you for helping keep mcp_arena and its users safe! 🔒
