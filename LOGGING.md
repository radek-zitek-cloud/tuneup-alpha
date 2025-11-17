# Logging Guide

This guide provides comprehensive information about the structured logging system in TuneUp Alpha.

## Overview

TuneUp Alpha includes a robust structured logging system that provides:

- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Flexible Output**: Console, file, or both
- **Automatic Log Rotation**: Configurable size-based rotation
- **Structured Logging**: Optional JSON format for machine parsing
- **Correlation IDs**: Track related operations across the application
- **Audit Trail**: Comprehensive tracking of all DNS changes

## Configuration

Logging is configured through the `logging` section in your configuration file:

```yaml
logging:
  enabled: true           # Enable/disable logging
  level: INFO            # Log level: DEBUG, INFO, WARNING, ERROR
  output: console        # Output destination: console, file, both
  log_file: null         # Path to log file (required for file/both output)
  max_bytes: 10485760    # Max file size before rotation (10MB default)
  backup_count: 5        # Number of rotated files to keep
  structured: false      # Use JSON structured logging
```

## Log Levels

### DEBUG

Most verbose level, includes all operational details:

```yaml
logging:
  level: DEBUG
```

Use for:
- Development and troubleshooting
- Understanding application flow
- Debugging configuration issues

### INFO (Default)

General informational messages about application operations:

```yaml
logging:
  level: INFO
```

Use for:
- Production monitoring
- Tracking major operations
- Audit trail review

### WARNING

Important events that may require attention:

```yaml
logging:
  level: WARNING
```

Use for:
- Production environments with limited logging
- Focusing on potential issues

### ERROR

Only error conditions:

```yaml
logging:
  level: ERROR
```

Use for:
- Minimal logging overhead
- Critical error tracking only

## Output Destinations

### Console Only

Logs to standard output (useful for containerized deployments):

```yaml
logging:
  output: console
```

### File Only

Logs to a file with automatic rotation:

```yaml
logging:
  output: file
  log_file: /var/log/tuneup-alpha/app.log
```

### Both Console and File

Logs to both destinations simultaneously:

```yaml
logging:
  output: both
  log_file: /var/log/tuneup-alpha/app.log
```

## Log Rotation

Log files are automatically rotated when they reach the configured size:

```yaml
logging:
  max_bytes: 52428800    # 50MB
  backup_count: 10       # Keep 10 backup files
```

Files are rotated as:
- `app.log` (current)
- `app.log.1` (most recent backup)
- `app.log.2`
- ...
- `app.log.10` (oldest backup)

## Structured Logging

Enable JSON structured logging for machine parsing and analysis:

```yaml
logging:
  structured: true
```

### Human-Readable Format (Default)

```text
2025-11-17 20:14:10 INFO     tuneup_alpha.cli [c16249aa]: Showing configured zones
2025-11-17 20:14:10 DEBUG    tuneup_alpha.config [c16249aa]: Loading configuration from /tmp/config.yaml
```

### Structured JSON Format

```json
{
  "timestamp": "2025-11-17T20:14:10.391434+00:00",
  "level": "INFO",
  "logger": "tuneup_alpha.cli",
  "message": "Showing configured zones",
  "module": "cli",
  "function": "show",
  "line": 90,
  "correlation_id": "c16249aa-70b6-4d29-bff7-cdc7da93026b"
}
```

## Correlation IDs

Every CLI command automatically gets a unique correlation ID that tracks all related operations. This makes it easy to trace a complete operation across multiple log entries.

In human-readable format, the correlation ID appears in brackets (first 8 characters):

```text
2025-11-17 20:14:10 INFO     tuneup_alpha.cli [c16249aa]: Showing configured zones
2025-11-17 20:14:10 INFO     tuneup_alpha.config [c16249aa]: Successfully loaded configuration
```

In structured format, it's included as a field:

```json
{
  "correlation_id": "c16249aa-70b6-4d29-bff7-cdc7da93026b",
  ...
}
```

## Audit Trail

All DNS operations are logged with comprehensive metadata for audit purposes.

### Zone Changes

```json
{
  "level": "INFO",
  "logger": "tuneup_alpha.audit",
  "message": "Zone created: example.com",
  "audit_type": "zone_change",
  "action": "created",
  "zone_name": "example.com",
  "server": "ns1.example.com",
  "record_count": 3
}
```

### Record Changes

```json
{
  "level": "INFO",
  "logger": "tuneup_alpha.audit",
  "message": "Record updated: www.example.com A 192.0.2.1",
  "audit_type": "record_change",
  "action": "updated",
  "zone_name": "example.com",
  "record_label": "www",
  "record_type": "A",
  "record_value": "192.0.2.1",
  "ttl": 300
}
```

### nsupdate Execution

