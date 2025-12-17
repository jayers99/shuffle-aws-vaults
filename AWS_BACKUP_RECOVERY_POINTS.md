# AWS Backup Recovery Points: Comprehensive Guide

## 1. What is a Recovery Point?

A **recovery point** is a backup of your AWS resource at a specific point in time. It's stored in a backup vault and contains the data necessary to restore your resource to that state. Recovery points are created based on:
- **Scheduled backups** (through backup plans)
- **On-demand backups** (manually triggered)
- **Continuous backups** (for point-in-time recovery)

---

## 2. What is BackupSizeInBytes and Why Does It Stay the Same?

This is the most important insight from the documentation:

**BackupSizeInBytes represents the size of the INCREMENTAL backup**, not cumulative. Here's why all recovery points for the same resource show similar or identical sizes:

- **First backup**: Full copy of all data
- **Subsequent backups**: Only the *changes* (deltas) since the previous backup are backed up
- **BackupSizeInBytes**: Reflects only the size of what was captured in that specific backup operation, not the total data to restore

### Example

If a database is 100GB and you take backups daily with minimal changes:
- **Day 1**: BackupSizeInBytes ≈ 100GB (full backup)
- **Day 2**: BackupSizeInBytes ≈ 50MB (only the changes)
- **Day 3**: BackupSizeInBytes ≈ 100MB (only the changes)
- **Day N**: BackupSizeInBytes ≈ varies (only the changes)

The sizes won't consistently increase because each recovery point is **independent and only stores the incremental data captured at that time**.

---

## 3. Incremental Backup Chain Dependency

Here's the critical architectural detail from AWS documentation:

> "Although each backup after the first (full) one is incremental (meaning it only captures changes from the previous backup), **all backups made with AWS Backup retain the necessary reference data to allow a full restore. This is true even if the original (full) backup has reached the end of its lifecycle and been deleted.**"

This means:
- **No hard chain dependency**: You can delete Day 1's full backup, and Day 2-N backups still contain all necessary reference data to restore
- **Self-contained recovery**: Each recovery point maintains enough metadata to reconstruct the full data state
- **Safe deletion**: Even if older backups expire due to lifecycle policies, newer incremental backups remain functional

---

## 4. Copying the Last Recovery Point

When you copy the **most recent recovery point** to another account/region:

### What Gets Copied

- AWS Backup copies the recovery point in **full** when copying to a new region/account for the first time
- This includes all necessary reference data from all previous incremental backups
- Subsequent copies of that same recovery point are **incremental** (if the service supports it)

### Data Transfer

- **Yes, you copy all the data**: The last recovery point contains all the reference data needed to restore the complete resource state, so a full copy is performed
- This is the "full data set" that represents the resource's state at that point in time

---

## 5. Impact on Point-in-Time Restore (PITR)

### Key Limitations and Effects

#### 1. PITR ≠ Periodic Backups
- PITR uses **continuous backups** (not periodic recovery points)
- On-demand backups **cannot** be used for PITR
- If you're copying only periodic recovery points, you lose granular PITR capability

#### 2. Restore Limitations by Recovery Point Type
- **Periodic backup** (like the last recovery point): Can only restore to the exact timestamp of that backup
- **Continuous backup**: Can restore to any point within the retention window

#### 3. If You Copy Only the Last Recovery Point
- ✅ You can restore to the exact time the last backup was taken
- ❌ You cannot restore to intermediate times between backups
- ❌ You lose the ability to recover from data corruption at an earlier time
- ❌ You lose PITR capability if that backup is periodic rather than continuous

### Example Scenario

If you backup daily and data corruption occurs on Day 5, but you only copied the Day 7 recovery point:
- You can restore to Day 7 state (data already corrupted)
- You cannot restore to Day 4 state (backup not available)

---

## Summary Table

| Aspect | Answer |
|--------|--------|
| **Recovery Point** | Snapshot of resource at a specific time stored in a vault |
| **BackupSizeInBytes** | Only incremental data captured, not cumulative—why sizes stay similar |
| **Backup Chain** | No hard dependency; each recovery point is self-contained with reference data |
| **Copying Last RP** | Copies full data (complete state at that time), not just deltas |
| **PITR Impact** | Losing intermediate recovery points limits your restore granularity to specific backup times only |

---

## Best Practices

1. **Maintain Multiple Recovery Points**: Don't rely on just the latest recovery point. Keep intermediate snapshots for better disaster recovery options.

2. **Use Continuous Backups for PITR**: If you need true point-in-time recovery capability, enable continuous backups instead of relying solely on periodic snapshots.

3. **Consider Lifecycle Policies**: Understand how retention policies affect your recovery options. Older recovery points may expire, limiting your restore window.

4. **Test Recovery**: Regularly test restores from different recovery points to ensure your backup strategy meets your RTO/RPO requirements.

---

## Key AWS Documentation References

- **Incremental Backups**: AWS Backup efficiently stores periodic backups incrementally. The first backup backs up the full copy of data, and each successive backup only captures changes.

- **Backup Independence**: All backups retain necessary reference data to allow a full restore, even if older backups are deleted.

- **Cross-Region Copy**: When copying to a new region for the first time, AWS Backup copies the recovery point in full, including all necessary reference data.

