"""Unit tests for upload service."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.tenant import TenantContext
from app.models.oltp import (
    Asset,
    BusinessUnit,
    CveRecord,
    Organization,
    VulnerabilityFinding,
)
from app.services.upload_service import UploadService, UploadValidationError


@pytest.fixture
def tenant_context(db: Session) -> TenantContext:
    """Create a test tenant context."""
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        code="test-org",
        is_active=True,
        approval_status="approved",
    )
    db.add(org)
    db.commit()
    return TenantContext(tenant_id=org.id, tenant_code="test-org")


@pytest.fixture
def upload_service(db: Session, tenant_context: TenantContext) -> UploadService:
    """Create upload service with tenant context."""
    return UploadService(db, tenant_context)


@pytest.fixture
def business_unit(db: Session, tenant_context: TenantContext) -> BusinessUnit:
    """Create a test business unit."""
    bu = BusinessUnit(
        id=uuid.uuid4(),
        tenant_id=tenant_context.tenant_id,
        name="Engineering",
        code="ENG",
    )
    db.add(bu)
    db.commit()
    return bu


@pytest.fixture
def existing_asset(db: Session, tenant_context: TenantContext, business_unit: BusinessUnit) -> Asset:
    """Create an existing asset for update tests."""
    asset = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_context.tenant_id,
        name="Test Server",
        asset_type="server",
        hostname="test-server-01",
        ip_address="10.0.1.10",
        business_unit_id=business_unit.id,
        criticality=3,
    )
    db.add(asset)
    db.commit()
    return asset


class TestAssetUploadCSV:
    """Test asset CSV upload functionality."""

    def test_upload_valid_csv_creates_assets(self, upload_service: UploadService, business_unit: BusinessUnit, db: Session):
        """Valid CSV should create new assets."""
        csv_content = b"""name,asset_type,hostname,ip_address,business_unit_code,criticality
Web Server,server,web01,10.0.1.20,ENG,4
Database Server,database,db01,10.0.1.21,ENG,5"""

        result = upload_service.upload_assets_csv(csv_content)

        assert result.inserted == 2
        assert result.failed == 0
        assert result.total_rows == 2

        # Verify assets created
        assets = db.query(Asset).filter(Asset.tenant_id == upload_service.tenant_id).all()
        assert len(assets) == 2

    def test_upload_updates_existing_asset(self, upload_service: UploadService, existing_asset: Asset):
        """CSV with existing hostname should update asset."""
        csv_content = f"""name,asset_type,hostname,ip_address,business_unit_code,criticality
Updated Server,server,test-server-01,10.0.1.99,ENG,2""".encode()

        result = upload_service.upload_assets_csv(csv_content)

        assert result.updated == 1
        assert result.inserted == 0

        # Verify asset was updated
        assert existing_asset.name == "Updated Server"
        assert existing_asset.criticality == 2
        assert existing_asset.ip_address == "10.0.1.99"

    def test_upload_missing_required_field_fails(self, upload_service: UploadService):
        """CSV missing required field should report error."""
        csv_content = b"""name,asset_type,hostname,ip_address,business_unit_code
,server,web01,10.0.1.20,ENG"""

        result = upload_service.upload_assets_csv(csv_content)

        assert result.failed == 1
        assert result.inserted == 0
        assert len(result.errors) == 1
        assert "name" in result.errors[0].field.lower()

    def test_upload_invalid_business_unit_fails(self, upload_service: UploadService):
        """CSV with non-existent business unit should fail."""
        csv_content = b"""name,asset_type,hostname,ip_address,business_unit_code
Web Server,server,web01,10.0.1.20,INVALID_BU"""

        result = upload_service.upload_assets_csv(csv_content)

        assert result.failed == 1
        assert "business unit" in result.errors[0].message.lower()

    def test_upload_invalid_csv_format_raises_error(self, upload_service: UploadService):
        """Invalid CSV format should raise UploadValidationError."""
        csv_content = b"not valid csv content without headers"

        with pytest.raises(UploadValidationError):
            upload_service.upload_assets_csv(csv_content)

    def test_upload_non_utf8_encoding_raises_error(self, upload_service: UploadService):
        """Non-UTF-8 encoding should raise error."""
        csv_content = b"\xff\xfe invalid encoding"

        with pytest.raises(UploadValidationError):
            upload_service.upload_assets_csv(csv_content)


class TestVulnerabilityUploadCSV:
    """Test vulnerability CSV upload functionality."""

    def test_upload_valid_cve_creates_records(self, upload_service: UploadService, db: Session):
        """Valid CVE CSV should create CVE records."""
        csv_content = b"""cve_id,title,description,severity,cvss_score
