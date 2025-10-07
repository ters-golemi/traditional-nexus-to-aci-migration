#!/bin/bash

# ACI Migration Automation Setup Script
# This script sets up the environment for Nexus to ACI migration automation

set -e  # Exit on any error

echo "=================================================="
echo "ACI Migration Automation - Environment Setup"
echo "=================================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo "Error: Python 3.8 or higher is required. Found Python $PYTHON_VERSION"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

echo "Python version check passed: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating output directories..."
mkdir -p migration_output
mkdir -p backups
mkdir -p logs

# Create default configuration file
echo "Creating default configuration files..."

cat > migration_config.json << EOF
{
  "apic": {
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "CHANGE_ME",
    "verify_ssl": false
  },
  "nexus": {
    "config_directory": "configs/nexus/current-state"
  },
  "aci": {
    "tenant_configs_directory": "configs/aci/tenant-configs"
  },
  "output_directory": "migration_output",
  "backup_directory": "backups",
  "log_level": "INFO"
}
EOF

# Create Ansible configuration
cat > ansible/ansible.cfg << EOF
[defaults]
inventory = inventory.yml
host_key_checking = False
timeout = 30
retry_files_enabled = False
log_path = ../logs/ansible.log

[inventory]
enable_plugins = yaml, ini

[ssh_connection]
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
pipelining = True
EOF

# Make scripts executable
echo "Setting script permissions..."
chmod +x scripts/*.py
chmod +x setup.sh

# Validate Ansible installation
if command -v ansible --version &> /dev/null; then
    echo "Ansible installation validated: $(ansible --version | head -1)"
else
    echo "Warning: Ansible not found in PATH. Install with: pip install ansible"
fi

echo ""
echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Update migration_config.json with your APIC credentials"
echo "3. Update ansible/inventory.yml with your device IPs"
echo "4. Review and customize configurations in configs/ directory"
echo "5. Run pre-migration checks: python3 scripts/migrate_orchestrator.py --config migration_config.json --phase pre-check"
echo ""
echo "For Ansible automation:"
echo "cd ansible && ansible-playbook playbooks/aci_migration.yml"
echo ""
echo "Documentation: See README.md for detailed usage instructions"
echo ""

# Check for common issues
echo "Environment validation:"
echo "- Python version: $(python3 --version)"
echo "- Pip version: $(pip --version)"
echo "- Virtual environment: $(which python)"

if [ -f "requirements.txt" ]; then
    echo "- Dependencies installed: $(pip list | wc -l) packages"
else
    echo "- Warning: requirements.txt not found"
fi

echo ""
echo "Setup completed successfully!"