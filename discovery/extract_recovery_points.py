#!/usr/bin/env python3
import boto3
import json
import concurrent.futures
from typing import List, Dict

def get_backup_vaults() -> List[str]:
    """Get all backup vault names"""
    client = boto3.client('backup')
    paginator = client.get_paginator('list_backup_vaults')
    vaults = []
    for page in paginator.paginate():
        vaults.extend([vault['BackupVaultName'] for vault in page['BackupVaults']])
    return vaults

def extract_vault_recovery_points(vault_name: str) -> List[Dict]:
    """Extract all recovery points from a single vault"""
    client = boto3.client('backup')
    paginator = client.get_paginator('list_recovery_points_by_backup_vault')
    recovery_points = []
    
    for page in paginator.paginate(BackupVaultName=vault_name):
        for rp in page['RecoveryPoints']:
            recovery_points.append({
                'recoveryPointArn': rp['RecoveryPointArn'],
                'resourceArn': rp['ResourceArn']
            })
    
    print(f"Vault {vault_name}: {len(recovery_points)} recovery points")
    return recovery_points

def main():
    print("Getting backup vaults...")
    vaults = get_backup_vaults()
    print(f"Found {len(vaults)} vaults")
    
    all_recovery_points = []
    
    # Process vaults in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_vault_recovery_points, vault): vault for vault in vaults}
        
        for future in concurrent.futures.as_completed(futures):
            vault_recovery_points = future.result()
            all_recovery_points.extend(vault_recovery_points)
    
    # Save to JSON file
    with open('recovery_points.json', 'w') as f:
        json.dump(all_recovery_points, f, indent=2)
    
    print(f"Extracted {len(all_recovery_points)} recovery points to recovery_points.json")

if __name__ == "__main__":
    main()