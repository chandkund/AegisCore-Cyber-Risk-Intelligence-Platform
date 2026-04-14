SET client_min_messages = WARNING;
-- business_units

CREATE TABLE business_units (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	parent_business_unit_id UUID, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_business_unit_id) REFERENCES business_units (id) ON DELETE SET NULL
)

;
-- cve_records

CREATE TABLE cve_records (
	id UUID NOT NULL, 
	cve_id VARCHAR(32) NOT NULL, 
	title VARCHAR(512), 
	description TEXT, 
	published_at TIMESTAMP WITH TIME ZONE, 
	last_modified_at TIMESTAMP WITH TIME ZONE, 
	cvss_base_score NUMERIC(4, 2), 
	cvss_vector VARCHAR(128), 
	severity VARCHAR(16) NOT NULL, 
	epss_score NUMERIC(6, 5), 
	exploit_available BOOLEAN DEFAULT 'false' NOT NULL, 
	PRIMARY KEY (id)
)

;
-- etl_watermarks

CREATE TABLE etl_watermarks (
	pipeline_name VARCHAR(120) NOT NULL, 
	last_success_at TIMESTAMP WITH TIME ZONE, 
	high_watermark TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (pipeline_name)
)

;
-- locations

CREATE TABLE locations (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	region VARCHAR(120), 
	country_code VARCHAR(2), 
	PRIMARY KEY (id)
)

;
-- roles

CREATE TABLE roles (
	id UUID NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	description VARCHAR(512), 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;
-- sla_policies

CREATE TABLE sla_policies (
	id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	max_days_to_remediate INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_sla_policies_name UNIQUE (name)
)

;
-- users

CREATE TABLE users (
	id UUID NOT NULL, 
	email VARCHAR(320) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_users_email UNIQUE (email)
)

;
-- audit_log

CREATE TABLE audit_log (
	id UUID NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	actor_user_id UUID, 
	action VARCHAR(120) NOT NULL, 
	resource_type VARCHAR(120) NOT NULL, 
	resource_id VARCHAR(64), 
	payload JSONB, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE SET NULL
)

;
-- refresh_tokens

CREATE TABLE refresh_tokens (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	token_hash VARCHAR(128) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
)

;
-- teams

CREATE TABLE teams (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	business_unit_id UUID NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_unit_id) REFERENCES business_units (id) ON DELETE RESTRICT
)

;
-- user_roles

CREATE TABLE user_roles (
	user_id UUID NOT NULL, 
	role_id UUID NOT NULL, 
	PRIMARY KEY (user_id, role_id), 
	CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
)

;
-- assets

CREATE TABLE assets (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	asset_type VARCHAR(64) NOT NULL, 
	hostname VARCHAR(253), 
	ip_address VARCHAR(45), 
	business_unit_id UUID NOT NULL, 
	team_id UUID, 
	location_id UUID, 
	criticality SMALLINT DEFAULT '3' NOT NULL, 
	owner_email VARCHAR(320), 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(business_unit_id) REFERENCES business_units (id) ON DELETE RESTRICT, 
	FOREIGN KEY(team_id) REFERENCES teams (id) ON DELETE SET NULL, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE SET NULL
)

;
-- asset_attributes

CREATE TABLE asset_attributes (
	id UUID NOT NULL, 
	asset_id UUID NOT NULL, 
	key VARCHAR(120) NOT NULL, 
	value TEXT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_asset_attributes_asset_key UNIQUE (asset_id, key), 
	FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE CASCADE
)

;
-- vulnerability_findings

CREATE TABLE vulnerability_findings (
	id UUID NOT NULL, 
	asset_id UUID NOT NULL, 
	cve_record_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	discovered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	remediated_at TIMESTAMP WITH TIME ZONE, 
	due_at TIMESTAMP WITH TIME ZONE, 
	assigned_to_user_id UUID, 
	internal_priority_score NUMERIC(8, 4), 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_findings_asset_cve UNIQUE (asset_id, cve_record_id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE CASCADE, 
	FOREIGN KEY(cve_record_id) REFERENCES cve_records (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assigned_to_user_id) REFERENCES users (id) ON DELETE SET NULL
)

;
-- remediation_events

CREATE TABLE remediation_events (
	id UUID NOT NULL, 
	finding_id UUID NOT NULL, 
	event_type VARCHAR(64) NOT NULL, 
	old_status VARCHAR(32), 
	new_status VARCHAR(32), 
	actor_user_id UUID, 
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	details JSONB, 
	PRIMARY KEY (id), 
	FOREIGN KEY(finding_id) REFERENCES vulnerability_findings (id) ON DELETE CASCADE, 
	FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE SET NULL
)

;