CVE-2024-1234,SQL Injection,SQL injection in login form,HIGH,8.5
CVE-2024-5678,XSS,Cross-site scripting,MEDIUM,6.1"""

        result = upload_service.upload_vulnerabilities_csv(csv_content)

        assert result.inserted == 2
        assert result.failed == 0

        # Verify CVEs created
        cves = db.query(CveRecord).filter(CveRecord.cve_id.in_(["CVE-2024-1234", "CVE-2024-5678"])).all()
        assert len(cves) == 2

    def test_upload_updates_existing_cve(self, upload_service: UploadService, db: Session):
        """CSV with existing CVE should update it."""
        # Create existing CVE
        cve = CveRecord(
            cve_id="CVE-2024-1234",
            title="Old Title",
            severity="LOW",
        )
        db.add(cve)
        db.commit()

        csv_content = b"""cve_id,title,description,severity,cvss_score
CVE-2024-1234,Updated Title,Updated description,HIGH,9.8"""

        result = upload_service.upload_vulnerabilities_csv(csv_content)

        assert result.updated == 1
        assert result.inserted == 0

        # Verify CVE was updated
        db.refresh(cve)
        assert cve.title == "Updated Title"
        assert cve.severity == "HIGH"
        assert float(cve.cvss_base_score) == 9.8

    def test_upload_invalid_cve_format_fails(self, upload_service: UploadService):
        """Invalid CVE ID format should fail."""
        csv_content = b"""cve_id,title,description,severity
INVALID-CVE,Test,Test,HIGH"""

        result = upload_service.upload_vulnerabilities_csv(csv_content)

        assert result.failed == 1
        assert "cve" in result.errors[0].message.lower()

    def test_upload_creates_finding_for_existing_asset(
        self, upload_service: UploadService, existing_asset: Asset, db: Session
    ):
        """Upload with existing asset identifier should create finding."""
        csv_content = f"""cve_id,asset_identifier,status,notes
CVE-2024-9999,test-server-01,OPEN,Test finding""".encode()

        result = upload_service.upload_vulnerabilities_csv(csv_content)

        assert result.inserted >= 1  # At least CVE created

        # Verify finding was created
        finding = (
            db.query(VulnerabilityFinding)
            .filter(VulnerabilityFinding.asset_id == existing_asset.id)
            .first()
        )
        assert finding is not None
        assert finding.status == "OPEN"


class TestMappingUploadCSV:
    """Test asset-vulnerability mapping CSV upload."""

    def test_upload_valid_mapping_creates_finding(
        self, upload_service: UploadService, existing_asset: Asset, db: Session
    ):
        """Valid mapping should create finding linking asset to CVE."""
        csv_content = f"""asset_identifier,cve_id,status,discovered_date,notes
test-server-01,CVE-2024-1111,OPEN,2024-01-15,Found during scan""".encode()

        result = upload_service.upload_mappings_csv(csv_content)

        assert result.inserted == 1
        assert result.failed == 0

        # Verify finding created
        finding = (
            db.query(VulnerabilityFinding)
            .filter(VulnerabilityFinding.asset_id == existing_asset.id)
            .first()
        )
        assert finding is not None
        assert finding.status == "OPEN"

    def test_upload_mapping_updates_existing_finding(
        self, upload_service: UploadService, existing_asset: Asset, db: Session
    ):
        """Mapping for existing finding should update it."""
        # Create CVE and finding
        cve = CveRecord(cve_id="CVE-2024-2222", title="Test", severity="LOW")
        db.add(cve)
        db.flush()

        finding = VulnerabilityFinding(
            tenant_id=upload_service.tenant_id,
            asset_id=existing_asset.id,
            cve_record_id=cve.id,
            status="OPEN",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add(finding)
        db.commit()

        # Update via mapping
        csv_content = f"""asset_identifier,cve_id,status,notes
test-server-01,CVE-2024-2222,REMEDIATED,Fixed in latest patch""".encode()

        result = upload_service.upload_mappings_csv(csv_content)

        assert result.updated == 1

        db.refresh(finding)
        assert finding.status == "REMEDIATED"
        assert finding.notes == "Fixed in latest patch"

    def test_upload_mapping_missing_asset_fails(self, upload_service: UploadService):
        """Mapping with non-existent asset should fail."""
        csv_content = b"""asset_identifier,cve_id,status
non-existent-asset,CVE-2024-3333,OPEN"""

        result = upload_service.upload_mappings_csv(csv_content)

        assert result.failed == 1
        assert "asset" in result.errors[0].message.lower()

    def test_upload_mapping_invalid_cve_fails(self, upload_service: UploadService, existing_asset: Asset):
        """Mapping with invalid CVE format should fail."""
        csv_content = f"""asset_identifier,cve_id,status