```json
{
  "level": "INFO",
  "logger": "tuneup_alpha.audit",
  "message": "nsupdate dry-run succeeded for example.com",
  "audit_type": "nsupdate_execution",
  "zone_name": "example.com",
  "dry_run": true,
  "success": true,
  "change_count": 3
}
```

## Production Deployment Examples

### Systemd Service with File Logging

```yaml
logging:
  enabled: true
  level: INFO
  output: file
  log_file: /var/log/tuneup-alpha/app.log
  max_bytes: 52428800    # 50MB
  backup_count: 20
  structured: true
```

### Docker Container with Console Logging

```yaml
logging:
  enabled: true
  level: INFO
  output: console
  structured: true  # For log aggregation systems
```

### Development Environment

```yaml
logging:
  enabled: true
  level: DEBUG
  output: both
  log_file: ./logs/dev.log
  structured: false  # Human-readable for development
```

## Log Analysis

### Viewing Logs

Human-readable format:

```bash
tail -f /var/log/tuneup-alpha/app.log
```

Structured JSON format:

```bash
# Pretty print JSON logs
tail -f /var/log/tuneup-alpha/app.log | jq .

# Filter by level
tail -f /var/log/tuneup-alpha/app.log | jq 'select(.level == "ERROR")'

# Filter by correlation ID
tail -f /var/log/tuneup-alpha/app.log | jq 'select(.correlation_id == "c16249aa-70b6-4d29-bff7-cdc7da93026b")'

# Extract audit logs only
tail -f /var/log/tuneup-alpha/app.log | jq 'select(.audit_type != null)'
```

### Searching Logs

```bash
# Find all zone changes
grep "zone_change" /var/log/tuneup-alpha/app.log

# Find failed operations
grep "success.*false" /var/log/tuneup-alpha/app.log

# Find operations for specific zone
grep "example.com" /var/log/tuneup-alpha/app.log
```

## Integration with Log Management Systems

### Splunk

Configure file output with structured JSON:

```yaml
logging:
  output: file
  structured: true
  log_file: /var/log/tuneup-alpha/app.log
```

Then configure Splunk to monitor the log file.

### ELK Stack (Elasticsearch, Logstash, Kibana)

Use Filebeat to ship logs to Logstash:

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/tuneup-alpha/app.log
  json.keys_under_root: true
  json.add_error_key: true
```

### CloudWatch Logs

Use the CloudWatch Logs agent to ship logs:

```yaml
logging:
  output: file
  structured: true
  log_file: /var/log/tuneup-alpha/app.log
```

### Prometheus/Grafana

While TuneUp Alpha doesn't export metrics directly, you can use log-based metrics extractors like `mtail` to convert audit logs into Prometheus metrics.

## Troubleshooting

### Logs Not Appearing

1. Check that logging is enabled:

   ```yaml
   logging:
     enabled: true
   ```

2. Verify log level is appropriate:

   ```yaml
   logging:
     level: DEBUG  # Most verbose
   ```

3. Check file permissions if using file output:

   ```bash
   ls -l /var/log/tuneup-alpha/
   ```

### Log Rotation Not Working

1. Verify `max_bytes` and `backup_count` are set:

   ```yaml
   logging:
     max_bytes: 10485760
     backup_count: 5
   ```

2. Check disk space availability

3. Verify write permissions to the log directory

### Performance Impact

If logging is impacting performance:

1. Reduce log level to WARNING or ERROR
2. Use file output instead of console
3. Disable structured logging if not needed
4. Increase `max_bytes` to reduce rotation frequency

## Best Practices

1. **Use INFO level for production**: Provides good visibility without excessive overhead
2. **Enable structured logging for production**: Makes log analysis much easier
3. **Use both console and file output during initial deployment**: Helps catch issues
4. **Set appropriate rotation sizes**: 50MB per file is a good starting point
5. **Keep enough backup files**: 10-20 backups provide good history without excessive disk usage
6. **Use correlation IDs for troubleshooting**: Track operations across the system
7. **Monitor audit logs regularly**: Review DNS changes for security and compliance

## Security Considerations

1. **Log file permissions**: Ensure log files are not world-readable if they contain sensitive information
2. **Log rotation**: Old logs may contain historical data - consider retention policies
3. **Sensitive data**: The logging system does not log secrets or key file contents
4. **Audit trail**: All DNS changes are logged for compliance and security review

## Performance Characteristics

- **Console logging**: Minimal overhead (~1-2% CPU)
- **File logging**: Slightly higher overhead (~2-5% CPU) due to disk I/O
- **Structured logging**: Negligible additional overhead (~<1%)
- **Log rotation**: Brief pause when rotation occurs (typically <100ms)

## Future Enhancements

Planned logging improvements include:

- Metrics export (Prometheus format)
- Remote syslog support
- Custom log formatters
- Log level configuration per module
- Real-time log streaming API
