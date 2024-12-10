# AATS (Autonomous Agent Team System) Details

## Core Services Architecture

### Project Manager Service
- **gRPC Port**: 50060
- **REST Port**: 8090
- **Health Check**: /health
- **Metrics**: /metrics
- **Internal Service**: Yes

### Database Controller Service
- **gRPC Port**: 50061
- **REST Port**: 8091
- **Health Check**: /health
- **Metrics**: /metrics
- **Internal Service**: Yes

### Communication Coordinator Service
- **gRPC Port**: 50062
- **REST Port**: 8092
- **Health Check**: /health
- **Metrics**: /metrics
- **Internal Service**: Yes

## Resource Configuration

### Compute Resources
```yaml
Project Manager:
  CPU:
    Requests: 2
    Limits: 4
  Memory:
    Requests: 4Gi
    Limits: 8Gi

Database Controller:
  CPU:
    Requests: 4
    Limits: 8
  Memory:
    Requests: 8Gi
    Limits: 16Gi

Communication Coordinator:
  CPU:
    Requests: 2
    Limits: 4
  Memory:
    Requests: 4Gi
    Limits: 8Gi

HITL Interface:
  CPU:
    Requests: 2
    Limits: 4
  Memory:
    Requests: 4Gi
    Limits: 8Gi
```

### Storage Resources
```yaml
Database Storage:
  PostgreSQL:
    Size: 500Gi
    StorageClass: ssd-high-iops
    AccessMode: ReadWriteOnce
    Retention: 90d
    Path: /var/lib/postgresql/data

  MongoDB:
    Size: 1Ti
    StorageClass: ssd-high-iops
    AccessMode: ReadWriteOnce
    Retention: 90d
    Path: /var/lib/mongodb

  Neo4j:
    Size: 200Gi
    StorageClass: ssd-high-iops
    AccessMode: ReadWriteOnce
    Retention: 90d
    Path: /var/lib/neo4j

  Redis:
    Size: 100Gi
    StorageClass: ssd-high-iops
    AccessMode: ReadWriteOnce
    Path: /var/lib/redis

Agent Storage:
  Size: 100Gi
  StorageClass: ssd
  AccessMode: ReadWriteMany
  Paths:
    - /var/lib/aats/agents
    - /var/lib/aats/models
    - /var/lib/aats/cache

Monitoring Storage:
  Size: 200Gi
  StorageClass: ssd
  AccessMode: ReadWriteOnce
  Retention: 30d
  Paths:
    - /var/lib/prometheus
    - /var/lib/grafana
```

### Network Resources
```yaml
Bandwidth:
  Ingress:
    Guaranteed: 1Gbps
    Burst: 10Gbps
  Egress:
    Guaranteed: 1Gbps
    Burst: 10Gbps

Connections:
  MaxConnections: 50000
  MaxConnectionRate: 5000/s
  IdleTimeout: 300s
  KeepAlive:
    Time: 120s
    Interval: 20s
    Probes: 6
```

### Autoscaling Configuration
```yaml
Horizontal Pod Autoscaling:
  MinReplicas: 3
  MaxReplicas: 20
  Metrics:
    CPU:
      TargetAverageUtilization: 75
    Memory:
      TargetAverageUtilization: 75
    Custom:
      - Type: Pods
        MetricName: agent_task_queue_length
        TargetAverageValue: 100

Vertical Pod Autoscaling:
  UpdateMode: Auto
  ControlledResources:
    - cpu
    - memory
  ResourcePolicy:
    MinAllowed:
      CPU: 1
      Memory: 2Gi
    MaxAllowed:
      CPU: 8
      Memory: 32Gi
```

## Security Configuration

### TLS Configuration
- **Certificate Path**: /etc/certs/aats
- **CA Path**: /etc/certs/ca
- **Validity**: 365 days
- **Key Size**: 4096 bits
- **Algorithm**: RSA
- **Minimum TLS Version**: 1.3

### Authentication Methods
1. **Agent Communication**:
   - Type: mTLS
   - Client Authentication Required
   - Cipher Suites:
     - TLS_AES_256_GCM_SHA384
     - TLS_CHACHA20_POLY1305_SHA256

2. **HITL Interface**:
   - Type: JWT + MFA
   - Issuer: auth.aats.ai
   - Audience: aats-hitl
   - Token Validity: 30 minutes
   - Refresh Token Validity: 8 hours
   - MFA Required: Yes

## Message Bus Configuration

