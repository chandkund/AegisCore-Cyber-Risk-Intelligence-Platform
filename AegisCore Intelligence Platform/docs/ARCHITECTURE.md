# AegisCore Architecture Documentation

**Version**: 1.0  
**Date**: April 2026  
**Status**: Production-Ready

---

## System Overview

AegisCore is a **multi-tenant SaaS security intelligence platform** designed for enterprise cyber risk management. It combines:

- **Real-time asset discovery and vulnerability tracking**
- **AI-powered risk prioritization**
- **Compliance reporting (SOC 2, GDPR, HIPAA)**
- **Multi-tenant data isolation**

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                     │
├─────────────┬─────────────┬─────────────────┬───────────────────────────────┤
│   Web App   │   Mobile    │   API Clients   │   SIEM Integration              │
│  (Next.js)  │  (Future)   │   (Python/JS)   │   (Webhooks/API)              │
└──────┬──────┴──────┬──────┴────────┬────────┴───────────────┬───────────────┘
       │             │               │                        │
       └─────────────┴───────────────┴────────────────────────┘
                                    │
                       AWS CloudFront / ALB (WAF)
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Application Layer                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Next.js    │  │   FastAPI    │  │   Celery     │  │   Redis      │    │
│  │   Frontend   │  │   API        │  │   Workers    │  │   Cache      │    │
│  │   :3000      │  │   :8000      │  │   (Async)    │  │   :6379      │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼────────────────┼─────────────────┼────────────────┼──────────────┘
          │                │                 │                │
          │                └────────┬────────┘                │
          │                         │                         │
          │               ┌──────────┴──────────┐             │
          │               │   Security Layer    │             │
          │               ├───────────────────┤             │
          │               │ - CSRF Protection │             │
          │               │ - Rate Limiting   │             │
          │               │ - JWT Auth        │             │
          │               │ - RBAC            │             │
          │               └──────────┬────────┘             │
          │                          │                      │
          └──────────────────────────┼──────────────────────┘
                                     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Layer                                     │
├──────────────┬──────────────┬──────────────┬──────────────────────────────┤
│  PostgreSQL  │  S3/MinIO    │  OpenSearch  │  MLflow/Model Registry       │
│  (OLTP)      │  (Files)     │  (Search)    │  (Risk Models)               │
│  Encrypted   │  Encrypted   │  Encrypted   │  Versioned                   │
│  Multi-AZ    │  Cross-region│  Clustered   │  A/B Testing                 │
└──────────────┴──────────────┴──────────────┴──────────────────────────────┘
```

---

## Component Details

### 1. Frontend (Next.js 14)

**Architecture Pattern**: App Router + Server Components

```
src/
├── app/                    # App Router
│   ├── (auth)/            # Auth group (login, register)
│   ├── (dashboard)/       # Main app
│   │   ├── platform/     # Platform owner pages
│   │   ├── tenants/      # Tenant management
│   │   └── ...
│   └── api/              # API routes
├── components/           # Reusable UI
├── lib/                  # Utilities, API clients
└── hooks/               # React hooks
```

**Key Features**:
- **Server-Side Rendering** for SEO and performance
- **Suspense Boundaries** for progressive loading
- **Parallel Routes** for complex layouts
- **Intercepting Routes** for modals

### 2. Backend (FastAPI)

**Architecture Pattern**: Layered Architecture with Dependency Injection

```
app/
├── api/                  # API Layer
│   ├── deps.py          # Dependencies (DB, auth)
│   └── v1/              # API Version 1
│       ├── endpoints/   # Route handlers
│       └── router.py    # Route aggregation
├── core/                # Business Logic
│   ├── config.py        # Settings (Pydantic)
│   ├── security.py      # Auth, passwords
│   └── rbac.py          # Role-based access
├── db/                  # Data Access
│   ├── base.py          # SQLAlchemy base
│   ├── session.py       # Connection management
│   └── deps.py          # DB dependency
├── models/              # Domain Models
│   ├── oltp.py          # Transactional models
│   └── olap.py          # Analytics models
├── services/            # Business Services
│   ├── email_service.py
│   ├── otp_service.py
│   └── ...
└── middleware/          # Cross-cutting
    ├── csrf_protection.py
    ├── security_headers.py
    └── rate_limit.py
