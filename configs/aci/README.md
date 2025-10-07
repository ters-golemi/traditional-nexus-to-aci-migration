# ACI Configuration Templates

This directory contains configuration templates and examples for the target ACI environment.

## Directory Structure

```
aci/
├── tenant-configs/        # Tenant configuration templates
│   ├── production-tenant.json
│   ├── development-tenant.json
│   └── shared-services.json
├── fabric-policies/       # ACI fabric-wide policies
│   ├── switch-profiles.json
│   ├── interface-policies.json
│   └── access-policies.json
├── networking/           # Network configuration
│   ├── vrfs.json
│   ├── bridge-domains.json
│   ├── subnets.json
│   └── l3outs.json
├── application-policies/ # Application-centric policies
│   ├── epgs.json
│   ├── contracts.json
│   └── filters.json
└── migration-mappings/   # Nexus to ACI mapping files
    ├── vlan-to-epg-mapping.csv
    ├── interface-mapping.csv
    └── policy-mapping.json
```

## Configuration Overview

The ACI templates are organized to support:

- **Multi-Tenant Architecture**: Separate tenants for production, development, and shared services
- **Application Segmentation**: EPGs for different application tiers
- **Security Policies**: Contracts and filters for micro-segmentation
- **Network Services**: L3Outs for external connectivity
- **Infrastructure**: Switch profiles and access policies

## Template Usage

1. Customize the tenant configurations for your environment
2. Update IP addressing and VLAN mappings
3. Modify contracts and filters based on your security requirements
4. Use the migration mappings to plan the transition from Nexus VLANs to ACI EPGs

## Important Notes

- All templates use example IP addressing - update for your environment
- Contract rules are examples - review and modify for your security requirements
- Switch profiles assume specific hardware models - adjust as needed
- Always test configurations in a lab environment first