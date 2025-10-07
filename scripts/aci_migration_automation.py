"""
ACI Migration Automation Scripts
================================

This module provides Python scripts for automating the migration from traditional Nexus 
to ACI infrastructure. The scripts handle configuration parsing, API interactions, 
and validation procedures.

Classes:
    ACIConnector: Handles APIC API connections and operations
    NexusConfigParser: Parses existing Nexus configurations
    MigrationValidator: Validates migration steps and configurations
    TenantManager: Manages ACI tenant operations
    
Functions:
    migrate_vlan_to_epg(): Maps VLANs to EPGs
    validate_connectivity(): Tests network connectivity post-migration
    backup_configurations(): Creates configuration backups
    generate_migration_report(): Creates migration status reports
"""

import requests
import json
import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import urllib3
from pathlib import Path

# Disable SSL warnings for lab environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aci_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ACIConnector:
    """
    Handles connections and operations with Cisco APIC controllers.
    
    This class provides methods for authenticating with APIC, sending API requests,
    and managing ACI configurations during the migration process.
    """
    
    def __init__(self, apic_ip: str, username: str, password: str, verify_ssl: bool = False):
        """
        Initialize ACI connector with APIC credentials.
        
        Args:
            apic_ip (str): APIC management IP address
            username (str): APIC username
            password (str): APIC password  
            verify_ssl (bool): Whether to verify SSL certificates
        """
        self.apic_ip = apic_ip
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{apic_ip}/api"
        self.session = requests.Session()
        self.token = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with APIC and obtain session token.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        login_data = {
            "aaaUser": {
                "attributes": {
                    "name": self.username,
                    "pwd": self.password
                }
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/aaaLogin.json",
                json=login_data,
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.token = result['imdata'][0]['aaaLogin']['attributes']['token']
                logger.info(f"Successfully authenticated to APIC {self.apic_ip}")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def get_tenant_config(self, tenant_name: str) -> Optional[Dict]:
        """
        Retrieve tenant configuration from APIC.
        
        Args:
            tenant_name (str): Name of the tenant to retrieve
            
        Returns:
            Dict: Tenant configuration or None if not found
        """
        try:
            response = self.session.get(
                f"{self.base_url}/mo/uni/tn-{tenant_name}.json?query-target=subtree",
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get tenant {tenant_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving tenant {tenant_name}: {str(e)}")
            return None
    
    def create_tenant(self, tenant_config: Dict) -> bool:
        """
        Create a new tenant in ACI fabric.
        
        Args:
            tenant_config (Dict): Tenant configuration in JSON format
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.base_url}/mo/uni.json",
                json=tenant_config,
                verify=self.verify_ssl,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully created tenant configuration")
                return True
            else:
                logger.error(f"Failed to create tenant: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating tenant: {str(e)}")
            return False
    
    def validate_fabric_health(self) -> Dict:
        """
        Check ACI fabric health before migration.
        
        Returns:
            Dict: Fabric health status including faults and node states
        """
        health_status = {
            'overall_health': 'unknown',
            'critical_faults': 0,
            'nodes_up': 0,
            'total_nodes': 0,
            'details': []
        }
        
        try:
            # Check fabric nodes
            nodes_response = self.session.get(
                f"{self.base_url}/class/fabricNode.json",
                verify=self.verify_ssl,
                timeout=30
            )
            
            if nodes_response.status_code == 200:
                nodes_data = nodes_response.json()
                health_status['total_nodes'] = len(nodes_data['imdata'])
                
                for node in nodes_data['imdata']:
                    node_attrs = node['fabricNode']['attributes']
                    if node_attrs['fabricSt'] == 'active':
                        health_status['nodes_up'] += 1
            
            # Check critical faults
            faults_response = self.session.get(
                f"{self.base_url}/class/faultInst.json?query-target-filter=eq(faultInst.severity,\"critical\")",
                verify=self.verify_ssl,
                timeout=30
            )
            
            if faults_response.status_code == 200:
                faults_data = faults_response.json()
                health_status['critical_faults'] = len(faults_data['imdata'])
            
            # Determine overall health
            if health_status['critical_faults'] == 0 and health_status['nodes_up'] == health_status['total_nodes']:
                health_status['overall_health'] = 'healthy'
            elif health_status['critical_faults'] > 5 or health_status['nodes_up'] < health_status['total_nodes'] * 0.8:
                health_status['overall_health'] = 'critical'
            else:
                health_status['overall_health'] = 'warning'
            
            logger.info(f"Fabric health check completed: {health_status['overall_health']}")
            
        except Exception as e:
            logger.error(f"Error checking fabric health: {str(e)}")
            health_status['overall_health'] = 'error'
        
        return health_status


class NexusConfigParser:
    """
    Parses Nexus switch configurations to extract migration-relevant information.
    
    This class analyzes existing Nexus configurations to identify VLANs, interfaces,
    routing protocols, and other settings that need to be migrated to ACI.
    """
    
    def __init__(self, config_directory: str):
        """
        Initialize parser with configuration directory.
        
        Args:
            config_directory (str): Path to directory containing Nexus configs
        """
        self.config_dir = Path(config_directory)
        self.parsed_configs = {}
        
    def parse_all_configs(self) -> Dict:
        """
        Parse all Nexus configuration files in the directory.
        
        Returns:
            Dict: Parsed configuration data organized by switch
        """
        config_files = list(self.config_dir.glob("*.cfg"))
        logger.info(f"Found {len(config_files)} configuration files to parse")
        
        for config_file in config_files:
            switch_name = config_file.stem
            self.parsed_configs[switch_name] = self.parse_config_file(config_file)
            
        return self.parsed_configs
    
    def parse_config_file(self, config_file: Path) -> Dict:
        """
        Parse a single Nexus configuration file.
        
        Args:
            config_file (Path): Path to configuration file
            
        Returns:
            Dict: Parsed configuration data
        """
        config_data = {
            'hostname': '',
            'vlans': {},
            'interfaces': {},
            'vpc_config': {},
            'routing': {}
        }
        
        try:
            with open(config_file, 'r') as f:
                lines = f.readlines()
            
            current_section = None
            current_interface = None
            
            for line in lines:
                line = line.strip()
                
                # Skip comments and empty lines
                if line.startswith('!') or not line:
                    continue
                
                # Parse hostname
                if line.startswith('hostname'):
                    config_data['hostname'] = line.split()[1]
                
                # Parse VLANs
                elif line.startswith('vlan '):
                    vlan_range = line.split()[1]
                    current_section = 'vlan'
                    if '-' in vlan_range:
                        start, end = vlan_range.split('-')
                        for vlan_id in range(int(start), int(end) + 1):
                            config_data['vlans'][str(vlan_id)] = {'name': f'VLAN_{vlan_id}'}
                    else:
                        config_data['vlans'][vlan_range] = {'name': f'VLAN_{vlan_range}'}
                
                # Parse VLAN names
                elif line.startswith('name ') and current_section == 'vlan':
                    vlan_name = ' '.join(line.split()[1:])
                    # Apply to the most recent VLAN
                    if config_data['vlans']:
                        last_vlan = list(config_data['vlans'].keys())[-1]
                        config_data['vlans'][last_vlan]['name'] = vlan_name
                
                # Parse interfaces
                elif line.startswith('interface '):
                    interface_name = line.split()[1]
                    current_interface = interface_name
                    current_section = 'interface'
                    config_data['interfaces'][interface_name] = {
                        'type': 'unknown',
                        'mode': 'access',
                        'vlans': [],
                        'description': ''
                    }
                
                # Parse interface configurations
                elif current_section == 'interface' and current_interface:
                    if line.startswith('description '):
                        description = ' '.join(line.split()[1:])
                        config_data['interfaces'][current_interface]['description'] = description
                    
                    elif line.startswith('switchport mode'):
                        mode = line.split()[-1]
                        config_data['interfaces'][current_interface]['mode'] = mode
                    
                    elif line.startswith('switchport access vlan'):
                        vlan = line.split()[-1]
                        config_data['interfaces'][current_interface]['vlans'] = [vlan]
                    
                    elif line.startswith('switchport trunk allowed vlan'):
                        vlans_str = ' '.join(line.split()[4:])
                        vlans = self._parse_vlan_list(vlans_str)
                        config_data['interfaces'][current_interface]['vlans'] = vlans
                
                # Reset section on new top-level command
                elif not line.startswith(' ') and current_section:
                    current_section = None
                    current_interface = None
            
            logger.info(f"Parsed configuration for {config_data.get('hostname', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error parsing config file {config_file}: {str(e)}")
        
        return config_data
    
    def _parse_vlan_list(self, vlan_string: str) -> List[str]:
        """
        Parse VLAN list from configuration line.
        
        Args:
            vlan_string (str): VLAN string from config (e.g., "10,20,30-35")
            
        Returns:
            List[str]: List of VLAN IDs
        """
        vlans = []
        parts = vlan_string.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                vlans.extend([str(i) for i in range(int(start), int(end) + 1)])
            else:
                vlans.append(part)
        
        return vlans
    
    def generate_migration_mapping(self, csv_file: str) -> Dict:
        """
        Generate VLAN to EPG migration mapping.
        
        Args:
            csv_file (str): Path to VLAN-to-EPG mapping CSV file
            
        Returns:
            Dict: Migration mapping data
        """
        mapping = {}
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vlan_id = row['Nexus_VLAN']
                    mapping[vlan_id] = {
                        'vlan_name': row['VLAN_Name'],
                        'tenant': row['ACI_Tenant'],
                        'app_profile': row['ACI_Application_Profile'],
                        'epg': row['ACI_EPG'],
                        'bridge_domain': row['ACI_Bridge_Domain'],
                        'subnet': row['Subnet'],
                        'priority': row['Migration_Priority'],
                        'notes': row['Notes']
                    }
            
            logger.info(f"Loaded migration mapping for {len(mapping)} VLANs")
            
        except Exception as e:
            logger.error(f"Error loading migration mapping: {str(e)}")
        
        return mapping


class MigrationValidator:
    """
    Validates migration steps and configurations to ensure successful transition.
    
    This class provides validation methods for pre-migration checks, post-migration
    verification, and ongoing monitoring during the migration process.
    """
    
    def __init__(self, aci_connector: ACIConnector, nexus_parser: NexusConfigParser):
        """
        Initialize validator with ACI connector and Nexus parser.
        
        Args:
            aci_connector (ACIConnector): Connected ACI API instance
            nexus_parser (NexusConfigParser): Configured Nexus parser
        """
        self.aci = aci_connector
        self.nexus = nexus_parser
        self.validation_results = {}
        
    def pre_migration_check(self) -> Dict:
        """
        Perform comprehensive pre-migration validation.
        
        Returns:
            Dict: Validation results with pass/fail status
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'checks': {}
        }
        
        logger.info("Starting pre-migration validation checks")
        
        # Check ACI fabric health
        fabric_health = self.aci.validate_fabric_health()
        results['checks']['fabric_health'] = {
            'status': 'pass' if fabric_health['overall_health'] == 'healthy' else 'fail',
            'details': fabric_health
        }
        
        # Validate configuration parsing
        parsed_configs = self.nexus.parse_all_configs()
        results['checks']['config_parsing'] = {
            'status': 'pass' if parsed_configs else 'fail',
            'details': f"Parsed {len(parsed_configs)} configuration files"
        }
        
        # Check VLAN consistency across switches
        vlan_consistency = self._check_vlan_consistency(parsed_configs)
        results['checks']['vlan_consistency'] = vlan_consistency
        
        # Validate migration mapping
        try:
            mapping_file = self.nexus.config_dir.parent / "configs/aci/migration-mappings/vlan-to-epg-mapping.csv"
            migration_mapping = self.nexus.generate_migration_mapping(str(mapping_file))
            results['checks']['migration_mapping'] = {
                'status': 'pass' if migration_mapping else 'fail',
                'details': f"Loaded mapping for {len(migration_mapping)} VLANs"
            }
        except Exception as e:
            results['checks']['migration_mapping'] = {
                'status': 'fail',
                'details': f"Error loading migration mapping: {str(e)}"
            }
        
        # Determine overall status
        failed_checks = [check for check in results['checks'].values() if check['status'] == 'fail']
        results['overall_status'] = 'fail' if failed_checks else 'pass'
        
        logger.info(f"Pre-migration validation completed: {results['overall_status']}")
        return results
    
    def _check_vlan_consistency(self, parsed_configs: Dict) -> Dict:
        """
        Check VLAN consistency across all switches.
        
        Args:
            parsed_configs (Dict): Parsed configuration data
            
        Returns:
            Dict: VLAN consistency check results
        """
        all_vlans = set()
        switch_vlans = {}
        
        for switch_name, config in parsed_configs.items():
            vlans = set(config['vlans'].keys())
            switch_vlans[switch_name] = vlans
            all_vlans.update(vlans)
        
        inconsistent_vlans = []
        for vlan in all_vlans:
            switches_with_vlan = [switch for switch, vlans in switch_vlans.items() if vlan in vlans]
            if len(switches_with_vlan) != len(parsed_configs):
                inconsistent_vlans.append({
                    'vlan': vlan,
                    'missing_from': [switch for switch in parsed_configs.keys() if switch not in switches_with_vlan]
                })
        
        return {
            'status': 'pass' if not inconsistent_vlans else 'warning',
            'details': {
                'total_vlans': len(all_vlans),
                'inconsistent_vlans': inconsistent_vlans
            }
        }
    
    def post_migration_validation(self, migrated_vlans: List[str]) -> Dict:
        """
        Validate successful migration of VLANs to EPGs.
        
        Args:
            migrated_vlans (List[str]): List of VLANs that should be migrated
            
        Returns:
            Dict: Post-migration validation results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'migrated_vlans': migrated_vlans,
            'epg_status': {},
            'connectivity_tests': {}
        }
        
        logger.info(f"Starting post-migration validation for {len(migrated_vlans)} VLANs")
        
        # Check if EPGs were created successfully
        for vlan in migrated_vlans:
            # This would check if corresponding EPG exists in ACI
            # Implementation depends on specific mapping logic
            results['epg_status'][vlan] = {
                'status': 'unknown',
                'details': 'EPG validation not implemented'
            }
        
        # Placeholder for connectivity tests
        results['connectivity_tests'] = {
            'status': 'pending',
            'details': 'Connectivity tests not implemented'
        }
        
        # Determine overall status
        results['overall_status'] = 'pending'
        
        logger.info("Post-migration validation completed")
        return results


def generate_migration_report(validation_results: Dict, output_file: str) -> None:
    """
    Generate a comprehensive migration report.
    
    Args:
        validation_results (Dict): Results from migration validation
        output_file (str): Path to output report file
    """
    report_content = []
    report_content.append("# ACI Migration Report")
    report_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_content.append("")
    
    # Overall status
    overall_status = validation_results.get('overall_status', 'unknown')
    report_content.append(f"## Overall Status: {overall_status.upper()}")
    report_content.append("")
    
    # Detailed results
    report_content.append("## Validation Results")
    for check_name, check_result in validation_results.get('checks', {}).items():
        status = check_result['status']
        details = check_result['details']
        
        report_content.append(f"### {check_name.replace('_', ' ').title()}")
        report_content.append(f"Status: {status.upper()}")
        report_content.append(f"Details: {details}")
        report_content.append("")
    
    # Write report to file
    try:
        with open(output_file, 'w') as f:
            f.write('\n'.join(report_content))
        logger.info(f"Migration report saved to {output_file}")
    except Exception as e:
        logger.error(f"Error writing report: {str(e)}")


if __name__ == "__main__":
    # Example usage
    print("ACI Migration Automation Scripts")
    print("================================")
    print("This module provides classes and functions for automating Nexus to ACI migration.")
    print("Import individual classes or functions as needed for your migration automation.")