```

**Key Patterns**:
- **Repository Pattern**: `UserRepository`, `AssetRepository`
- **Dependency Injection**: FastAPI's `Depends`
- **Unit of Work**: SQLAlchemy sessions
- **CQRS**: Separate read/write models (OLTP/OLAP)

### 3. Database Architecture

**OLTP (Online Transaction Processing)**
- **PostgreSQL 16**: Primary transactional database
- **Encryption**: TDE (AES-256) via AWS KMS
- **Replication**: Multi-AZ with read replicas
- **Backup**: Continuous + 30-day retention

**Schema Design**:
```sql
-- Multi-tenant isolation
tenants (id, name, code, approval_status)
users (id, tenant_id, email, hashed_password, roles)
assets (id, tenant_id, name, type, ip_address)
vulnerabilities (id, tenant_id, asset_id, cve_id, severity)
```

**OLAP (Online Analytical Processing)**
- **OpenSearch**: Full-text search + aggregations
- **Use Cases**: Asset search, CVE lookup, analytics

### 4. Security Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├────────────────────────────────────────────────────────────┤
│ Layer 1: Network                                           │
│   - AWS WAF (OWASP Top 10, Geo-blocking)                    │
│   - Security Groups (Least privilege)                     │
│   - VPC Isolation                                         │
├────────────────────────────────────────────────────────────┤
│ Layer 2: Application                                      │
│   - CSRF Protection (Double-submit cookie)                │
│   - Rate Limiting (120 req/min global, 10 login/min)     │
│   - Input Validation (Pydantic)                           │
│   - Security Headers (HSTS, CSP, X-Frame-Options)         │
├────────────────────────────────────────────────────────────┤
│ Layer 3: Authentication                                   │
│   - JWT with bcrypt (12 rounds)                           │
│   - Secure cookies (HttpOnly, Secure, SameSite)         │
│   - OTP Email Verification                                │
│   - Password Strength (zxcvbn)                          │
├────────────────────────────────────────────────────────────┤
│ Layer 4: Authorization                                    │
│   - RBAC with 4 roles                                     │
│   - Tenant Isolation (Row-level security)               │
│   - Platform Owner (cross-tenant access)                │
├────────────────────────────────────────────────────────────┤
│ Layer 5: Data                                             │
│   - Encryption at Rest (TDE)                            │
│   - TLS 1.3 in Transit                                    │
│   - KMS Key Rotation (Annual)                           │
└────────────────────────────────────────────────────────────┘
```

### 5. Caching Strategy

```python
# Redis caching layers
Layer 1: Session Store
  - JWT token blacklisting
  - Rate limit counters
  
Layer 2: Application Cache
  - User permissions (TTL: 5 min)
  - Organization settings (TTL: 1 hour)
  - Static reference data (TTL: 24 hours)
  
Layer 3: Query Cache
  - Asset search results (TTL: 30 sec)
  - Dashboard statistics (TTL: 1 min)
  - CVE details (TTL: 24 hours)
```

### 6. Event-Driven Architecture

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Events  │───▶│  Redis   │───▶│ Celery   │
│          │    │  Queue   │    │ Workers  │
└──────────┘    └──────────┘    └────┬─────┘
     │                               │
     │    ┌──────────┐              │
     └───▶│Database  │◀─────────────┘
        │ Trigger   │
        └──────────┘

Event Types:
- user.created → Send welcome email
- asset.discovered → Enrich with CVE data
- vulnerability.found → Trigger notification
- compliance.violation → Create ticket
```

---

## API Design

### RESTful Conventions

```
/api/v1
├── /auth
│   ├── POST /login
│   ├── POST /register
│   ├── POST /refresh
│   ├── POST /logout
│   ├── POST /change-password
│   └── GET  /me
├── /users
│   ├── GET    /           (list)
│   ├── POST   /           (create)
│   ├── GET    /{id}       (read)
│   ├── PUT    /{id}       (update)
│   └── DELETE /{id}       (delete)
├── /assets
│   ├── GET    /           (list, search)
│   ├── POST   /           (create)
│   ├── GET    /{id}       (read)
│   ├── PUT    /{id}       (update)
│   ├── DELETE /{id}       (delete)
│   └── POST   /import     (bulk import)
└── /platform (platform owner only)
    ├── GET /tenants
    ├── GET /compliance/security-score
    └── GET /audit-logs
```

### Pagination Standard

```json
{
  "items": [...],
  "total": 1000,
  "page": 1,
  "per_page": 50,
  "pages": 20
}
```

### Error Response Standard

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ],
    "request_id": "req_123abc"
  }
}
```

---

## Deployment Architecture

### Local Development

```yaml
# docker-compose.yml services:
- postgres:5432    # Database
- redis:6379       # Cache
- api:8000         # Backend API
- web:3000         # Next.js frontend
- prometheus:9090  # Metrics
- grafana:3001     # Dashboards
```

### Production (AWS)

```
┌─────────────────────────────────────────────────────────────┐
│                        CloudFront                           │
│                   (CDN + DDoS Protection)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                      WAF (AWS)                                │
│  - OWASP Top 10 Rules                                       │
│  - Rate Limiting                                            │
│  - Geo-blocking                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            │        ALB        │
            │   (SSL/TLS 1.3)   │
            └─────────┬─────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────┴────┐   ┌───┴────┐   ┌────┴────┐
   │  ECS    │   │  ECS   │   │  ECS    │
   │  API    │   │  API   │   │  API    │
   │ Task 1  │   │ Task 2 │   │ Task 3  │
   └────┬────┘   └───┬────┘   └────┬────┘
        │            │              │
        └────────────┼──────────────┘
                     │
        ┌────────────┴────────────┐
        │    RDS PostgreSQL       │
        │  (Multi-AZ, Encrypted)  │
        └─────────────────────────┘
```

