# TuneUp Alpha Administrator Manual

Version 0.2.0

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Installation and Deployment](#installation-and-deployment)
4. [DNS Server Configuration](#dns-server-configuration)
5. [Security Configuration](#security-configuration)
6. [Logging and Monitoring](#logging-and-monitoring)
7. [Backup and Recovery](#backup-and-recovery)
8. [Performance Tuning](#performance-tuning)
9. [Multi-User Deployments](#multi-user-deployments)
10. [CI/CD Integration](#cicd-integration)
11. [Troubleshooting and Diagnostics](#troubleshooting-and-diagnostics)
12. [Maintenance Procedures](#maintenance-procedures)
13. [Security Best Practices](#security-best-practices)
14. [Disaster Recovery](#disaster-recovery)

## Introduction

### Purpose of This Manual

This manual provides comprehensive guidance for system administrators deploying, configuring, and maintaining TuneUp Alpha in production environments. It covers installation, security, monitoring, backup, and operational procedures.

### Intended Audience

This manual is written for:

- System administrators deploying TuneUp Alpha
- DevOps engineers integrating DNS management into CI/CD pipelines
- IT security personnel configuring access controls
- Operations teams responsible for monitoring and maintenance

### Prerequisites

Administrators should have:

- Strong understanding of DNS concepts and operations
- Experience with Linux/Unix system administration
- Familiarity with YAML configuration formats
- Knowledge of TSIG authentication and BIND utilities
- Understanding of security best practices

### Related Documentation

- **USER_MANUAL.md**: End-user guide for daily operations
- **ARCHITECTURE.md**: Technical architecture and component details
- **LOGGING.md**: Comprehensive logging configuration guide
- **README.md**: Quick start and feature overview

## System Architecture

### Component Overview

TuneUp Alpha consists of several key components:

```
┌─────────────────────────────────────────────────────────┐
│                    TuneUp Alpha                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐   │
│  │   CLI    │  │   TUI    │  │  Config Repository │   │
│  │ (Typer)  │  │(Textual) │  │  (YAML)            │   │
│  └────┬─────┘  └────┬─────┘  └──────┬─────────────┘   │
│       │             │               │                   │
│       └─────────────┴───────────────┘                   │
│                     │                                    │
│       ┌─────────────┴──────────────┐                   │
│       │                            │                   │
│  ┌────▼─────┐  ┌──────────┐  ┌───▼────────┐          │
│  │ nsupdate │  │DNS State │  │DNS Lookup  │          │
│  │ Client   │  │Validator │  │ Utilities  │          │
│  └────┬─────┘  └────┬─────┘  └────────────┘          │
│       │             │                                    │
└───────┼─────────────┼────────────────────────────────────┘
        │             │
        │             │  DNS Queries (dig)
        │             ▼
        │        ┌──────────┐
        │        │   DNS    │
        │        │  Server  │
        │        └──────────┘
        │
        │  nsupdate + TSIG
        ▼
   ┌──────────┐
   │   DNS    │
   │  Server  │
   └──────────┘
```

### Runtime Requirements

**Hardware Requirements:**

- **CPU**: 1 core minimum, 2+ cores recommended
- **RAM**: 256 MB minimum, 512 MB recommended
- **Disk**: 100 MB for application, plus space for logs
- **Network**: Connectivity to DNS servers on port 53 (TCP/UDP)

**Software Dependencies:**

- **Python**: 3.11 or higher
- **nsupdate**: From BIND utilities (bind9-utils or bind-utils)
- **dig**: For DNS lookups (dnsutils or bind-utils)
- **Operating System**: Linux, macOS, or Windows with WSL

**Network Requirements:**

- Outbound TCP/UDP port 53 to DNS servers
- NTP synchronization (critical for TSIG authentication)
- Stable network connectivity

### File System Layout

**Default installation:**

```
/opt/tuneup-alpha/           # Application directory
├── bin/                     # Virtual environment binaries
├── lib/                     # Python packages
└── share/                   # Documentation

~/.config/tuneup-alpha/      # User configuration
├── config.yaml              # Main configuration file
└── .theme                   # TUI theme preference

/var/log/tuneup-alpha/       # Log files (if configured)
├── app.log                  # Current log
├── app.log.1                # Rotated logs
├── app.log.2
└── ...

/etc/nsupdate/               # TSIG key storage (recommended)
├── example.com.key
├── staging.com.key
└── ...
```

### Process Model

**CLI Operations:**

- Single-process execution
- Short-lived (seconds to minutes)
- Synchronous operations
- Exit on completion or error

**TUI Application:**

- Single-process interactive application
- Long-lived session
- Asynchronous UI updates
- Persists until user quits

**No Daemon:**

- TuneUp Alpha does not run as a background service
- All operations are on-demand
- Use cron/systemd timers for scheduled operations

## Installation and Deployment

### Production Installation

#### Option 1: System-Wide Installation

Install TuneUp Alpha for all users:

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip python3-venv \
                        bind9-utils dnsutils

# Create application directory
sudo mkdir -p /opt/tuneup-alpha
sudo chown $USER:$USER /opt/tuneup-alpha

# Create virtual environment
python3.11 -m venv /opt/tuneup-alpha/venv

# Activate and install
source /opt/tuneup-alpha/venv/bin/activate
pip install --upgrade pip
pip install tuneup-alpha

# Create symlink for global access
sudo ln -s /opt/tuneup-alpha/venv/bin/tuneup-alpha \
           /usr/local/bin/tuneup-alpha

# Verify installation
tuneup-alpha version
```

#### Option 2: Per-User Installation

Install for a specific user (e.g., automation account):

```bash
# As the target user
sudo su - dnsadmin

# Install in user's home directory
python3.11 -m venv ~/.local/tuneup-alpha
source ~/.local/tuneup-alpha/bin/activate
pip install tuneup-alpha

# Add to PATH in ~/.bashrc
echo 'export PATH="$HOME/.local/tuneup-alpha/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
tuneup-alpha version
```

#### Option 3: Container Deployment

Create a Docker container:

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bind9-utils \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Install TuneUp Alpha
RUN pip install tuneup-alpha

# Create config directory
RUN mkdir -p /config /keys

# Set working directory
WORKDIR /app

# Default command
ENTRYPOINT ["tuneup-alpha"]
CMD ["--help"]
```

Build and run:

```bash
# Build image
docker build -t tuneup-alpha:latest .

# Run with mounted config and keys
docker run --rm \
  -v /path/to/config:/config \
  -v /path/to/keys:/keys:ro \
  tuneup-alpha:latest \
  --config-path /config/config.yaml \
  show
```

### Directory Structure Setup

Create the recommended directory structure:

```bash
# Configuration directory
sudo mkdir -p /etc/tuneup-alpha
sudo chmod 755 /etc/tuneup-alpha

# Log directory
sudo mkdir -p /var/log/tuneup-alpha
sudo chown dnsadmin:dnsadmin /var/log/tuneup-alpha
sudo chmod 750 /var/log/tuneup-alpha

# TSIG keys directory
sudo mkdir -p /etc/nsupdate
sudo chown root:dnsadmin /etc/nsupdate
sudo chmod 750 /etc/nsupdate

# Backup directory
sudo mkdir -p /var/backups/tuneup-alpha
sudo chown dnsadmin:dnsadmin /var/backups/tuneup-alpha
sudo chmod 750 /var/backups/tuneup-alpha
```

### Initial Configuration

Create the initial configuration:

```bash
# As the dnsadmin user
sudo su - dnsadmin

# Initialize configuration
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml init

# Set proper permissions
chmod 640 /etc/tuneup-alpha/config.yaml
```

Edit the configuration file:

```yaml
prefix_key_path: /etc/nsupdate

logging:
  enabled: true
  level: INFO
  output: both
  log_file: /var/log/tuneup-alpha/app.log
  max_bytes: 52428800    # 50MB
  backup_count: 20
  structured: true

zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    default_ttl: 3600
    notes: Production DNS zone
    records: []
```

### Post-Installation Verification

Verify the installation:

```bash
# Check version
tuneup-alpha version

# Test nsupdate availability
which nsupdate
nsupdate -V

# Test dig availability
which dig
dig -v

# Test configuration loading
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml show

# Test logging
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml version
cat /var/log/tuneup-alpha/app.log
```

## DNS Server Configuration

### BIND Configuration

Configure BIND to accept dynamic updates from TuneUp Alpha.

#### Generate TSIG Key

```bash
# Generate a TSIG key
tsig-keygen -a hmac-sha256 example.com-key > /etc/nsupdate/example.com.key

# Set permissions
chmod 600 /etc/nsupdate/example.com.key
chown dnsadmin:dnsadmin /etc/nsupdate/example.com.key
```

Example key file content:

```
key "example.com-key" {
    algorithm hmac-sha256;
    secret "base64encodedSecretKeyGoesHere==";
};
```

#### Configure named.conf

Add the key to BIND configuration:

```conf
# /etc/bind/named.conf.local

# Include the TSIG key
include "/etc/nsupdate/example.com.key";

# Define the zone
zone "example.com" {
    type master;
    file "/var/lib/bind/example.com.zone";
    
    # Allow updates authenticated with the TSIG key
    update-policy {
        grant example.com-key zonesub ANY;
    };
    
    # Optional: Restrict to specific hosts
    allow-update {
        key example.com-key;
    };
    
    # Notify secondaries after updates
    notify yes;
    also-notify {
        192.0.2.2;  # Secondary nameserver
    };
};
```

#### Zone File Permissions

Ensure BIND can write to zone files:

```bash
# Set ownership
sudo chown bind:bind /var/lib/bind/example.com.zone

# Set permissions
sudo chmod 644 /var/lib/bind/example.com.zone

# If using a journal file
sudo chown bind:bind /var/lib/bind/example.com.zone.jnl
sudo chmod 644 /var/lib/bind/example.com.zone.jnl
```

#### Reload BIND

```bash
# Check configuration syntax
sudo named-checkconf

# Check zone file syntax
sudo named-checkzone example.com /var/lib/bind/example.com.zone

# Reload BIND
sudo systemctl reload bind9
# or
sudo rndc reload
```

### Testing TSIG Authentication

Test that nsupdate works with the TSIG key:

```bash
# Create a test update script
cat > /tmp/test-update.txt << 'EOF'
server ns1.example.com
zone example.com
update add test.example.com 300 A 192.0.2.100
send
EOF

# Test the update
nsupdate -k /etc/nsupdate/example.com.key /tmp/test-update.txt

# Verify the record was created
dig @ns1.example.com test.example.com A

# Clean up test record
cat > /tmp/cleanup.txt << 'EOF'
server ns1.example.com
zone example.com
update delete test.example.com A
send
EOF

nsupdate -k /etc/nsupdate/example.com.key /tmp/cleanup.txt
```

### PowerDNS Configuration

For PowerDNS with TSIG support:

```bash
# Generate TSIG key
pdnsutil generate-tsig-key example.com-key hmac-sha256

# Get the secret
pdnsutil list-tsig-keys

# Activate metadata for zone
pdnsutil set-meta example.com TSIG-ALLOW-DNSUPDATE example.com-key

# Allow updates
pdnsutil set-meta example.com ALLOW-DNSUPDATE-FROM 0.0.0.0/0
```

Create the key file for TuneUp Alpha:

```bash
cat > /etc/nsupdate/example.com.key << 'EOF'
key "example.com-key" {
    algorithm hmac-sha256;
    secret "secretFromPdnsutil==";
};
EOF

chmod 600 /etc/nsupdate/example.com.key
```

### NSD Configuration

NSD doesn't support dynamic updates directly. Consider using:

- BIND for zones requiring dynamic updates
- PowerDNS with API integration
- Alternative tools for NSD management

### Cloud DNS Providers

#### AWS Route 53

Route 53 doesn't support nsupdate. Alternatives:

- Use AWS CLI with dynamic DNS scripts
- Implement custom integration using boto3
- Use TuneUp Alpha for on-premises BIND

#### Google Cloud DNS

Google Cloud DNS doesn't support nsupdate. Alternatives:

- Use gcloud CLI for DNS management
- Implement custom integration using Google Cloud API
- Use TuneUp Alpha for on-premises zones

#### Azure DNS

Azure DNS doesn't support nsupdate. Alternatives:

- Use Azure CLI for DNS management
- Implement custom integration using Azure SDK
- Use TuneUp Alpha for on-premises zones

## Security Configuration

### File Permissions

Set appropriate permissions for all sensitive files:

```bash
# Configuration file - readable by dnsadmin only
chmod 640 /etc/tuneup-alpha/config.yaml
chown dnsadmin:dnsadmin /etc/tuneup-alpha/config.yaml

# TSIG keys - readable by dnsadmin only
chmod 600 /etc/nsupdate/*.key
chown dnsadmin:dnsadmin /etc/nsupdate/*.key

# Log directory - writable by dnsadmin
chmod 750 /var/log/tuneup-alpha
chown dnsadmin:dnsadmin /var/log/tuneup-alpha

# Log files - readable by dnsadmin and log group
chmod 640 /var/log/tuneup-alpha/*.log
chown dnsadmin:adm /var/log/tuneup-alpha/*.log
```

### User and Group Management

Create dedicated user for DNS management:

```bash
# Create dnsadmin user
sudo useradd -r -s /bin/bash -d /home/dnsadmin -m dnsadmin

# Create dnsops group for additional users
sudo groupadd dnsops

# Add users to dnsops group
sudo usermod -a -G dnsops alice
sudo usermod -a -G dnsops bob

# Set group ownership
sudo chown dnsadmin:dnsops /etc/tuneup-alpha
sudo chmod 750 /etc/tuneup-alpha
```

### SSH Key Management

For automated access:

```bash
# Generate SSH key for automation
sudo su - dnsadmin
ssh-keygen -t ed25519 -C "dnsadmin@automation" -f ~/.ssh/id_ed25519

# For CI/CD integration
# Copy the public key to authorized_keys on target systems
```

### SELinux Configuration

On SELinux-enabled systems:

```bash
# Allow nsupdate to access TSIG keys
sudo semanage fcontext -a -t dnssec_t "/etc/nsupdate(/.*)?"
sudo restorecon -R /etc/nsupdate

# Allow TuneUp Alpha to write logs
sudo semanage fcontext -a -t var_log_t "/var/log/tuneup-alpha(/.*)?"
sudo restorecon -R /var/log/tuneup-alpha

# If needed, create custom policy
# sudo ausearch -c tuneup-alpha --raw | audit2allow -M tuneup-alpha
# sudo semodule -i tuneup-alpha.pp
```

### AppArmor Configuration

On AppArmor-enabled systems:

Create profile `/etc/apparmor.d/usr.local.bin.tuneup-alpha`:

```
#include <tunables/global>

/usr/local/bin/tuneup-alpha {
  #include <abstractions/base>
  #include <abstractions/python>
  
  # Application binary
  /usr/local/bin/tuneup-alpha r,
  /opt/tuneup-alpha/** r,
  
  # Configuration
  /etc/tuneup-alpha/** r,
  /etc/nsupdate/*.key r,
  
  # Logs
  /var/log/tuneup-alpha/* w,
  
  # nsupdate and dig
  /usr/bin/nsupdate ix,
  /usr/bin/dig ix,
  
  # Network
  network inet stream,
  network inet dgram,
}
```

Load the profile:

```bash
sudo apparmor_parser -r /etc/apparmor.d/usr.local.bin.tuneup-alpha
```

### Firewall Configuration

Configure firewall to allow DNS traffic:

```bash
# UFW
sudo ufw allow out 53/tcp
sudo ufw allow out 53/udp

# firewalld
sudo firewall-cmd --permanent --add-service=dns
sudo firewall-cmd --reload

# iptables
sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
```

### Secrets Management

#### Using Environment Variables

Store key paths in environment variables:

```bash
# In /etc/environment or user's .bashrc
export TUNEUP_KEY_PATH=/etc/nsupdate
export TUNEUP_CONFIG=/etc/tuneup-alpha/config.yaml
```

#### Using HashiCorp Vault

Integrate with Vault for TSIG key management:

```bash
# Store TSIG key in Vault
vault kv put secret/dns/example.com \
  key_content=@/etc/nsupdate/example.com.key

# Retrieve before running TuneUp Alpha
vault kv get -field=key_content secret/dns/example.com > /tmp/temp.key
chmod 600 /tmp/temp.key

# Run TuneUp Alpha
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml apply example.com

# Clean up
shred -u /tmp/temp.key
```

#### Using AWS Secrets Manager

```bash
# Store TSIG key
aws secretsmanager create-secret \
  --name tuneup-alpha/example.com/key \
  --secret-string file:///etc/nsupdate/example.com.key

# Retrieve in automation script
aws secretsmanager get-secret-value \
  --secret-id tuneup-alpha/example.com/key \
  --query SecretString \
  --output text > /tmp/temp.key
```

### Audit Logging

Enable comprehensive audit logging:

```yaml
logging:
  enabled: true
  level: INFO
  output: both
  log_file: /var/log/tuneup-alpha/audit.log
  max_bytes: 104857600  # 100MB
  backup_count: 50
  structured: true
```

Configure log forwarding to SIEM:

```bash
# Using rsyslog
cat >> /etc/rsyslog.d/tuneup-alpha.conf << 'EOF'
# Forward TuneUp Alpha logs to SIEM
$ModLoad imfile
$InputFileName /var/log/tuneup-alpha/audit.log
$InputFileTag tuneup-alpha:
$InputFileStateFile stat-tuneup-alpha
$InputFileSeverity info
$InputFileFacility local6
$InputRunFileMonitor

local6.* @@siem.example.com:514
EOF

sudo systemctl restart rsyslog
```

## Logging and Monitoring

### Logging Configuration

#### Production Logging Setup

Recommended production configuration:

```yaml
logging:
  enabled: true
  level: INFO
  output: both
  log_file: /var/log/tuneup-alpha/app.log
  max_bytes: 52428800    # 50MB
  backup_count: 20
  structured: true
```

#### Log Levels by Environment

**Development:**

```yaml
logging:
  level: DEBUG
  output: both
  structured: false  # Human-readable
```

**Staging:**

```yaml
logging:
  level: INFO
  output: both
  structured: true
```

**Production:**

```yaml
logging:
  level: INFO
  output: file
  structured: true
```

### Log Rotation

TuneUp Alpha includes built-in log rotation, but you can also use logrotate:

```bash
# /etc/logrotate.d/tuneup-alpha
/var/log/tuneup-alpha/*.log {
    daily
    missingok
    rotate 90
    compress
    delaycompress
    notifempty
    create 640 dnsadmin adm
    sharedscripts
    postrotate
        # Signal application to reopen log file if needed
    endscript
}
```

### Monitoring Metrics

#### Key Metrics to Monitor

1. **Operation Success Rate**
   - Track successful vs failed nsupdate executions
   - Alert on failure rate > 5%

2. **Configuration Changes**
   - Monitor frequency of config updates
   - Alert on unexpected changes

3. **DNS State Validation**
   - Track verify command results
   - Alert on persistent validation failures

4. **Log File Size**
   - Monitor log directory disk usage
   - Alert when approaching capacity

#### Metrics Extraction from Logs

Extract metrics from structured logs:

```bash
# Count successful operations today
jq 'select(.level == "INFO" and .message | contains("success"))' \
   /var/log/tuneup-alpha/app.log | wc -l

# Count failed operations
jq 'select(.level == "ERROR")' \
   /var/log/tuneup-alpha/app.log | wc -l

# List zones updated today
jq -r 'select(.audit_type == "nsupdate_execution") | .zone_name' \
   /var/log/tuneup-alpha/app.log | sort -u
```

#### Prometheus Integration

Create a metrics exporter script:

```bash
#!/bin/bash
# /usr/local/bin/tuneup-metrics.sh

LOG_FILE="/var/log/tuneup-alpha/app.log"
METRICS_FILE="/var/lib/prometheus/node-exporter/tuneup.prom"

# Count operations
SUCCESS=$(jq -c 'select(.audit_type == "nsupdate_execution" and .success == true)' "$LOG_FILE" | wc -l)
FAILED=$(jq -c 'select(.audit_type == "nsupdate_execution" and .success == false)' "$LOG_FILE" | wc -l)

# Write metrics
cat > "$METRICS_FILE" << EOF
# HELP tuneup_operations_total Total DNS operations
# TYPE tuneup_operations_total counter
tuneup_operations_success_total $SUCCESS
tuneup_operations_failed_total $FAILED

# HELP tuneup_last_operation_timestamp Timestamp of last operation
# TYPE tuneup_last_operation_timestamp gauge
tuneup_last_operation_timestamp $(date +%s)
EOF
```

Run via cron:

```bash
# Run every 5 minutes
*/5 * * * * /usr/local/bin/tuneup-metrics.sh
```

### Alerting

#### Email Alerts on Failures

Create alert script:

```bash
#!/bin/bash
# /usr/local/bin/tuneup-alert.sh

LOG_FILE="/var/log/tuneup-alpha/app.log"
ALERT_EMAIL="ops@example.com"

# Check for recent errors (last 5 minutes)
ERRORS=$(jq -c --arg since "$(date -d '5 minutes ago' --iso-8601=seconds)" \
  'select(.level == "ERROR" and .timestamp > $since)' "$LOG_FILE")

if [ -n "$ERRORS" ]; then
  echo "$ERRORS" | mail -s "[ALERT] TuneUp Alpha Errors" "$ALERT_EMAIL"
fi
```

Schedule via cron:

```bash
*/5 * * * * /usr/local/bin/tuneup-alert.sh
```

#### Slack Integration

```bash
#!/bin/bash
# Send alerts to Slack

SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
ERROR_COUNT=$(jq -c 'select(.level == "ERROR")' /var/log/tuneup-alpha/app.log | wc -l)

if [ "$ERROR_COUNT" -gt 0 ]; then
  curl -X POST "$SLACK_WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d "{\"text\": \"⚠️ TuneUp Alpha: $ERROR_COUNT errors detected\"}"
fi
```

### Health Checks

Create a health check script:

```bash
#!/bin/bash
# /usr/local/bin/tuneup-health.sh

CONFIG="/etc/tuneup-alpha/config.yaml"
EXIT_CODE=0

# Check if tuneup-alpha is installed
if ! command -v tuneup-alpha &> /dev/null; then
  echo "ERROR: tuneup-alpha not found"
  EXIT_CODE=1
fi

# Check if nsupdate is available
if ! command -v nsupdate &> /dev/null; then
  echo "ERROR: nsupdate not found"
  EXIT_CODE=1
fi

# Check if config file exists
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: Config file not found: $CONFIG"
  EXIT_CODE=1
fi

# Check if log directory is writable
if [ ! -w "/var/log/tuneup-alpha" ]; then
  echo "ERROR: Log directory not writable"
  EXIT_CODE=1
fi

# Test configuration loading
if ! tuneup-alpha --config-path "$CONFIG" show &> /dev/null; then
  echo "ERROR: Failed to load configuration"
  EXIT_CODE=1
fi

if [ $EXIT_CODE -eq 0 ]; then
  echo "OK: All health checks passed"
fi

exit $EXIT_CODE
```

Run via cron or monitoring system:

```bash
# Check every hour
0 * * * * /usr/local/bin/tuneup-health.sh || echo "Health check failed"
```

## Backup and Recovery

### Configuration Backup

#### Manual Backup

```bash
#!/bin/bash
# /usr/local/bin/tuneup-backup.sh

BACKUP_DIR="/var/backups/tuneup-alpha"
CONFIG_FILE="/etc/tuneup-alpha/config.yaml"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Create backup
cp "$CONFIG_FILE" "$BACKUP_DIR/config-$TIMESTAMP.yaml"

# Compress old backups (older than 7 days)
find "$BACKUP_DIR" -name "config-*.yaml" -mtime +7 -exec gzip {} \;

# Remove backups older than 90 days
find "$BACKUP_DIR" -name "config-*.yaml.gz" -mtime +90 -delete

echo "Backup created: $BACKUP_DIR/config-$TIMESTAMP.yaml"
```

Schedule daily backups:

```bash
# Daily at 2 AM
0 2 * * * /usr/local/bin/tuneup-backup.sh
```

#### Git-Based Backup

```bash
# Initialize git repository
cd /etc/tuneup-alpha
git init
git add config.yaml
git commit -m "Initial configuration"

# Exclude sensitive files
cat > .gitignore << 'EOF'
*.key
*.private
.theme
EOF

# Add remote (private repository)
git remote add origin git@github.com:yourorg/dns-config.git

# Push to remote
git push -u origin main
```

Automate git commits:

```bash
#!/bin/bash
# /usr/local/bin/tuneup-git-backup.sh

cd /etc/tuneup-alpha

# Check if there are changes
if git diff --quiet config.yaml; then
  echo "No changes to commit"
  exit 0
fi

# Commit and push
git add config.yaml
git commit -m "Auto-backup $(date +%Y-%m-%d\ %H:%M:%S)"
git push origin main

echo "Configuration backed up to git"
```

#### Remote Backup

```bash
# Backup to remote server via rsync
rsync -avz --delete \
  /etc/tuneup-alpha/ \
  backup-server:/backups/tuneup-alpha/

# Or use scp
scp /etc/tuneup-alpha/config.yaml \
  backup-server:/backups/tuneup-alpha/config-$(date +%Y%m%d).yaml
```

### DNS State Backup

Backup current DNS state:

```bash
#!/bin/bash
# /usr/local/bin/dns-state-backup.sh

BACKUP_DIR="/var/backups/tuneup-alpha/dns-state"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
CONFIG="/etc/tuneup-alpha/config.yaml"

mkdir -p "$BACKUP_DIR"

# Get list of zones
ZONES=$(tuneup-alpha --config-path "$CONFIG" show --format=plain | awk '{print $1}')

# Backup each zone
for zone in $ZONES; do
  echo "Backing up $zone..."
  dig @$(dig +short NS "$zone" | head -1) "$zone" AXFR > \
    "$BACKUP_DIR/${zone}-${TIMESTAMP}.zone"
done

# Compress backups older than 1 day
find "$BACKUP_DIR" -name "*.zone" -mtime +1 -exec gzip {} \;

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "*.zone.gz" -mtime +30 -delete
```

### Recovery Procedures

#### Restore Configuration from Backup

```bash
# List available backups
ls -lh /var/backups/tuneup-alpha/

# Restore specific backup
cp /var/backups/tuneup-alpha/config-20241117-140000.yaml \
   /etc/tuneup-alpha/config.yaml

# Verify restored configuration
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml show

# Apply to DNS if needed
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml \
  apply example.com --no-dry-run
```

#### Restore from Git

```bash
cd /etc/tuneup-alpha

# View commit history
git log --oneline

# Restore to specific commit
git checkout abc123 -- config.yaml

# Or restore to previous version
git checkout HEAD~1 -- config.yaml

# Verify and apply
tuneup-alpha show
```

#### Point-in-Time Recovery

```bash
#!/bin/bash
# Restore to specific date/time

TARGET_DATE="2024-11-17 14:00:00"
BACKUP_DIR="/var/backups/tuneup-alpha"

# Find closest backup
BACKUP=$(find "$BACKUP_DIR" -name "config-*.yaml*" \
  -newermt "$TARGET_DATE" | sort | head -1)

if [ -z "$BACKUP" ]; then
  echo "No backup found for $TARGET_DATE"
  exit 1
fi

echo "Restoring from: $BACKUP"

# Decompress if needed
if [[ "$BACKUP" == *.gz ]]; then
  gunzip -c "$BACKUP" > /etc/tuneup-alpha/config.yaml
else
  cp "$BACKUP" /etc/tuneup-alpha/config.yaml
fi

echo "Configuration restored"
```

### Disaster Recovery Plan

#### Complete System Recovery

1. **Install TuneUp Alpha** on new system
2. **Restore TSIG keys** from secure backup
3. **Restore configuration** from backup
4. **Verify connectivity** to DNS servers
5. **Validate configuration** matches DNS state
6. **Document recovery** in logs

```bash
#!/bin/bash
# /usr/local/bin/disaster-recovery.sh

echo "=== TuneUp Alpha Disaster Recovery ==="

# Step 1: Install dependencies
echo "Installing dependencies..."
apt-get update
apt-get install -y python3.11 python3-pip python3-venv bind9-utils

# Step 2: Install TuneUp Alpha
echo "Installing TuneUp Alpha..."
python3.11 -m venv /opt/tuneup-alpha/venv
source /opt/tuneup-alpha/venv/bin/activate
pip install tuneup-alpha

# Step 3: Restore TSIG keys
echo "Restoring TSIG keys..."
rsync -avz backup-server:/secure/nsupdate/ /etc/nsupdate/
chmod 600 /etc/nsupdate/*.key

# Step 4: Restore configuration
echo "Restoring configuration..."
rsync -avz backup-server:/backups/tuneup-alpha/ /etc/tuneup-alpha/

# Step 5: Verify
echo "Verifying installation..."
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml show

echo "=== Recovery complete ==="
```

## Performance Tuning

### Optimization Strategies

#### Configuration File Optimization

```yaml
# Use default_ttl to avoid repeating TTL values
zones:
  - name: example.com
    default_ttl: 3600  # Applied to all records without explicit TTL
    records:
      - label: "@"
        type: A
        value: 192.0.2.1
        # No TTL needed - uses default_ttl
```

#### Batch Operations

Process multiple zones efficiently:

```bash
#!/bin/bash
# Apply updates to all zones in parallel

CONFIG="/etc/tuneup-alpha/config.yaml"
ZONES=$(tuneup-alpha --config-path "$CONFIG" show --format=plain | awk '{print $1}')

# Apply in parallel (max 4 concurrent)
echo "$ZONES" | xargs -P 4 -I {} bash -c \
  "tuneup-alpha --config-path $CONFIG apply {} --no-dry-run --force"
```

#### DNS Query Optimization

Reduce DNS lookup overhead in TUI:

```yaml
# Disable auto-lookup if not needed
# (User manual feature - controlled by user interaction)
```

### Resource Limits

#### Memory Limits

For containerized deployments:

```yaml
# docker-compose.yml
services:
  tuneup-alpha:
    image: tuneup-alpha:latest
    mem_limit: 512m
    memswap_limit: 512m
```

#### Process Limits

For systemd services:

```ini
[Service]
MemoryLimit=512M
CPUQuota=50%
TasksMax=100
```

### Caching Strategies

#### DNS Response Caching

Configure system DNS caching:

```bash
# Install nscd or dnsmasq
sudo apt-get install nscd

# Configure caching
sudo systemctl enable nscd
sudo systemctl start nscd
```

### Concurrent Operations

Limit concurrent nsupdate executions:

```bash
#!/bin/bash
# Use flock to prevent concurrent updates

LOCK_FILE="/var/lock/tuneup-alpha.lock"

(
  flock -n 200 || {
    echo "Another instance is running"
    exit 1
  }
  
  # Run TuneUp Alpha operation
  tuneup-alpha apply example.com --no-dry-run
  
) 200>"$LOCK_FILE"
```

## Multi-User Deployments

### Access Control

#### Role-Based Access

Define roles:

1. **Administrator**: Full access to all operations
2. **Operator**: Can view and apply, cannot modify keys
3. **Viewer**: Read-only access

```bash
# Create groups
sudo groupadd dns-admin
sudo groupadd dns-operator
sudo groupadd dns-viewer

# Assign users
sudo usermod -a -G dns-admin alice
sudo usermod -a -G dns-operator bob
sudo usermod -a -G dns-viewer charlie

# Set permissions
sudo chown root:dns-admin /etc/tuneup-alpha/config.yaml
sudo chmod 660 /etc/tuneup-alpha/config.yaml

sudo chown root:dns-admin /etc/nsupdate
sudo chmod 750 /etc/nsupdate
```

#### Sudo Configuration

Allow operators to run specific commands:

```bash
# /etc/sudoers.d/tuneup-alpha

# DNS Operators can run apply and verify
%dns-operator ALL=(dnsadmin) NOPASSWD: /usr/local/bin/tuneup-alpha apply *
%dns-operator ALL=(dnsadmin) NOPASSWD: /usr/local/bin/tuneup-alpha verify *
%dns-operator ALL=(dnsadmin) NOPASSWD: /usr/local/bin/tuneup-alpha diff *
%dns-operator ALL=(dnsadmin) NOPASSWD: /usr/local/bin/tuneup-alpha plan *

# Viewers can only show
%dns-viewer ALL=(dnsadmin) NOPASSWD: /usr/local/bin/tuneup-alpha show
```

### Shared Configuration

#### Using Shared Storage

```bash
# Mount shared filesystem
sudo mount -t nfs nfs-server:/export/tuneup-alpha /etc/tuneup-alpha

# Add to /etc/fstab for persistence
echo "nfs-server:/export/tuneup-alpha /etc/tuneup-alpha nfs defaults 0 0" | \
  sudo tee -a /etc/fstab
```

#### Git-Based Workflow

```bash
# Developer makes changes
cd /etc/tuneup-alpha
git pull
vi config.yaml
git add config.yaml
git commit -m "Add new record for api.example.com"
git push

# On production server
cd /etc/tuneup-alpha
git pull
tuneup-alpha apply example.com --no-dry-run
```

### Audit Trail for Multi-User

Track who made changes:

```bash
#!/bin/bash
# Wrapper script: /usr/local/bin/tuneup-wrapper.sh

USER=$(whoami)
COMMAND="$@"
TIMESTAMP=$(date --iso-8601=seconds)

# Log the command
echo "[$TIMESTAMP] $USER: $COMMAND" >> /var/log/tuneup-alpha/user-audit.log

# Execute TuneUp Alpha
/usr/local/bin/tuneup-alpha "$@"

# Log the result
echo "[$TIMESTAMP] $USER: Exit code $?" >> /var/log/tuneup-alpha/user-audit.log
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/dns-deploy.yml
name: Deploy DNS Changes

on:
  push:
    branches: [main]
    paths:
      - 'dns-config.yaml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y bind9-utils
          pip install tuneup-alpha
      
      - name: Configure TSIG key
        run: |
          mkdir -p /tmp/keys
          echo "${{ secrets.TSIG_KEY }}" > /tmp/keys/example.com.key
          chmod 600 /tmp/keys/example.com.key
      
      - name: Validate configuration
        run: |
          tuneup-alpha --config-path dns-config.yaml show
      
      - name: Plan changes
        run: |
          tuneup-alpha --config-path dns-config.yaml plan example.com
      
      - name: Apply changes
        run: |
          tuneup-alpha --config-path dns-config.yaml \
            apply example.com --no-dry-run --force
      
      - name: Verify deployment
        run: |
          sleep 10  # Wait for DNS propagation
          tuneup-alpha --config-path dns-config.yaml verify example.com
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - deploy
  - verify

variables:
  CONFIG_FILE: dns-config.yaml

validate:
  stage: validate
  image: python:3.11-slim
  before_script:
    - apt-get update && apt-get install -y bind9-utils
    - pip install tuneup-alpha
  script:
    - tuneup-alpha --config-path $CONFIG_FILE show
    - tuneup-alpha --config-path $CONFIG_FILE plan example.com

deploy:
  stage: deploy
  image: python:3.11-slim
  before_script:
    - apt-get update && apt-get install -y bind9-utils
    - pip install tuneup-alpha
    - mkdir -p /tmp/keys
    - echo "$TSIG_KEY" > /tmp/keys/example.com.key
    - chmod 600 /tmp/keys/example.com.key
  script:
    - tuneup-alpha --config-path $CONFIG_FILE \
        apply example.com --no-dry-run --force
  only:
    - main

verify:
  stage: verify
  image: python:3.11-slim
  before_script:
    - apt-get update && apt-get install -y bind9-utils dnsutils
    - pip install tuneup-alpha
  script:
    - sleep 10
    - tuneup-alpha --config-path $CONFIG_FILE verify example.com
  only:
    - main
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        CONFIG_FILE = 'dns-config.yaml'
        VENV_DIR = "${WORKSPACE}/.venv"
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3.11 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install tuneup-alpha
                '''
            }
        }
        
        stage('Validate') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    tuneup-alpha --config-path ${CONFIG_FILE} show
                '''
            }
        }
        
        stage('Plan') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    tuneup-alpha --config-path ${CONFIG_FILE} plan example.com
                '''
            }
        }
        
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([file(credentialsId: 'tsig-key', variable: 'TSIG_KEY_FILE')]) {
                    sh '''
                        . ${VENV_DIR}/bin/activate
                        tuneup-alpha --config-path ${CONFIG_FILE} \
                            apply example.com --no-dry-run --force
                    '''
                }
            }
        }
        
        stage('Verify') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    sleep 10
                    . ${VENV_DIR}/bin/activate
                    tuneup-alpha --config-path ${CONFIG_FILE} verify example.com
                '''
            }
        }
    }
    
    post {
        failure {
            emailext(
                subject: "DNS Deployment Failed: ${env.JOB_NAME}",
                body: "Check ${env.BUILD_URL} for details",
                to: 'ops@example.com'
            )
        }
    }
}
```

### Ansible Playbook

```yaml
# playbooks/deploy-dns.yml
---
- name: Deploy DNS Changes
  hosts: dns-servers
  become: yes
  vars:
    config_file: /etc/tuneup-alpha/config.yaml
    zones:
      - example.com
      - staging.com
  
  tasks:
    - name: Ensure TuneUp Alpha is installed
      pip:
        name: tuneup-alpha
        state: present
        virtualenv: /opt/tuneup-alpha/venv
        virtualenv_python: python3.11
    
    - name: Copy configuration
      copy:
        src: files/config.yaml
        dest: "{{ config_file }}"
        owner: dnsadmin
        group: dnsadmin
        mode: '0640'
    
    - name: Validate configuration
      command: >
        /opt/tuneup-alpha/venv/bin/tuneup-alpha
        --config-path {{ config_file }}
        show
      changed_when: false
    
    - name: Apply DNS changes
      command: >
        /opt/tuneup-alpha/venv/bin/tuneup-alpha
        --config-path {{ config_file }}
        apply {{ item }} --no-dry-run --force
      loop: "{{ zones }}"
      register: apply_result
    
    - name: Verify deployment
      command: >
        /opt/tuneup-alpha/venv/bin/tuneup-alpha
        --config-path {{ config_file }}
        verify {{ item }}
      loop: "{{ zones }}"
      changed_when: false
```

## Troubleshooting and Diagnostics

### Diagnostic Commands

#### Check System Status

```bash
# System health check
/usr/local/bin/tuneup-health.sh

# Check version
tuneup-alpha version

# Verify nsupdate
which nsupdate
nsupdate -V

# Check DNS connectivity
dig @8.8.8.8 google.com
```

#### Configuration Debugging

```bash
# Enable debug logging temporarily
cat > /tmp/debug-config.yaml << 'EOF'
logging:
  enabled: true
  level: DEBUG
  output: console
  structured: false

zones:
  - name: example.com
    server: ns1.example.com
    key_file: /etc/nsupdate/example.com.key
    records: []
EOF

# Run with debug config
tuneup-alpha --config-path /tmp/debug-config.yaml show
```

#### TSIG Key Testing

```bash
# Test TSIG key manually
cat > /tmp/test.nsupdate << 'EOF'
server ns1.example.com
zone example.com
update add test.example.com 300 TXT "test"
send
EOF

# Execute
nsupdate -v -k /etc/nsupdate/example.com.key /tmp/test.nsupdate

# Check result
dig @ns1.example.com test.example.com TXT

# Cleanup
cat > /tmp/cleanup.nsupdate << 'EOF'
server ns1.example.com
zone example.com
update delete test.example.com TXT
send
EOF

nsupdate -k /etc/nsupdate/example.com.key /tmp/cleanup.nsupdate
```

### Common Issues

See USER_MANUAL.md Troubleshooting section for common issues and solutions.

### Advanced Debugging

#### Network Packet Capture

```bash
# Capture DNS traffic
sudo tcpdump -i any -n port 53 -w /tmp/dns-traffic.pcap

# In another terminal, run TuneUp Alpha operation
tuneup-alpha apply example.com --no-dry-run

# Stop capture (Ctrl+C)
# Analyze with wireshark
wireshark /tmp/dns-traffic.pcap
```

#### Strace Analysis

```bash
# Trace system calls
strace -o /tmp/tuneup-strace.log \
  tuneup-alpha apply example.com --dry-run

# Review
less /tmp/tuneup-strace.log
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily

```bash
# Check logs for errors
grep ERROR /var/log/tuneup-alpha/app.log | tail -20

# Verify critical zones
for zone in example.com staging.com; do
  tuneup-alpha verify $zone
done
```

#### Weekly

```bash
# Review log file sizes
du -sh /var/log/tuneup-alpha/

# Check backup status
ls -lh /var/backups/tuneup-alpha/ | tail -10

# Test disaster recovery procedure (in staging)
```

#### Monthly

```bash
# Review and rotate old logs
find /var/log/tuneup-alpha -name "*.log.*" -mtime +60 -delete

# Review and clean old backups
find /var/backups/tuneup-alpha -mtime +90 -delete

# Update TuneUp Alpha
pip install --upgrade tuneup-alpha

# Review security advisories
```

#### Quarterly

```bash
# Audit TSIG keys - rotate if needed
# Review user access permissions
# Test complete disaster recovery
# Review and update documentation
```

### Upgrade Procedures

#### Minor Version Upgrade

```bash
# Backup current installation
cp -r /opt/tuneup-alpha /opt/tuneup-alpha.backup

# Upgrade
source /opt/tuneup-alpha/venv/bin/activate
pip install --upgrade tuneup-alpha

# Verify
tuneup-alpha version
tuneup-alpha show

# Test
tuneup-alpha plan example.com
```

#### Major Version Upgrade

```bash
# Review changelog and breaking changes
# Backup configuration and data
cp /etc/tuneup-alpha/config.yaml /tmp/config-backup.yaml

# Create new virtual environment
python3.11 -m venv /opt/tuneup-alpha-new/venv
source /opt/tuneup-alpha-new/venv/bin/activate
pip install tuneup-alpha

# Test with existing configuration
tuneup-alpha --config-path /etc/tuneup-alpha/config.yaml show

# If successful, replace old installation
mv /opt/tuneup-alpha /opt/tuneup-alpha-old
mv /opt/tuneup-alpha-new /opt/tuneup-alpha

# Update symlinks
sudo ln -sf /opt/tuneup-alpha/venv/bin/tuneup-alpha \
           /usr/local/bin/tuneup-alpha
```

## Security Best Practices

### Security Checklist

- [ ] TSIG keys stored with 600 permissions
- [ ] Configuration files have restricted permissions
- [ ] Separate user account for DNS operations
- [ ] Audit logging enabled
- [ ] Log files monitored for suspicious activity
- [ ] Backups encrypted and stored securely
- [ ] Network access restricted to necessary hosts
- [ ] SELinux/AppArmor policies configured
- [ ] Regular security updates applied
- [ ] TSIG keys rotated periodically

### Hardening Guide

```bash
# Restrict file permissions
chmod 600 /etc/nsupdate/*.key
chmod 640 /etc/tuneup-alpha/config.yaml
chmod 750 /var/log/tuneup-alpha

# Set immutable flag on key files
sudo chattr +i /etc/nsupdate/*.key
# To modify: sudo chattr -i /etc/nsupdate/*.key

# Disable core dumps
echo "* hard core 0" | sudo tee -a /etc/security/limits.conf

# Enable process accounting
sudo apt-get install acct
sudo systemctl enable acct
```

## Disaster Recovery

### Recovery Time Objectives

- **Configuration restore**: < 5 minutes
- **Full system restore**: < 30 minutes
- **DNS service restoration**: < 60 minutes

### Recovery Scenarios

#### Scenario 1: Corrupted Configuration

```bash
# Restore from latest backup
cp /var/backups/tuneup-alpha/config-latest.yaml \
   /etc/tuneup-alpha/config.yaml

# Verify
tuneup-alpha show
```

#### Scenario 2: Lost TSIG Keys

```bash
# Restore from secure backup
scp backup-server:/secure/nsupdate/example.com.key \
    /etc/nsupdate/example.com.key
chmod 600 /etc/nsupdate/example.com.key

# Test
tuneup-alpha plan example.com
```

#### Scenario 3: Complete System Loss

Follow the complete disaster recovery procedure documented in the Disaster Recovery Plan section.

---

## Appendix

### Glossary

- **TSIG**: Transaction Signature - DNS authentication mechanism
- **nsupdate**: BIND utility for dynamic DNS updates
- **Zone**: DNS domain managed by TuneUp Alpha
- **Record**: Individual DNS entry within a zone
- **Dry-run**: Preview mode that doesn't make actual changes

### References

- BIND 9 Documentation: https://bind9.readthedocs.io/
- DNS RFCs: RFC 1035, RFC 2136, RFC 2845
- TuneUp Alpha GitHub: https://github.com/radek-zitek-cloud/tuneup-alpha

### Support

For additional support:

- GitHub Issues: https://github.com/radek-zitek-cloud/tuneup-alpha/issues
- Documentation: See README.md and USER_MANUAL.md

---

**Document Version**: 1.0
**Last Updated**: 2024-11-18
**Maintained By**: TuneUp Alpha Team