test-server-01,INVALID-CVE,OPEN""".encode()

        result = upload_service.upload_mappings_csv(csv_content)

        assert result.failed == 1
        assert "cve" in result.errors[0].message.lower()


class TestAssetUploadJSON:
    """Test asset JSON upload functionality."""

    def test_upload_valid_json_creates_assets(self, upload_service: UploadService, business_unit: BusinessUnit, db: Session):
        """Valid JSON array should create assets."""
        json_content = b'[{"name": "Web Server", "asset_type": "server", "business_unit_code": "ENG", "criticality": 4}]'

        result = upload_service.upload_assets_json(json_content)

        assert result.inserted == 1
        assert result.failed == 0

    def test_upload_json_not_array_raises_error(self, upload_service: UploadService):
        """JSON that is not an array should raise error."""
        json_content = b'{"name": "test", "asset_type": "server"}'

        with pytest.raises(UploadValidationError, match="array"):
            upload_service.upload_assets_json(json_content)

    def test_upload_invalid_json_raises_error(self, upload_service: UploadService):
        """Invalid JSON should raise error."""
        json_content = b'not valid json'

        with pytest.raises(UploadValidationError):
            upload_service.upload_assets_json(json_content)


class TestTenantIsolation:
    """Test that uploads are properly tenant-scoped."""

    def test_asset_lookup_is_tenant_scoped(
        self, upload_service: UploadService, db: Session, tenant_context: TenantContext
    ):
        """Asset lookup should not find assets from other tenants."""
        # Create asset in different tenant (org + BU required by schema)
        other_tenant_id = uuid.uuid4()
        db.add(
            Organization(
                id=other_tenant_id,
                name="Other Org Scoped",
                code=f"other-{other_tenant_id.hex[:8]}",
                is_active=True,
                approval_status="approved",
            )
        )
        db.flush()
        other_bu = BusinessUnit(
            id=uuid.uuid4(),
            tenant_id=other_tenant_id,
            name="Other BU",
            code=f"OBU-{uuid.uuid4().hex[:6]}",
        )
        db.add(other_bu)
        db.flush()
        other_asset = Asset(
            id=uuid.uuid4(),
            tenant_id=other_tenant_id,
            name="Other Asset",
            asset_type="server",
            hostname="other-host",
            business_unit_id=other_bu.id,
        )
        db.add(other_asset)
        db.commit()

        # Try to create mapping using other tenant's asset
        csv_content = b"""asset_identifier,cve_id,status
other-host,CVE-2024-4444,OPEN"""

        result = upload_service.upload_mappings_csv(csv_content)

        # Should fail because asset not found in current tenant
        assert result.failed == 1


class TestValidationHelpers:
    """Test validation helper methods."""

    def test_valid_cve_id_format(self, upload_service: UploadService):
        """Valid CVE IDs should pass validation."""
        valid_cves = ["CVE-2024-1234", "CVE-2023-99999", "cve-2024-1234"]
        for cve in valid_cves:
            assert upload_service._is_valid_cve_id(cve) is True, f"{cve} should be valid"

    def test_invalid_cve_id_format(self, upload_service: UploadService):
        """Invalid CVE IDs should fail validation."""
        invalid_cves = ["INVALID", "CVE-123", "2024-1234", ""]
        for cve in invalid_cves:
            assert upload_service._is_valid_cve_id(cve) is False, f"{cve} should be invalid"

    def test_valid_ip_address(self, upload_service: UploadService):
        """Valid IP addresses should pass validation."""
        valid_ips = ["192.168.1.1", "10.0.0.1", "::1", "2001:db8::1"]
        for ip in valid_ips:
            assert upload_service._is_valid_ip(ip) is True, f"{ip} should be valid"

    def test_invalid_ip_address(self, upload_service: UploadService):
        """Invalid IP addresses should fail validation."""
        invalid_ips = ["not-an-ip", "256.1.1.1", "", "192.168.1"]
        for ip in invalid_ips:
            assert upload_service._is_valid_ip(ip) is False, f"{ip} should be invalid"

    def test_valid_email(self, upload_service: UploadService):
        """Valid emails should pass validation."""
        valid_emails = ["test@example.com", "user.name@domain.co.uk"]
        for email in valid_emails:
            assert upload_service._is_valid_email(email) is True

    def test_invalid_email(self, upload_service: UploadService):
        """Invalid emails should fail validation."""
        invalid_emails = ["not-an-email", "@example.com", "test@", ""]
        for email in invalid_emails:
            assert upload_service._is_valid_email(email) is False


class TestImportSummary:
    """Test import summary calculations."""

    def test_summary_counts_are_accurate(self, upload_service: UploadService, business_unit: BusinessUnit):
        """Import summary should accurately count operations."""
        csv_content = b"""name,asset_type,business_unit_code
Asset1,server,ENG
Asset2,database,ENG
Asset3,network,ENG"""

        result = upload_service.upload_assets_csv(csv_content)

        assert result.total_rows == 3
        assert result.inserted + result.updated + result.failed == 3
        assert result.processing_time_ms >= 0
        assert result.imported_at is not None
