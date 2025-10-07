# Nexus to ACI Migration Guide

## Table of Contents
1. [Overview](#overview)
2. [Current Environment Assessment](#current-environment-assessment)
3. [Prerequisites](#prerequisites)
4. [ACI Architecture Overview](#aci-architecture-overview)
5. [Planning Phase](#planning-phase)
6. [Migration Procedure](#migration-procedure)
7. [Validation and Testing](#validation-and-testing)
8. [Rollback Procedures](#rollback-procedures)
9. [Post-Migration Tasks](#post-migration-tasks)
10. [Best Practices and Recommendations](#best-practices-and-recommendations)
11. [References](#references)

---

## Overview

This guide provides a comprehensive step-by-step procedure for migrating from a traditional Cisco Nexus data center network to the Cisco Application Centric Infrastructure (ACI) solution. The migration follows Cisco Validated Designs and industry best practices to ensure minimal disruption to production services.

### Migration Approach
- **Parallel Migration**: Deploy ACI alongside existing Nexus infrastructure
- **Phased Cutover**: Migrate workloads in controlled phases
- **Zero-Downtime Goal**: Minimize service interruption during migration

---

## Current Environment Assessment

### Network Topology

**Current Infrastructure:**
- **2x Core Nexus Switches**: Providing Layer 3 routing and inter-VLAN routing
- **2x Aggregation Nexus Switches**: Aggregation layer with vPC to core
- **2x Access Nexus Switches**: Access layer connecting servers and ESXi hosts
- **vPC Configuration**: Between core and aggregation layers
- **20 VLANs**: Supporting various application and management networks
- **Connected Workloads**: Physical servers and VMware ESXi hosts

### Documentation Requirements

Before starting migration, document:

1. **Network Inventory**
   - Switch models and software versions
   - Interface configurations and assignments
   - vPC domain configurations
   - Port-channel configurations

2. **VLAN Information**
   - VLAN IDs and names
   - VLAN-to-subnet mappings
   - STP configurations
   - VLAN trunking details

3. **IP Addressing**
   - Management IP addresses
   - Gateway addresses for each VLAN
   - HSRP/VRRP configurations
   - Routing protocol configurations

4. **Application Topology**
   - Application dependencies
   - Server-to-VLAN mappings
   - ESXi host configurations
   - Network policies and ACLs

5. **Quality of Service (QoS)**
   - QoS policies
   - Traffic classification
   - Rate limiting configurations

6. **Security Policies**
   - ACLs and security policies
   - Port security configurations
   - Storm control settings

---

## Prerequisites

### Hardware Requirements

**Minimum ACI Components:**
- **3x Cisco APIC Controllers**: For cluster deployment (provides redundancy)
- **2x Spine Switches**: Minimum for ACI fabric
- **2x Leaf Switches**: To start (can add more as needed)
- **Compatible Optics**: For spine-leaf connectivity

**Recommended Configuration:**
- Multiple leaf switches for workload distribution
- Redundant connectivity to existing infrastructure during migration

### Software Requirements

- **ACI Firmware**: Latest recommended release (check Cisco.com)
- **APIC Software**: Compatible version with fabric switches
- **VMware vCenter**: For ESXi integration (if applicable)
- **Cisco ACI Virtual Edge**: For VM visibility (optional)

### Network Requirements

- **Out-of-band Management Network**: For APIC management
- **IP Addressing Plan**: For ACI fabric (TEP pool, infrastructure VLAN)
- **L3Out Connectivity**: To existing network during migration
- **Time Synchronization**: NTP server for all devices

### Skills and Resources

- **Trained Personnel**: ACI configuration and troubleshooting
- **Maintenance Window**: Scheduled for cutover activities
- **Backup Team**: For rollback if needed
- **Change Management**: Approved change requests

### Documentation and Tools

- **Migration Runbook**: Detailed step-by-step procedures
- **Network Diagrams**: Current and target state
- **Configuration Backup**: All existing Nexus configurations
- **Testing Plan**: Pre and post-migration validation

---

## ACI Architecture Overview

### Key ACI Components

#### Application Policy Infrastructure Controller (APIC)
- Centralized management and policy controller
- Cluster of 3 controllers for production (minimum)
- REST API for automation and orchestration
- GUI and CLI interfaces

#### Spine Switches
- High-speed non-blocking fabric interconnect
- No direct endpoint connectivity
- Provides anycast gateway functionality
- ECMP load balancing across fabric

#### Leaf Switches
- Direct endpoint connectivity (servers, storage, hypervisors)
- Enforce policy from APIC
- VXLAN encapsulation for overlay network
- Local switching for traffic within same leaf

### ACI Fabric Architecture

```
                    [APIC Cluster]
                          |
                    Out-of-Band Mgmt
                          |
        +-----------------+------------------+
        |                                    |
    [Spine-1]                            [Spine-2]
        |                                    |
    +---+---+---+                        +---+---+---+
    |   |   |   |                        |   |   |   |
[Leaf-1][Leaf-2][Leaf-3]            [Leaf-1][Leaf-2][Leaf-3]
    |       |       |                    |       |       |
Servers  ESXi   Storage              Servers  ESXi   Storage
```

### ACI Policy Model

#### Tenant
- Logical container for policies
- Isolates network and security policies
- Can represent business units or applications

#### Application Profile
- Container for endpoint groups (EPGs)
- Represents application tiers

#### Endpoint Groups (EPGs)
- Collection of endpoints with common policy requirements
- Replaces traditional VLANs concept
- Can span multiple switches

#### Bridge Domains (BD)
- Layer 2 forwarding domain
- Associated with one VRF
- Similar to traditional VLAN broadcast domain

#### VRF (Virtual Routing and Forwarding)
- Layer 3 namespace
- Provides routing isolation
- Contains multiple bridge domains

#### Contracts
- Define allowed communication between EPGs
- Replaces traditional ACLs
- Applied between consumer and provider EPGs

---

## Planning Phase

### Phase 1: Assessment and Design (Week 1-2)

#### 1.1 Network Assessment
```bash
# Collect configurations from all Nexus switches
show running-config
show vlan
show interface status
show vpc
show spanning-tree summary
show ip route summary
show mac address-table count
```

#### 1.2 Application Mapping
- Create application-to-VLAN mappings
- Identify inter-application communication patterns
- Document traffic flows between tiers
- Map security requirements to contracts

#### 1.3 ACI Design
- **Tenant Design**: Create tenant structure
  - Common Tenant: Shared services
  - Application Tenant: Application-specific policies
  
- **VRF Design**: 
  - Maintain existing routing domains
  - Plan for VRF overlap if needed
  
- **Bridge Domain Design**:
  - One BD per existing VLAN (initial mapping)
  - Plan subnet configurations
  - Configure gateway IP addresses
  
- **EPG Design**:
  - Map VLANs to EPGs
  - Define static or dynamic port bindings
  - Plan for VMM integration

- **Contract Design**:
  - Document required communication
  - Create security matrix (EPG-to-EPG)
  - Define filters and subjects

#### 1.4 IP Addressing Plan
- **ACI Infrastructure**:
  - TEP Pool: 10.0.0.0/16 (example)
  - Multicast TEP: 225.0.0.0/15
  - Infrastructure VLAN: 4094
  
- **Migration Network**:
  - Transit VLANs for L3Out
  - IP addresses for border leaf connectivity

#### 1.5 Integration Points
- **L3Out Configuration**:
  - Connectivity to existing Nexus core
  - OSPF/BGP peering configuration
  - Route redistribution plan
  
- **VMware Integration**:
  - VMM domain creation
  - vCenter integration
  - Port group automation

### Phase 2: Lab Validation (Week 3-4)

#### 2.1 Build Lab Environment
- Deploy ACI fabric in lab
- Replicate production configurations
- Test migration procedures

#### 2.2 Test Scenarios
- Workload connectivity tests
- Failover scenarios
- Performance benchmarks
- Integration with monitoring tools

#### 2.3 Runbook Validation
- Validate each migration step
- Document timing for each phase
- Identify potential issues
- Create troubleshooting guides

### Phase 3: Production Preparation (Week 5)

#### 3.1 ACI Fabric Deployment
- Rack and stack ACI hardware
- Cable spine-leaf connections
- Connect APIC cluster to OOB network
- Power on and initial configuration

#### 3.2 APIC Cluster Setup
```
# Initial APIC Configuration
Fabric Name: PROD-ACI-FABRIC
Number of Controllers: 3
Controller ID: 1 (for first APIC)
POD ID: 1
TEP Address Pool: 10.0.0.0/16
Multicast Address Pool: 225.0.0.0/15
VLAN ID for Infrastructure: 4094
BD Multicast GIPO: 225.2.0.0/16
```

#### 3.3 Fabric Discovery
- Register spine switches
- Register leaf switches
- Verify fabric health
- Configure NTP and DNS

#### 3.4 Base Configuration
- Create tenants
- Configure VRFs
- Create bridge domains
- Define EPGs
- Create contracts
- Configure L3Out to existing network

---

## Migration Procedure

### Overview
The migration follows a phased approach to minimize risk and allow rollback at each stage. Each phase includes validation steps before proceeding.

### Phase 1: ACI Fabric Preparation (Day 1)

#### Step 1.1: Verify ACI Fabric Health
```
# From APIC GUI
System > Fabric Membership
- Verify all spines and leafs are registered
- Check firmware versions are consistent

Tenants > Fabric > Topology
- Verify all uplinks are operational
- Check for any faults
```

#### Step 1.2: Configure Management Access
```
# APIC Configuration
1. Create admin users and roles
2. Configure AAA (RADIUS/TACACS+ if required)
3. Set up remote syslog
4. Configure SNMP monitoring
5. Enable HTTPS access
```

#### Step 1.3: Create Tenant Structure
```
# Create Application Tenant
Tenants > Add Tenant
Name: Production
Description: Production Applications

# Create VRF
Tenants > Production > Networking > VRFs
Name: PROD-VRF
Policy Control Enforcement: Enforced
```

#### Step 1.4: Configure Bridge Domains
```
# For each of the 20 VLANs, create corresponding BD
Example for VLAN 10:

Tenants > Production > Networking > Bridge Domains
Name: BD-VLAN10
VRF: PROD-VRF
L2 Unknown Unicast: Flood
L3 Configurations:
  - Subnet: 10.10.10.1/24
  - Scope: Public (if need routing)
  - Shared between VRF: No
  - Make this IP address primary: Yes
```

#### Step 1.5: Create Application Profiles and EPGs
```
# Create Application Profile
Tenants > Production > Application Profiles
Name: Three-Tier-App

# Create EPGs (example for web tier)
Application Profiles > Three-Tier-App > Application EPGs
Name: Web-EPG
Bridge Domain: BD-VLAN10
QoS Class: Level3
```

#### Step 1.6: Configure Contracts
```
# Create filters
Tenants > Production > Security Policies > Filters
Name: Web-Filter
Entry: http (TCP 80), https (TCP 443)

# Create contract
Tenants > Production > Security Policies > Contracts
Name: Web-Contract
Subjects > Add Subject
  - Name: Web-Subject
  - Filters: Web-Filter

# Apply contract to EPGs
Provider EPG: Web-EPG
Consumer EPG: App-EPG
Contract: Web-Contract
```

### Phase 2: L3Out Configuration for Integration (Day 1)

#### Step 2.1: Configure L3Out to Existing Nexus Core
```
# Create L3Out
Tenants > Production > Networking > L3Outs
Name: Core-L3Out
VRF: PROD-VRF
L3 Domain: Physical-L3-Domain

# Configure Logical Node Profile
External EPGs > Logical Node Profiles
Name: Border-Leaves
Nodes: Select border leaf switches
Router ID: Assign loopback IPs

# Configure Logical Interface Profile
Logical Node Profiles > Logical Interface Profiles
Name: Uplink-to-Core
Path: Select uplink interface
IP Address: Transit VLAN IP
MTU: 9000
```

#### Step 2.2: Configure Routing Protocol
```
# If using OSPF
L3Out > Core-L3Out > Routing Protocol
Protocol: OSPF
Area ID: 0.0.0.0
Area Type: Regular

# Configure OSPF Interface
Logical Interface Profile > OSPF Interface Profile
Authentication: If required
Network Type: Broadcast or Point-to-Point
```

#### Step 2.3: Configure External EPG
```
# Create External EPG for existing network
L3Out > Core-L3Out > External EPGs
Name: Legacy-Network
Subnet: 0.0.0.0/0 (or specific subnets)
Scope: Import Security, Export Security

# Apply contracts
- Provide contracts for services in ACI
- Consume contracts for services in legacy network
```

#### Step 2.4: Verify L3Out Connectivity
```
# Verify routing adjacency
Tenants > Production > L3Outs > Core-L3Out
- Check OSPF/BGP neighbor status
- Verify route advertisement

# Test connectivity from APIC
Operations > Troubleshooting > Ping
Source: Border Leaf TEP
Destination: Nexus Core IP
```

### Phase 3: Physical Connectivity Preparation (Day 2)

#### Step 3.1: Cable ACI Leaf Switches to Access Layer
```
# Connect servers and ESXi hosts to ACI leaf switches
# Use parallel cabling - don't disconnect from Nexus yet

Physical Connections:
- Server NIC 1 -> Nexus Access Switch (existing)
- Server NIC 2 -> ACI Leaf Switch (new)
- ESXi vmnic0 -> Nexus Access Switch (existing)
- ESXi vmnic1 -> ACI Leaf Switch (new)
```

#### Step 3.2: Configure Interface Policies
```
# Create Interface Policy Group
Fabric > Access Policies > Interface Policies
Name: Server-Policy-Group
Link Level: 1G or 10G
CDP: Enabled
LLDP: Enabled
```

#### Step 3.3: Configure Interface Profiles
```
# Create Leaf Interface Profile
Fabric > Access Policies > Interface Profiles
Name: Leaf101-IntProfile
Interface Selectors: 1/1-1/48
Interface Policy Group: Server-Policy-Group
```

#### Step 3.4: Create Static Port Bindings
```
# Bind EPGs to physical ports
Tenants > Production > Application Profiles > EPGs
Select EPG > Static Ports
Deployment Immediacy: Immediate
Mode: trunk (for ESXi) or access (for servers)
```

### Phase 4: Pilot Migration (Day 3-4)

#### Step 4.1: Select Pilot Workload
- Choose non-critical application
- Select development or test environment
- Ensure proper backup

#### Step 4.2: Prepare Servers/ESXi
```
# For physical servers
1. Configure NIC teaming for both NICs
2. Set secondary NIC as standby
3. Update VLAN tagging if needed

# For ESXi hosts
1. Add second vmnic to distributed switch
2. Configure failover order
3. Place vmnic0 as active, vmnic1 as standby
```

#### Step 4.3: Pre-Migration Validation
```
# Document current state
- Ping test from/to server
- Check application connectivity
- Verify throughput
- Document routing table
- Capture packet captures if needed
```

#### Step 4.4: Perform Cutover
```
# On ESXi (if applicable)
1. vCenter > Host > Configure > Networking
2. Edit Failover Order
3. Move vmnic1 (ACI) to Active
4. Move vmnic0 (Nexus) to Standby

# On Physical Server
1. Change NIC teaming primary adapter
2. Or physically move cable from Nexus to ACI

# Time to complete: ~5 minutes per host
```

#### Step 4.5: Post-Migration Validation
```
# Verify connectivity
1. Ping default gateway
2. Test application access
3. Check ACI learned endpoints
   - Tenants > Operational > Endpoints
4. Verify contract statistics
5. Run application smoke tests
```

#### Step 4.6: Monitor for Issues
- Monitor for 24-48 hours
- Check application logs
- Review ACI health scores
- Validate performance metrics

### Phase 5: Bulk Migration (Day 5-10)

#### Step 5.1: Group Workloads by Application
- Migrate related workloads together
- Follow application dependencies
- Schedule during maintenance windows

#### Step 5.2: Migration Batches
```
Batch 1 (Day 5): Non-production environments
- Development servers
- Test environments
- Validation: 4 hours post-migration

Batch 2 (Day 6): Back-office applications
- Internal tools
- Management systems
- Validation: 4 hours post-migration

Batch 3 (Day 7-8): Production applications (Tier 2)
- Less critical production apps
- Migrate during maintenance window
- Validation: 24 hours post-migration

Batch 4 (Day 9-10): Critical production applications (Tier 1)
- Business-critical applications
- Database servers
- Validation: 48 hours post-migration
```

#### Step 5.3: Batch Migration Process
```
For each batch:
1. Pre-migration validation
2. Perform cutover (following Step 4.4)
3. Immediate validation (15 minutes)
4. Extended monitoring (per schedule)
5. Document any issues
6. Update runbook if needed
```

### Phase 6: VMware ESXi Integration (Day 11)

#### Step 6.1: Create VMM Domain
```
# APIC Configuration
Virtual Networking > VMware > VMM Domain
Name: vCenter-VMM
vCenter Details:
  - vCenter IP: <vCenter IP>
  - Username: <ACI user>
  - Password: <password>
  - Datacenter: <DC name>
```

#### Step 6.2: Associate EPGs with VMM
```
# For each EPG
Tenants > Production > Application Profiles > EPG
Domains: Add VMM Domain
Resolution Immediacy: Immediate
Deployment Immediacy: Immediate

# This creates port groups automatically in vCenter
```

#### Step 6.3: Migrate VM Network Adapters
```
# In vCenter
1. Port groups are created automatically
2. Edit VM network adapter
3. Change from Nexus port group to ACI port group
4. Validate connectivity
```

### Phase 7: Decommission Nexus Access Layer (Day 12-14)

#### Step 7.1: Verify All Workloads Migrated
```
# Check Nexus access switches
show interface status | include connected
show mac address-table dynamic

# Should show minimal or no active connections
```

#### Step 7.2: Graceful Shutdown
```
# On Nexus access switches
1. Remove from vPC domain (if applicable)
2. Shut down uplinks
3. Monitor for any alerts or issues
4. Wait 24 hours
```

#### Step 7.3: Physical Decommission
- Power off access switches
- Remove from racks
- Update asset inventory
- Retain for potential rollback (30 days)

### Phase 8: Optimize ACI Configuration (Day 15-20)

#### Step 8.1: Review and Optimize Contracts
```
# Analyze traffic patterns
Tenants > Operational > Contract Statistics

# Optimize contracts
- Remove unused contracts
- Consolidate similar contracts
- Implement micro-segmentation where needed
```

#### Step 8.2: Implement Advanced Features
```
# Enable endpoint learning optimizations
- IP data plane learning
- Enforce subnet check

# Configure QoS
- Define QoS classes
- Apply to EPGs

# Implement service graph (if needed)
- Load balancers
- Firewalls
```

#### Step 8.3: Automation Integration
```
# Configure REST API access
- Create API users
- Generate certificates
- Document API endpoints

# Integrate with orchestration tools
- Ansible playbooks
- Terraform configurations
- Python scripts
```

### Phase 9: Decommission Nexus Aggregation/Core (Day 21-30)

#### Step 9.1: Update L3Out to External Network
```
# Reconfigure L3Out to external router
- Update L3Out to point to data center edge
- Modify routing protocol configurations
- Advertise routes from ACI
```

#### Step 9.2: Migration L3 Services
```
# Migrate Layer 3 functionality
1. Update default routes
2. Migrate routing protocols to ACI
3. Update firewall adjacencies
4. Update load balancer configurations
```

#### Step 9.3: Decommission Nexus Core/Aggregation
```
# Graceful shutdown process
1. Verify no active traffic
2. Backup final configurations
3. Shut down routing protocols
4. Shut down interfaces
5. Power off devices
6. Update documentation
```

---

## Validation and Testing

### Pre-Migration Validation

#### Network Validation
```bash
# On Nexus switches - document baseline
show interface counters
show interface counters errors
show vlan
show vpc
show ip route summary
show ip arp summary
show spanning-tree summary
```

#### Application Validation
```
# Document working state
1. Application response time
2. Database connectivity
3. User login functionality
4. File access tests
5. External connectivity tests
```

### Post-Migration Validation

#### Step 1: Endpoint Learning Verification
```
# APIC GUI
Tenants > Operational > Endpoints
- Verify all expected endpoints are learned
- Check IP and MAC addresses
- Validate encapsulation (VLAN)
```

#### Step 2: Connectivity Tests
```
# From APIC or leaf switches
# Ping tests between EPGs
Operations > Troubleshooting > Ping
Source: EP in EPG1
Destination: EP in EPG2

# Traceroute to verify path
Operations > Troubleshooting > Traceroute
```

#### Step 3: Contract Verification
```
# Check contract statistics
Tenants > Operational > Contract Statistics
- Verify packet counts
- Check for drops
- Validate security rules

# Test permitted traffic
- Should pass based on contracts

# Test denied traffic
- Should be blocked based on contracts
```

#### Step 4: Fabric Health Check
```
# System-wide health
System > Dashboard
- Check overall health score (should be >90)
- Verify no critical faults

# Fabric health
Tenants > Fabric > Topology
- All links should be up
- No errors on interfaces
```

#### Step 5: Performance Validation
```
# Interface statistics
Fabric > Inventory > Pod > Switches > Interfaces
- Check throughput
- Verify no errors
- Compare to baseline

# Endpoint statistics
Tenants > Operational > Endpoints
- Check transmitted/received packets
- Verify no drops
```

#### Step 6: Routing Validation
```
# Verify L3Out routes
Tenants > Networking > L3Outs > Routing Table
- Check received routes
- Verify advertised routes

# Test external connectivity
- Ping external networks
- Test internet access
- Verify WAN connectivity
```

#### Step 7: Application Testing
```
# End-to-end application tests
1. User login tests
2. Database query tests
3. File transfer tests
4. API endpoint tests
5. Performance benchmarking
```

### Monitoring and Troubleshooting

#### Health Monitoring
```
# Configure health alerts
System > Faults
- Set up email notifications
- Configure syslog forwarding
- Integrate with monitoring tools

# Regular health checks
- Daily: Review dashboard and faults
- Weekly: Analyze performance trends
- Monthly: Capacity planning review
```

#### Common Issues and Solutions

**Issue 1: Endpoint Not Learning**
```
Troubleshooting:
1. Verify physical connectivity
2. Check EPG static port binding
3. Verify VLAN encapsulation
4. Check endpoint IP addressing
5. Review port-channel configuration

Resolution:
- Correct EPG domain association
- Fix VLAN mismatch
- Configure proper encapsulation
```

**Issue 2: Traffic Not Passing Between EPGs**
```
Troubleshooting:
1. Check contract configuration
2. Verify EPG provider/consumer roles
3. Check filter rules
4. Review contract scope
5. Check VRF configuration

Resolution:
- Apply correct contracts
- Fix filter definitions
- Adjust contract scope
```

**Issue 3: L3Out Routing Issues**
```
Troubleshooting:
1. Verify routing protocol adjacency
2. Check route advertisements
3. Verify external EPG subnets
4. Check interface configuration
5. Review transit VLAN connectivity

Resolution:
- Fix routing protocol configuration
- Correct route redistribution
- Update external EPG scope
```

---

## Rollback Procedures

### Rollback Scenarios

#### Scenario 1: Single Workload Rollback
```
Timeframe: 5-10 minutes
Risk: Low

Steps:
1. For physical servers:
   - Change NIC teaming back to Nexus
   - Or move cable back to Nexus port

2. For ESXi VMs:
   - Edit VM network adapter
   - Change port group back to Nexus
   - Or change vmnic failover order

3. Validate connectivity
4. Document rollback reason
```

#### Scenario 2: Batch Rollback
```
Timeframe: 30-60 minutes
Risk: Medium

Prerequisites:
- Nexus configuration still intact
- No changes to Nexus switch configuration

Steps:
1. Rollback workloads in reverse order
2. Follow single workload rollback procedure
3. Verify each workload before proceeding
4. Update migration runbook
5. Analyze root cause
```

#### Scenario 3: Full Migration Rollback
```
Timeframe: 2-4 hours
Risk: High
Decision Point: Within first 7 days

Prerequisites:
- Nexus infrastructure still operational
- Configuration backups available
- Change management approval

Steps:
1. Stop new workload migrations
2. Rollback workloads by application group
3. Restore Nexus configurations if modified
4. Re-enable Nexus core routing
5. Update monitoring systems
6. Conduct post-rollback validation
7. Perform root cause analysis
```

### Rollback Decision Matrix

| Timeline | Scope | Decision Authority | Risk Level |
|----------|-------|-------------------|------------|
| Day 1-3 | Pilot | Operations Team | Low |
| Day 4-7 | Partial | IT Manager | Medium |
| Day 8-14 | Majority | IT Director | High |
| Day 15+ | Full | Executive | Critical |

### Point of No Return

**After Day 21** (when Nexus core is decommissioned):
- Full rollback not feasible
- Only forward-fix options available
- Requires new hardware for Nexus rollback

---

## Post-Migration Tasks

### Week 1 Post-Migration

#### Day 1-3: Intensive Monitoring
```
Activities:
- 24/7 monitoring of fabric health
- Real-time application monitoring
- Rapid response to any issues
- Daily health reports to stakeholders
```

#### Day 4-7: Optimization
```
Activities:
- Review contract usage
- Optimize EPG design
- Fine-tune QoS policies
- Update documentation
```

### Week 2-4 Post-Migration

#### Documentation Updates
```
1. Network diagrams
   - Physical topology
   - Logical topology
   - Application flows

2. Configuration documentation
   - Tenant configurations
   - EPG mappings
   - Contract definitions
   - L3Out configurations

3. Operational procedures
   - Daily operations
   - Troubleshooting guides
   - Escalation procedures
```

#### Knowledge Transfer
```
Training Sessions:
1. ACI Architecture Overview (4 hours)
2. Daily Operations (2 hours)
3. Troubleshooting (4 hours)
4. Advanced Features (2 hours)

Hands-on Labs:
- Creating tenants and EPGs
- Modifying contracts
- Troubleshooting connectivity
- Adding new workloads
```

#### Automation Development
```
1. Provisioning automation
   - New EPG creation
   - Contract templates
   - Port binding automation

2. Monitoring automation
   - Health score alerts
   - Capacity thresholds
   - Performance baselines

3. Backup automation
   - Configuration backups
   - Scheduled exports
   - Version control
```

### Month 2-3 Post-Migration

#### Performance Optimization
```
1. Review traffic patterns
   - Identify hotspots
   - Optimize flow distribution
   - Adjust QoS policies

2. Capacity planning
   - Forecast growth
   - Plan leaf expansion
   - Evaluate bandwidth needs
```

#### Advanced Features Implementation
```
1. Micro-segmentation
   - Implement zero-trust security
   - Create micro-EPGs
   - Granular contracts

2. Service graphs
   - Integrate load balancers
   - Add firewall services
   - Deploy SSL offload

3. Multi-site integration (if applicable)
   - Configure multi-site orchestrator
   - Extend policies across sites
   - Implement stretched EPGs
```

#### Process Integration
```
1. Change management
   - Update change procedures
   - Define approval workflows
   - Document standard changes

2. Incident management
   - Update incident response
   - Define escalation paths
   - Create troubleshooting guides

3. Monitoring integration
   - SNMP integration
   - Syslog forwarding
   - API-based monitoring
```

---

## Best Practices and Recommendations

### Design Best Practices

#### Tenant Design
```
Recommended Approach:
- Separate tenants by business unit or security requirement
- Use common tenant for shared services
- Implement tenant isolation for compliance requirements

Example Structure:
- Common Tenant: DNS, NTP, Monitoring
- Production Tenant: Production applications
- Development Tenant: Dev/Test environments
```

#### VRF Design
```
Best Practices:
- One VRF per security zone
- Avoid overlapping IP addresses
- Plan for VRF routing leaking if needed
- Use meaningful names (PROD-VRF, DMZ-VRF)
```

#### Bridge Domain Configuration
```
Recommendations:
- Enable unicast routing for L3 communication
- Configure appropriate L2 unknown unicast mode
- Set correct ARP flooding policy
- Optimize L3Out associations
```

#### EPG Design
```
Best Practices:
- Group endpoints with similar security requirements
- Use descriptive naming conventions
- Leverage VMM integration for VMs
- Plan for EPG preferred groups if needed

Naming Convention Example:
<Tenant>-<AppProfile>-<Tier>-EPG
PROD-3Tier-Web-EPG
PROD-3Tier-App-EPG
PROD-3Tier-DB-EPG
```

#### Contract Design
```
Recommendations:
- Start with minimal contracts (least privilege)
- Use subjects to group related filters
- Implement taboo contracts for explicit deny
- Regular contract audits and cleanup

Contract Strategy:
- Default: Deny all
- Explicit: Allow only required traffic
- Document: Each contract purpose
- Review: Quarterly contract usage
```

### Operational Best Practices

#### Configuration Management
```
1. Version Control
   - Export configurations regularly
   - Maintain configuration history
   - Document all changes

2. Backup Strategy
   - Automated daily backups
   - Off-site backup storage
   - Test restore procedures quarterly

3. Change Control
   - All changes through change management
   - Document rationale for changes
   - Schedule changes during maintenance windows
```

#### Monitoring and Alerting
```
1. Health Score Monitoring
   - Alert on health score < 90
   - Daily health reports
   - Trend analysis

2. Critical Alerts
   - Fabric link down
   - APIC cluster issues
   - Critical fault events

3. Capacity Monitoring
   - Interface utilization
   - Endpoint scale
   - Contract scale
```

#### Security Best Practices
```
1. Access Control
   - Implement role-based access control (RBAC)
   - Use strong passwords
   - Enable MFA for administrative access
   - Regular access reviews

2. Security Policies
   - Default deny posture
   - Micro-segmentation for critical apps
   - Regular security audits
   - Compliance reporting

3. Network Security
   - Disable unused ports
   - Configure port security
   - Enable DHCP snooping
   - Implement dynamic ARP inspection
```

### Performance Optimization

#### Fabric Optimization
```
1. Load Balancing
   - Utilize ECMP across spine switches
   - Balance workload across leaf switches
   - Optimize vPC+ configurations

2. MTU Configuration
   - Enable jumbo frames (9000 MTU)
   - Consistent MTU across fabric
   - Verify endpoint MTU support

3. QoS Configuration
   - Classify traffic appropriately
   - Configure priority flow control if needed
   - Monitor queue depths
```

#### Endpoint Optimization
```
1. Endpoint Learning
   - Enable IP data plane learning
   - Configure enforce subnet check
   - Optimize endpoint retention policies

2. Multicast Optimization
   - Configure PIM for multicast traffic
   - Optimize multicast tree building
   - Use L3 multicast where possible
```

### Scalability Considerations

#### Planning for Growth
```
1. Leaf Switch Capacity
   - Monitor endpoint count per leaf
   - Plan for 80% utilization maximum
   - Add leaf pairs as needed

2. Spine Capacity
   - Monitor spine bandwidth utilization
   - Plan for 50% utilization for growth
   - Add spines before 70% utilization

3. APIC Cluster
   - Maintain 3-node cluster minimum
   - Monitor CPU and memory
   - Plan for controller replacement cycle
```

#### Scale Limits
```
Important Scale Numbers (varies by platform):
- Endpoints per leaf: ~6000-12000
- EPGs per leaf: ~3500
- Contracts: ~10000
- Tenants: ~3000

Recommendation: Operate at 60-70% of maximum scale
```

### Documentation Standards

#### Required Documentation
```
1. Architecture Documentation
   - High-level design
   - Network topology diagrams
   - Policy model documentation

2. Configuration Documentation
   - Tenant configurations
   - VLAN to EPG mappings
   - Contract definitions
   - L3Out configurations

3. Operational Documentation
   - Standard operating procedures
   - Troubleshooting guides
   - Runbooks for common tasks

4. Contact Information
   - Support escalation
   - Vendor contacts
   - Emergency procedures
```

#### Documentation Format
```
Recommended Structure:
1. Executive Summary
2. Architecture Overview
3. Detailed Configurations
4. Operational Procedures
5. Troubleshooting
6. Appendices

Update Frequency:
- After each change
- Quarterly reviews
- Annual comprehensive review
```

---

## References

### Cisco Documentation

#### ACI Configuration Guides
- [Cisco APIC Getting Started Guide](https://www.cisco.com/c/en/us/support/cloud-systems-management/application-policy-infrastructure-controller-apic/products-installation-and-configuration-guides-list.html)
- [Cisco ACI Fundamentals](https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/5x/fundamentals/cisco-apic-fundamentals-52x.html)
- [Cisco ACI Policy Model](https://www.cisco.com/c/en/us/td/docs/dcn/aci/apic/5x/policy-model/cisco-apic-policy-model-52x.html)

#### Cisco Validated Designs
- [Cisco Data Center Design Guide](https://www.cisco.com/c/en/us/solutions/design-zone/data-center-design-guides/index.html)
- [ACI Multi-Site Design Guide](https://www.cisco.com/c/en/us/td/docs/dcn/mso/design/aci-multi-site-design-guide.html)
- [ACI with VMware vSphere Design Guide](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-742371.html)

#### Migration Guides
- [Migrating to Cisco ACI](https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/guide-c07-734097.html)
- [ACI Migration Tool User Guide](https://www.cisco.com/c/en/us/support/cloud-systems-management/application-policy-infrastructure-controller-apic/products-user-guide-list.html)

### Best Practices Documentation
- [Cisco ACI Best Practices Quick Summary](https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-aci-best-practices-quick-summary.html)
- [ACI Operations Guide](https://www.cisco.com/c/en/us/support/cloud-systems-management/application-policy-infrastructure-controller-apic/products-maintenance-guides-list.html)
- [ACI Troubleshooting Guide](https://www.cisco.com/c/en/us/support/docs/cloud-systems-management/application-policy-infrastructure-controller-apic/119001-technote-apic-00.html)

### Training Resources
- [Cisco ACI Learning Path](https://learningnetwork.cisco.com/s/aci-learning-path)
- [ACI Fundamentals (On-Demand Training)](https://learningnetwork.cisco.com)
- [DevNet ACI Learning Labs](https://developer.cisco.com/learning/tracks/aci-programmability)

### Community Resources
- [Cisco Community - ACI Forum](https://community.cisco.com/t5/application-centric/bd-p/discussions-data-center-aci)
- [ACI GitHub Examples](https://github.com/datacenter)
- [ACI Code Exchange](https://developer.cisco.com/codeexchange/explore/#tech=ACI)

### Tools and Automation
- [Cisco ACI Toolkit](https://github.com/datacenter/acitoolkit)
- [ACI Ansible Collection](https://galaxy.ansible.com/cisco/aci)
- [Terraform ACI Provider](https://registry.terraform.io/providers/CiscoDevNet/aci/latest/docs)
- [Python SDK for ACI](https://github.com/datacenter/cobra)

### Additional Resources
- [Cisco Live Presentations](https://www.ciscolive.com/global/on-demand-library.html) - Search for "ACI"
- [ACI Whitepapers](https://www.cisco.com/c/en/us/products/cloud-systems-management/application-policy-infrastructure-controller-apic/white-paper-listing.html)
- [Data Center Design Zone](https://www.cisco.com/c/en/us/solutions/design-zone/data-center-design-guides/index.html)

---

## Appendices

### Appendix A: Pre-Migration Checklist

```
Network Assessment:
☐ Document all Nexus switch configurations
☐ Map all VLANs and subnets
☐ Document vPC configurations
☐ Identify all connected endpoints
☐ Document routing protocols and configurations
☐ Map application dependencies
☐ Identify security policies and ACLs
☐ Document QoS policies
☐ Backup all configurations

ACI Preparation:
☐ Procure ACI hardware (APIC, Spine, Leaf)
☐ Verify firmware compatibility
☐ Plan IP addressing (TEP pool, infra VLAN)
☐ Design tenant structure
☐ Design VRF architecture
☐ Map VLANs to Bridge Domains and EPGs
☐ Design contract structure
☐ Plan L3Out configuration
☐ Design VMM integration

Lab Validation:
☐ Build lab environment
☐ Test migration procedures
☐ Validate application connectivity
☐ Test failover scenarios
☐ Document timing and issues

Change Management:
☐ Create change request
☐ Obtain approvals
☐ Schedule maintenance windows
☐ Notify stakeholders
☐ Prepare rollback plan

Team Preparation:
☐ Train operations team on ACI
☐ Assign roles and responsibilities
☐ Prepare runbooks
☐ Set up communication channels
☐ Prepare monitoring and alerting
```

### Appendix B: VLAN to EPG Mapping Template

```
| VLAN ID | VLAN Name | Subnet | Gateway | Tenant | Bridge Domain | EPG | Notes |
|---------|-----------|--------|---------|--------|---------------|-----|-------|
| 10 | Web-VLAN | 10.10.10.0/24 | 10.10.10.1 | PROD | BD-Web | Web-EPG | Web Tier |
| 20 | App-VLAN | 10.10.20.0/24 | 10.10.20.1 | PROD | BD-App | App-EPG | App Tier |
| 30 | DB-VLAN | 10.10.30.0/24 | 10.10.30.1 | PROD | BD-DB | DB-EPG | Database |
| 40 | Mgmt-VLAN | 10.10.40.0/24 | 10.10.40.1 | COMMON | BD-Mgmt | Mgmt-EPG | Management |
| ... | ... | ... | ... | ... | ... | ... | ... |
```

### Appendix C: Contract Matrix Template

```
| Provider EPG | Consumer EPG | Contract | Filters | Ports | Description |
|--------------|--------------|----------|---------|-------|-------------|
| Web-EPG | Internet-EPG | Web-Contract | HTTP, HTTPS | 80, 443 | Web access |
| App-EPG | Web-EPG | App-Contract | Custom | 8080 | App tier access |
| DB-EPG | App-EPG | DB-Contract | MySQL | 3306 | Database access |
| ... | ... | ... | ... | ... | ... |
```

### Appendix D: Migration Timeline Template

```
| Phase | Activities | Duration | Responsible | Status |
|-------|------------|----------|-------------|--------|
| Assessment | Network documentation | 2 weeks | Network Team | Not Started |
| Design | ACI design and planning | 2 weeks | Architect | Not Started |
| Lab Testing | Build and test lab | 2 weeks | Network Team | Not Started |
| Deployment | Deploy ACI fabric | 1 week | Network Team | Not Started |
| Migration Pilot | Migrate pilot workload | 2 days | Migration Team | Not Started |
| Bulk Migration | Migrate all workloads | 1 week | Migration Team | Not Started |
| Optimization | Optimize and tune | 1 week | Network Team | Not Started |
| Decommission | Remove legacy equipment | 2 weeks | Network Team | Not Started |
```

### Appendix E: Troubleshooting Quick Reference

```
Issue: Endpoint not learning
Check:
1. Physical connectivity
2. EPG static port binding
3. VLAN configuration
4. CDP/LLDP neighbors
Command: show endpoint

Issue: No communication between EPGs
Check:
1. Contract configuration
2. Provider/Consumer relationships
3. Filter rules
4. Contract scope
Command: show contract, show zoning-rule

Issue: L3Out not working
Check:
1. Routing protocol status
2. Interface configuration
3. External EPG subnet configuration
4. Route advertisement
Command: show ip route, show bgp summary

Issue: High latency
Check:
1. Interface errors
2. Queue drops
3. Fabric health
4. Spine bandwidth utilization
Command: show interface counters, show system internal eltmc info

Issue: Policy not applying
Check:
1. EPG domain association
2. Resolution immediacy
3. Deployment immediacy
4. Fault events
Command: show faults
```

### Appendix F: Glossary

**ACI (Application Centric Infrastructure)**: Cisco's software-defined networking (SDN) solution for data centers.

**APIC (Application Policy Infrastructure Controller)**: Centralized controller for ACI fabric management and policy enforcement.

**BD (Bridge Domain)**: Layer 2 forwarding construct in ACI, similar to a VLAN broadcast domain.

**Contract**: Policy construct that defines allowed communication between EPGs.

**EPG (Endpoint Group)**: Collection of endpoints with similar policy requirements.

**Fabric**: The collection of spine and leaf switches forming the ACI network.

**Filter**: Defines specific protocols and ports for contract rules.

**L3Out**: External Layer 3 connectivity from ACI fabric to outside networks.

**Leaf Switch**: Switch in ACI fabric that connects to endpoints (servers, storage).

**Spine Switch**: Switch in ACI fabric that provides interconnection between leaf switches.

**Subject**: Container within a contract that associates filters with directives.

**TEP (Tunnel Endpoint)**: IP address used for VXLAN tunneling in ACI fabric.

**Tenant**: Top-level policy container that represents a unit of isolation.

**VRF (Virtual Routing and Forwarding)**: Layer 3 namespace providing routing isolation.

**VMM (Virtual Machine Manager)**: Integration between ACI and virtualization platforms like VMware.

**VXLAN**: Overlay encapsulation protocol used in ACI fabric.

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024 | Network Team | Initial document creation |

---

**End of Migration Guide**

For questions or clarifications, contact your network architecture team or Cisco support.
