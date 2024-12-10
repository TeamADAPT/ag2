# AATS Deployment Guide

## Overview
This guide provides detailed instructions for deploying and managing the Autonomous AI Agent Team System (AATS) across different environments. The system is designed to be deployed on Kubernetes with support for high availability, scalability, and resilience.

## Prerequisites

### Infrastructure Requirements
- Kubernetes cluster (v1.25+)
- Helm (v3.0+)
- kubectl CLI tool
- AWS CLI (for AWS deployments)
- Terraform (v1.0+)

### Resource Requirements
```yaml
Minimum Cluster Resources:
- 32 CPU cores
- 64GB RAM
- 500GB Storage
- 3 Worker Nodes
```

### Required Services
- PostgreSQL (v14+)
- MongoDB (v6+)
- Redis (v7+)
- Neo4j (v5+)
- Kafka (v3+)
- RabbitMQ (v3.11+)

## Deployment Environments

### Development
```bash
# Set up development environment
kubectl create namespace aats-dev
kubectl config set-context --current --namespace=aats-dev

# Deploy development configuration
helm install aats-dev ./helm/aats \
  -f values.dev.yaml \
  --set environment=development
```

### Testing
```bash
# Set up testing environment
kubectl create namespace aats-test
kubectl config set-context --current --namespace=aats-test

# Deploy testing configuration
helm install aats-test ./helm/aats \
  -f values.test.yaml \
  --set environment=testing
```

### Production
```bash
# Set up production environment
kubectl create namespace aats-prod
kubectl config set-context --current --namespace=aats-prod

# Deploy production configuration
helm install aats-prod ./helm/aats \
  -f values.prod.yaml \
  --set environment=production
```

## Deployment Steps

1. **Infrastructure Setup**
```bash
# Initialize infrastructure
cd terraform
terraform init
terraform plan -var-file=env/prod.tfvars
terraform apply -var-file=env/prod.tfvars
```

2. **Database Setup**
```bash
# Deploy databases
helm install aats-databases ./helm/databases \
  -f databases/values.yaml \
  --set global.environment=production
```

3. **Message Brokers Setup**
```bash
# Deploy message brokers
helm install aats-brokers ./helm/brokers \
  -f brokers/values.yaml \
  --set global.environment=production
```

4. **Core Services Setup**
```bash
# Deploy core services
helm install aats-core ./helm/core \
  -f core/values.yaml \
  --set global.environment=production
```

5. **Agent Deployment**
```bash
# Deploy strategic agents
helm install aats-strategic ./helm/agents/strategic \
  -f agents/strategic/values.yaml

# Deploy tactical agents
helm install aats-tactical ./helm/agents/tactical \
  -f agents/tactical/values.yaml

# Deploy operational agents
helm install aats-operational ./helm/agents/operational \
  -f agents/operational/values.yaml
```

## Monitoring Setup

1. **Prometheus & Grafana**
```bash
# Deploy monitoring stack
helm install aats-monitoring ./helm/monitoring \
  -f monitoring/values.yaml \
  --set global.environment=production
```

2. **Logging Stack**
```bash
# Deploy logging stack
helm install aats-logging ./helm/logging \
  -f logging/values.yaml \
  --set global.environment=production
```

## Security Configuration

1. **Network Policies**
```bash
# Apply network policies
kubectl apply -f security/network-policies/

# Verify policies
kubectl describe networkpolicies -n aats-prod
```

2. **Service Mesh**
```bash
# Install Istio
istioctl install -f security/istio/values.yaml

# Enable sidecar injection
kubectl label namespace aats-prod istio-injection=enabled
```

## Scaling Configuration

### Horizontal Pod Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aats-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aats-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Pod Autoscaling
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: aats-agent-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aats-agent
  updatePolicy:
    updateMode: Auto
```

## Backup and Recovery

### Database Backups
```bash
# Configure automated backups
kubectl apply -f backup/cronjobs/database-backup.yaml

# Verify backup configuration
kubectl get cronjobs -n aats-prod
```

### Disaster Recovery
```bash
# Test disaster recovery
./scripts/dr-test.sh

# Perform failover
./scripts/failover.sh
```

## Maintenance Procedures

### Rolling Updates
```bash
# Update agent version
kubectl set image deployment/aats-agent \
  aats-agent=aats-agent:new-version --record

# Monitor rollout
kubectl rollout status deployment/aats-agent
```

### Database Maintenance
```bash
# Schedule maintenance window
kubectl apply -f maintenance/database-maintenance.yaml

# Monitor maintenance status
kubectl get pods -l maintenance=true
```

## Troubleshooting

### Common Issues

1. **Pod Startup Issues**
```bash
# Check pod status
kubectl get pods -n aats-prod
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

2. **Database Connection Issues**
```bash
# Check database connectivity
kubectl exec -it <pod-name> -- pg_isready -h <database-host>
kubectl exec -it <pod-name> -- mongosh --eval "db.runCommand({ping:1})"
```

3. **Resource Issues**
```bash
# Check resource usage
kubectl top pods
kubectl top nodes
```

### Health Checks

```bash
# Check system health
./scripts/health-check.sh

# Generate health report
./scripts/generate-health-report.sh
```

## Monitoring and Alerts

### Prometheus Queries
```promql
# CPU Usage
rate(container_cpu_usage_seconds_total{namespace="aats-prod"}[5m])

# Memory Usage
container_memory_usage_bytes{namespace="aats-prod"}

# Error Rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Alert Rules
```yaml
groups:
- name: aats-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High error rate detected
```

## Performance Tuning

### JVM Settings
```yaml
env:
- name: JAVA_OPTS
  value: "-Xms2g -Xmx4g -XX:+UseG1GC"
```

### Database Tuning
```yaml
postgresql:
  parameters:
    max_connections: 200
    shared_buffers: 4GB
    effective_cache_size: 12GB
```

## Security Hardening

### Pod Security Policies
```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: aats-restricted
spec:
  privileged: false
  seLinux:
    rule: RunAsAny
  runAsUser:
    rule: MustRunAsNonRoot
  fsGroup:
    rule: RunAsAny
  volumes:
  - configMap
  - emptyDir
  - projected
  - secret
  - downwardAPI
  - persistentVolumeClaim
```

## Compliance and Auditing

### Audit Logging
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata
  resources:
  - group: ""
    resources: ["pods", "services"]
```

## Support and Escalation

### Contact Information
- **DevOps Team**: devops@aats.ai
- **Security Team**: security@aats.ai
- **On-Call Support**: oncall@aats.ai

### Escalation Procedures
1. L1 Support: On-call engineer
2. L2 Support: Team lead
3. L3 Support: System architect
4. Emergency: CTO/VP Engineering

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Istio Documentation](https://istio.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
