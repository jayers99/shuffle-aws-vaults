"""Unit tests for Vault domain model."""

import pytest

from shuffle_aws_vaults.domain.vault import Vault


def test_vault_creation(sample_vault: Vault) -> None:
    """Test creating a vault."""
    assert sample_vault.name == "test-vault"
    assert sample_vault.region == "us-east-1"
    assert sample_vault.account_id == "123456789012"
    assert sample_vault.recovery_point_count == 5


def test_is_encrypted(sample_vault: Vault, empty_vault: Vault) -> None:
    """Test is_encrypted method."""
    assert sample_vault.is_encrypted() is True
    assert empty_vault.is_encrypted() is False


def test_has_recovery_points(sample_vault: Vault, empty_vault: Vault) -> None:
    """Test has_recovery_points method."""
    assert sample_vault.has_recovery_points() is True
    assert empty_vault.has_recovery_points() is False


def test_matches_pattern_exact() -> None:
    """Test matches_pattern with exact match."""
    vault = Vault(
        name="prod-vault",
        arn="arn:aws:backup:us-east-1:123456789012:backup-vault:prod-vault",
        region="us-east-1",
        account_id="123456789012",
    )
    assert vault.matches_pattern("prod-vault") is True
    assert vault.matches_pattern("dev-vault") is False


def test_matches_pattern_wildcard() -> None:
    """Test matches_pattern with wildcard."""
    vault = Vault(
        name="prod-vault-001",
        arn="arn:aws:backup:us-east-1:123456789012:backup-vault:prod-vault-001",
        region="us-east-1",
        account_id="123456789012",
    )
    assert vault.matches_pattern("prod-*") is True
    assert vault.matches_pattern("*") is True
    assert vault.matches_pattern("dev-*") is False


def test_vault_immutability(sample_vault: Vault) -> None:
    """Test that vaults are immutable."""
    with pytest.raises(AttributeError):
        sample_vault.name = "new-name"  # type: ignore
