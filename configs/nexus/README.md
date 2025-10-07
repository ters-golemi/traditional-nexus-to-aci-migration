# Nexus Configuration Examples

This directory contains sample configurations for the traditional Nexus environment that will be migrated to ACI.

## Directory Structure

```
nexus/
├── current-state/          # Existing Nexus configurations
│   ├── core-01.cfg        # Core switch 1 configuration
│   ├── core-02.cfg        # Core switch 2 configuration
│   ├── agg-01.cfg         # Aggregation switch 1 configuration
│   ├── agg-02.cfg         # Aggregation switch 2 configuration
│   ├── access-01.cfg      # Access switch 1 configuration
│   └── access-02.cfg      # Access switch 2 configuration
├── migration-prep/        # Pre-migration configuration changes
│   ├── vlan-mapping.txt   # VLAN to EPG mapping
│   └── interface-prep.cfg # Interface preparation configs
└── backup/               # Configuration backups
    └── backup-procedure.md
```

## Configuration Overview

The sample configurations represent a typical three-tier Nexus environment with:

- **Core Layer**: 2x Nexus 9000 switches with L3 routing
- **Aggregation Layer**: 2x Nexus 9000 switches with vPC
- **Access Layer**: 2x Nexus 9000 switches connecting servers
- **VLANs**: 20 VLANs for different application tiers
- **Routing**: OSPF and BGP for redundancy

## Usage Instructions

1. Review the current-state configurations to understand the existing setup
2. Use the migration-prep configurations during the transition phase
3. Follow the backup procedures before making any changes
4. Validate configurations using the provided scripts

## Security Notice

These are example configurations for demonstration purposes. Always:
- Change default passwords
- Update SNMP community strings
- Modify IP addressing to match your environment
- Review security policies before deployment