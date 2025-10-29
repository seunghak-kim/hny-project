# 배포 가이드

**버전**: 1.0
**작성일**: 2025-10-14
**환경**: 개발 → 스테이징 → 프로덕션

---

## 📚 목차

- [배포 개요](#-배포-개요)
- [환경 구성](#-환경-구성)
- [Docker 배포](#-docker-배포)
- [Kubernetes 배포](#-kubernetes-배포)
- [CI/CD 파이프라인](#-cicd-파이프라인)
- [모니터링 및 로깅](#-모니터링-및-로깅)
- [보안 설정](#-보안-설정)
- [롤백 및 복구](#-롤백-및-복구)

---

## 🎯 배포 개요

### 배포 전략

| 환경 | 용도 | 도메인 (예시) | 상태 |
|------|------|--------------|------|
| **Development** | 로컬 개발 | `localhost:8000` | ✅ 구축 완료 |
| **Staging** | 테스트 환경 | `staging.holmesnyangz.com` | 🔜 예정 |
| **Production** | 실서비스 | `api.holmesnyangz.com` | 🔜 예정 |

### 아키텍처 (프로덕션)

```mermaid
flowchart LR
    Users([사용자])

    subgraph CloudFlare["☁️ CloudFlare"]
        CDN[CDN + DDoS Protection]
    end

    subgraph LoadBalancer["⚖️ Load Balancer"]
        NGINX[NGINX]
    end

    subgraph Backend["🔧 Backend Cluster"]
        API1[FastAPI Pod 1]
        API2[FastAPI Pod 2]
        API3[FastAPI Pod 3]
    end

    subgraph Database["💾 Database"]
        PG[PostgreSQL Primary]
        PG_R[PostgreSQL Replica]
    end

    subgraph Cache["⚡ Cache"]
        Redis[Redis Cluster]
    end

    subgraph Monitoring["📊 Monitoring"]
        Prometheus[Prometheus]
        Grafana[Grafana]
        Sentry[Sentry]
    end

    Users --> CDN
    CDN --> NGINX
    NGINX --> API1
    NGINX --> API2
    NGINX --> API3

    API1 --> PG
    API2 --> PG
    API3 --> PG

    PG --> PG_R

    API1 --> Redis
    API2 --> Redis
    API3 --> Redis

    API1 -.-> Prometheus
    API2 -.-> Prometheus
    API3 -.-> Prometheus

    Prometheus --> Grafana
    API1 -.-> Sentry
```

---

## ⚙️ 환경 구성

### 1. 환경 변수 (.env)

#### Development

```bash
# .env.development
NODE_ENV=development
LOG_LEVEL=DEBUG

# OpenAI
OPENAI_API_KEY=sk-...

# PostgreSQL (Local)
DATABASE_URL=postgresql://postgres:root1234@localhost:5432/real_estate

# Redis (Optional)
# REDIS_URL=redis://localhost:6379/0
```

#### Staging

```bash
# .env.staging
NODE_ENV=staging
LOG_LEVEL=INFO

# OpenAI
OPENAI_API_KEY=sk-...

# PostgreSQL (Cloud)
DATABASE_URL=postgresql://user:password@staging-db.example.com:5432/real_estate

# Redis
REDIS_URL=redis://staging-redis.example.com:6379/0

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/yyy
```

#### Production

```bash
# .env.production
NODE_ENV=production
LOG_LEVEL=WARNING

# OpenAI
OPENAI_API_KEY=sk-...

# PostgreSQL (HA Cluster)
DATABASE_URL=postgresql://user:password@prod-db.example.com:5432/real_estate

# Redis (Cluster)
REDIS_URL=redis://prod-redis.example.com:6379/0

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/yyy
PROMETHEUS_MULTIPROC_DIR=/tmp

# Security
CORS_ORIGINS=["https://holmesnyangz.com"]
ALLOWED_HOSTS=["api.holmesnyangz.com"]
```

---

## 🐳 Docker 배포

### 1. Dockerfile (Backend)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# 작업 디렉토리
WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY . .

# 비루트 사용자
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 실행
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. Docker Compose (전체 스택)

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: real_estate
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis (Optional)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/real_estate
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    restart: unless-stopped

  # Frontend (Optional)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_WS_URL: ws://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

  # NGINX (Reverse Proxy)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3. 빌드 및 실행

```bash
# 이미지 빌드
docker-compose build

# 컨테이너 시작 (detached mode)
docker-compose up -d

# 로그 확인
docker-compose logs -f backend

# 컨테이너 중지
docker-compose down

# 볼륨 포함 삭제 (주의!)
docker-compose down -v
```

### 4. Docker Hub 배포

```bash
# 이미지 태깅
docker tag holmesnyangz-backend:latest holmesnyangz/backend:1.0.0
docker tag holmesnyangz-backend:latest holmesnyangz/backend:latest

# Docker Hub 로그인
docker login

# 이미지 푸시
docker push holmesnyangz/backend:1.0.0
docker push holmesnyangz/backend:latest
```

---

## ☸️ Kubernetes 배포

### 1. Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: holmesnyangz
```

### 2. ConfigMap (환경 변수)

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: holmesnyangz
data:
  LOG_LEVEL: "INFO"
  POSTGRES_HOST: "postgres-service"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "real_estate"
  REDIS_URL: "redis://redis-service:6379/0"
```

### 3. Secret (민감 정보)

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
  namespace: holmesnyangz
type: Opaque
data:
  OPENAI_API_KEY: <base64-encoded>
  POSTGRES_PASSWORD: <base64-encoded>
```

```bash
# Secret 생성 (CLI)
kubectl create secret generic backend-secret \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=POSTGRES_PASSWORD=root1234 \
  -n holmesnyangz
```

### 4. Deployment (Backend)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: holmesnyangz
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: holmesnyangz/backend:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: backend-config
              key: LOG_LEVEL
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: backend-secret
              key: OPENAI_API_KEY
        - name: DATABASE_URL
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)"
        envFrom:
        - configMapRef:
            name: backend-config
        - secretRef:
            name: backend-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 5. Service (LoadBalancer)

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: holmesnyangz
spec:
  type: LoadBalancer
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

### 6. Ingress (NGINX)

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: backend-ingress
  namespace: holmesnyangz
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.holmesnyangz.com
    secretName: backend-tls
  rules:
  - host: api.holmesnyangz.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
```

### 7. HPA (Horizontal Pod Autoscaler)

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: holmesnyangz
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 8. 배포 실행

```bash
# Namespace 생성
kubectl apply -f k8s/namespace.yaml

# ConfigMap & Secret
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Deployment & Service
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Ingress
kubectl apply -f k8s/ingress.yaml

# HPA
kubectl apply -f k8s/hpa.yaml

# 상태 확인
kubectl get all -n holmesnyangz
kubectl get pods -n holmesnyangz -w

# 로그 확인
kubectl logs -f deployment/backend -n holmesnyangz
```

---

## 🔄 CI/CD 파이프라인

### GitHub Actions (예시)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches:
      - main

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: ./backend
        push: true
        tags: |
          holmesnyangz/backend:latest
          holmesnyangz/backend:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v4
      with:
        manifests: |
          k8s/deployment.yaml
          k8s/service.yaml
        images: |
          holmesnyangz/backend:${{ github.sha }}
        namespace: holmesnyangz

    - name: Verify deployment
      run: |
        kubectl rollout status deployment/backend -n holmesnyangz
```

---

## 📊 모니터링 및 로깅

### 1. Prometheus + Grafana

```yaml
# k8s/monitoring/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: holmesnyangz
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'backend'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - holmesnyangz
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: backend
```

### 2. Sentry (에러 추적)

```python
# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("NODE_ENV", "development")
)
```

### 3. 로깅 (ELK Stack)

```yaml
# k8s/logging/filebeat.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
  namespace: holmesnyangz
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/*backend*.log
    output.elasticsearch:
      hosts: ["elasticsearch:9200"]
```

---

## 🔒 보안 설정

### 1. HTTPS (Let's Encrypt)

```bash
# cert-manager 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# ClusterIssuer 생성
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@holmesnyangz.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 2. Network Policies

```yaml
# k8s/security/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-netpol
  namespace: holmesnyangz
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

---

## 🔙 롤백 및 복구

### 1. Kubernetes 롤백

```bash
# 롤아웃 히스토리 확인
kubectl rollout history deployment/backend -n holmesnyangz

# 이전 버전으로 롤백
kubectl rollout undo deployment/backend -n holmesnyangz

# 특정 리비전으로 롤백
kubectl rollout undo deployment/backend --to-revision=2 -n holmesnyangz

# 롤아웃 상태 확인
kubectl rollout status deployment/backend -n holmesnyangz
```

### 2. 데이터베이스 복구

```bash
# 백업에서 복구
psql -U postgres -d real_estate < backup_20251014.sql

# PITR (Point-in-Time Recovery) - PostgreSQL
# 1. WAL 아카이브 복사
# 2. recovery.conf 설정
# 3. PostgreSQL 재시작
```

---

## 📋 체크리스트

### 배포 전

- [ ] `.env.production` 파일 확인
- [ ] Secret 생성 및 검증
- [ ] 데이터베이스 백업
- [ ] 롤백 계획 수립
- [ ] 모니터링 도구 준비

### 배포 중

- [ ] Docker 이미지 빌드
- [ ] 이미지 푸시 (Docker Hub)
- [ ] Kubernetes 배포
- [ ] Health Check 확인
- [ ] Smoke Test 실행

### 배포 후

- [ ] 로그 확인 (에러 없음)
- [ ] 모니터링 대시보드 확인
- [ ] API 응답 시간 확인
- [ ] 사용자 피드백 수집
- [ ] 문서 업데이트

---

**생성일**: 2025-10-14
**버전**: 1.0
**상태**: 📋 배포 준비 가이드
