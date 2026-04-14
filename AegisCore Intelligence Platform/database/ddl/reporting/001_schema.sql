CREATE SCHEMA IF NOT EXISTS reporting;
SET search_path TO reporting, public;
-- reporting.dim_assignee_user

CREATE TABLE reporting.dim_assignee_user (
	user_key SERIAL NOT NULL, 
	user_id UUID NOT NULL, 
	email VARCHAR(320) NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	PRIMARY KEY (user_key), 
	CONSTRAINT uq_dim_assignee_natural UNIQUE (user_id)
)

;
-- reporting.dim_business_unit

CREATE TABLE reporting.dim_business_unit (
	bu_key SERIAL NOT NULL, 
	business_unit_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	PRIMARY KEY (bu_key), 
	CONSTRAINT uq_dim_bu_natural UNIQUE (business_unit_id)
)

;
-- reporting.dim_cve

CREATE TABLE reporting.dim_cve (
	cve_key SERIAL NOT NULL, 
	cve_record_id UUID NOT NULL, 
	cve_id VARCHAR(32) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	cvss_base_score NUMERIC(4, 2), 
	PRIMARY KEY (cve_key), 
	CONSTRAINT uq_dim_cve_natural UNIQUE (cve_record_id)
)

;
-- reporting.dim_date

CREATE TABLE reporting.dim_date (
	date_key INTEGER NOT NULL, 
	full_date DATE NOT NULL, 
	year INTEGER NOT NULL, 
	quarter INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	week_of_year INTEGER NOT NULL, 
	day_of_week INTEGER NOT NULL, 
	is_weekend BOOLEAN NOT NULL, 
	PRIMARY KEY (date_key), 
	UNIQUE (full_date)
)

;
-- reporting.dim_severity

CREATE TABLE reporting.dim_severity (
	severity_key SERIAL NOT NULL, 
	severity_code VARCHAR(16) NOT NULL, 
	rank INTEGER NOT NULL, 
	PRIMARY KEY (severity_key), 
	CONSTRAINT uq_dim_severity_code UNIQUE (severity_code)
)

;
-- reporting.dim_team

CREATE TABLE reporting.dim_team (
	team_key SERIAL NOT NULL, 
	team_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	bu_key INTEGER NOT NULL, 
	PRIMARY KEY (team_key), 
	CONSTRAINT uq_dim_team_natural UNIQUE (team_id), 
	FOREIGN KEY(bu_key) REFERENCES reporting.dim_business_unit (bu_key)
)

;
-- reporting.dim_asset

CREATE TABLE reporting.dim_asset (
	asset_key SERIAL NOT NULL, 
	asset_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	asset_type VARCHAR(64) NOT NULL, 
	criticality INTEGER NOT NULL, 
	bu_key INTEGER NOT NULL, 
	team_key INTEGER, 
	PRIMARY KEY (asset_key), 
	CONSTRAINT uq_dim_asset_natural UNIQUE (asset_id), 
	FOREIGN KEY(bu_key) REFERENCES reporting.dim_business_unit (bu_key), 
	FOREIGN KEY(team_key) REFERENCES reporting.dim_team (team_key)
)

;
-- reporting.fact_vulnerability_snapshot

CREATE TABLE reporting.fact_vulnerability_snapshot (
	id SERIAL NOT NULL, 
	snapshot_date DATE NOT NULL, 
	date_key INTEGER NOT NULL, 
	finding_oltp_id UUID NOT NULL, 
	asset_key INTEGER NOT NULL, 
	cve_key INTEGER NOT NULL, 
	bu_key INTEGER NOT NULL, 
	team_key INTEGER, 
	assignee_user_key INTEGER, 
	severity_key INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	cvss_base_score NUMERIC(4, 2), 
	epss_score NUMERIC(6, 5), 
	days_open INTEGER NOT NULL, 
	is_overdue BOOLEAN NOT NULL, 
	exploit_available BOOLEAN NOT NULL, 
	loaded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_fact_snapshot_finding_day UNIQUE (snapshot_date, finding_oltp_id), 
	FOREIGN KEY(date_key) REFERENCES reporting.dim_date (date_key), 
	FOREIGN KEY(asset_key) REFERENCES reporting.dim_asset (asset_key), 
	FOREIGN KEY(cve_key) REFERENCES reporting.dim_cve (cve_key), 
	FOREIGN KEY(bu_key) REFERENCES reporting.dim_business_unit (bu_key), 
	FOREIGN KEY(team_key) REFERENCES reporting.dim_team (team_key), 
	FOREIGN KEY(assignee_user_key) REFERENCES reporting.dim_assignee_user (user_key), 
	FOREIGN KEY(severity_key) REFERENCES reporting.dim_severity (severity_key)
)

;