### Kafka Configuration
- **Broker Port**: 9092
- **Schema Registry Port**: 8081
- **JMX Port**: 9999
- **Authentication**: SASL/SCRAM with SSL
- **Topics**:
  - agent.tasks.*
  - agent.status.*
  - agent.metrics.*
  - system.events.*
- **Retention**: 7 days
- **Replication Factor**: 3

### RabbitMQ Configuration
- **AMQP Port**: 5672
- **Management Port**: 15672
- **Authentication**: Username/Password with SSL
- **Vhosts**: aats
- **Queues**:
  - agent.tasks
  - agent.responses
  - system.notifications
- **Exchanges**:
  - agent.direct
  - agent.topic
  - agent.fanout

## Database Configuration

### PostgreSQL
- **Port**: 5432
- **Max Connections**: 1000
- **Shared Buffers**: 8GB
- **Effective Cache Size**: 24GB
- **Work Memory**: 32MB
- **Maintenance Work Memory**: 2GB
- **WAL Level**: Logical
- **Archive Mode**: On

### MongoDB
- **Port**: 27017
- **Replica Set**: Yes
- **Sharding**: Yes
- **WiredTiger Cache**: 16GB
- **Journaling**: Enabled
- **Read Concern**: Majority
- **Write Concern**: Majority

### Neo4j
- **Bolt Port**: 7687
- **HTTP Port**: 7474
- **HTTPS Port**: 7473
- **Page Cache**: 16GB
- **Heap Size**: 16GB
- **Causal Clustering**: Enabled

### Redis
- **Port**: 6379
- **Mode**: Cluster
- **Max Memory**: 12GB
- **Eviction Policy**: volatile-lru
- **Persistence**: RDB + AOF
- **Replication**: Yes

## Monitoring Configuration

### Prometheus
- **Port**: 9090
- **Retention**: 30d
- **Storage**: 200Gi
- **Scrape Interval**: 10s
- **Evaluation Interval**: 10s
- **Resource Requirements**:
  - CPU: 4 cores
  - Memory: 16Gi

### Grafana
- **Port**: 3000
- **Authentication**: OAuth2 + LDAP
- **Dashboards**: Auto-provisioned
- **Resource Requirements**:
  - CPU: 2 cores
  - Memory: 4Gi

### AlertManager
- **Port**: 9093
- **Webhook Port**: 9094
- **Integrations**:
  - Slack
  - Email
  - PagerDuty
- **Resource Requirements**:
  - CPU: 2 cores
  - Memory: 4Gi

## RBAC Configuration

### Roles
```yaml
aats-admin:
  Resources: [agents, tasks, system, metrics]
  Verbs: [create, read, update, delete]

aats-operator:
  Resources: [agents, tasks, metrics]
  Verbs: [read, update]

aats-viewer:
  Resources: [metrics, health]
  Verbs: [read]
```

### Service Accounts
```yaml
Name: aats-system
Namespace: aats
Roles:
  - aats-admin
  - metrics-admin
  - storage-admin
```

## Resource Quotas

### Namespace Quotas
```yaml
AATS Namespace:
  CPU:
    Requests: 32
    Limits: 64
  Memory:
    Requests: 64Gi
    Limits: 128Gi
  Storage:
    Requests: 2Ti
    Snapshots: 20
```

### Resource Limits
```yaml
Agent Container:
  Min:
    CPU: 500m
    Memory: 1Gi
  Default:
    CPU: 2
    Memory: 4Gi
  Max:
    CPU: 8
    Memory: 32Gi

Service Container:
  Min:
    CPU: 1
    Memory: 2Gi
  Default:
    CPU: 4
    Memory: 8Gi
  Max:
    CPU: 16
    Memory: 64Gi
```

## Maintenance and Updates

### Regular Maintenance
- Certificate rotation (365 days)
- Secret rotation (30 days)
- Security policy updates (monthly)
- Network policy reviews (monthly)
- Access control audits (monthly)
- Performance tuning (weekly)
- Resource quota reviews (weekly)
- Backup verification (daily)

### Update Procedures
- Zero-downtime deployments
- Rolling updates
- Automated rollback capability
- Database migration procedures
- State backup procedures
- Recovery procedures

### Backup Schedule
- Full system backup (daily)
- Database backups (hourly)
- Configuration backups (daily)
- State backups (every 15 minutes)
- Retention: 90 days

### Monitoring and Alerts
- System health monitoring
- Performance metrics
- Error rate tracking
- Resource utilization
- Security events
- HITL notifications
- Agent status updates