### CI/CD Pipeline

```
Developer Push
      │
      ▼
┌───────────────┐
│  GitHub       │
│  Actions      │
└───────┬───────┘
        │
    ┌───┴───┐
    ▼       ▼
┌──────┐ ┌────────┐
│ Lint │ │  Test  │
│      │ │        │
│ Ruff │ │ Pytest │
│Black │ │ E2E    │
└──┬───┘ └───┬────┘
   │         │
   └────┬────┘
        ▼
┌───────────────┐
│ Security Scan │
│ - Safety      │
│ - npm audit   │
│ - CodeQL      │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Build Images  │
│ - API         │
│ - Frontend    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Deploy to     │
│ Staging       │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Integration   │
│ Tests         │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Deploy to     │
│ Production    │
└───────────────┘
```

---

## Observability

### Metrics (Prometheus)

```
# Application Metrics
app_requests_total{method,endpoint,status}
app_request_duration_seconds{method,endpoint}
app_active_users
celery_tasks_total{task_name,status}

# Business Metrics
assets_total{tenant_id}
vulnerabilities_critical_total{tenant_id}
users_active_total

# Infrastructure Metrics
system_cpu_percent
system_memory_percent
database_connections_active
redis_operations_total
```

### Logging (Structured JSON)

```json
{
  "timestamp": "2026-04-17T10:30:00Z",
  "level": "INFO",
  "message": "User login successful",
  "service": "aegiscore-api",
  "version": "1.0.0",
  "trace_id": "trace_abc123",
  "span_id": "span_def456",
  "user_id": "usr_789",
  "tenant_id": "ten_abc",
  "request_id": "req_xyz789",
  "duration_ms": 45,
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status_code": 200
}
```

### Alerting Rules

```yaml
# Critical alerts
- name: HighErrorRate
  condition: error_rate > 5% for 5m
  severity: critical
  
- name: DatabaseConnectionsHigh
  condition: db_connections > 80% for 10m
  severity: warning
  
- name: SecurityBlockedRequests
  condition: waf_blocked > 100/min for 5m
  severity: warning
```

---

## Scalability

### Horizontal Scaling

| Component | Scaling Strategy | Max Scale |
|-----------|-----------------|-----------|
| API (ECS) | CPU/Memory based | 20 tasks |
| Database | Read replicas | 5 replicas |
| Redis | Cluster mode | 6 nodes |
| OpenSearch | Data nodes | 10 nodes |

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API p95 latency | < 200ms | ~150ms |
| Login response | < 500ms | ~300ms |
| Asset search | < 100ms | ~80ms |
| Report generation | < 5s | ~3s |
| Concurrent users | 10,000 | Tested 5,000 |

---

## Disaster Recovery

### RPO/RTO Targets

| Component | RPO | RTO |
|-----------|-----|-----|
| Database | 1 hour | 4 hours |
| File Storage | 0 (sync) | 2 hours |
| Configuration | 0 (IaC) | 30 minutes |

### Backup Strategy

```
PostgreSQL:
  - Continuous backup to S3
  - Daily snapshots (30-day retention)
  - Weekly full backups (1-year retention)
  - Cross-region replication

Application State:
  - Redis: RDB snapshots every hour
  - User uploads: S3 versioning + cross-region
  - ML models: Versioned in S3
```

---

## Future Enhancements

### Phase 2 (Q3 2026)
- [ ] Multi-region deployment (EU, APAC)
- [ ] Kubernetes migration (EKS)
- [ ] GraphQL API layer
- [ ] Real-time WebSocket updates

### Phase 3 (Q4 2026)
- [ ] AI/ML pipeline for threat prediction
- [ ] Automated remediation playbooks
- [ ] Integration marketplace
- [ ] Mobile application

---

## Appendix: Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js | 14.1 |
| Styling | Tailwind CSS | 3.4 |
| Components | shadcn/ui | Latest |
| Icons | Lucide React | Latest |
| Backend | FastAPI | 0.109 |
| ORM | SQLAlchemy | 2.0 |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Search | OpenSearch | 2.x |
| ML | scikit-learn | 1.4 |
| Infrastructure | Terraform | 1.7 |
| CI/CD | GitHub Actions | - |
| Monitoring | Prometheus + Grafana | Latest |

---

**Document Owner**: Architecture Team  
**Review Cycle**: Quarterly  
**Next Review**: July 2026
