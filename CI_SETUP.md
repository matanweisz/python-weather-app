# CI Pipeline Setup Guide

This guide explains how to set up the Jenkins CI pipeline for the weather-app.

## Overview

The CI pipeline (`Jenkinsfile`) automates:
1. **Static Analysis** - Lint Dockerfile and Python code
2. **Build** - Create container image with Buildah
3. **Push** - Upload image to AWS ECR
4. **Update GitOps** - Commit new image tag to GitOps repository

## Prerequisites

### 1. Jenkins Installed on Kubernetes

Jenkins must be running in the `jenkins` namespace with:
- Kubernetes plugin configured
- JCasC (Jenkins Configuration as Code) enabled
- GitHub credentials configured

### 2. IAM Role for ECR Access (IRSA)

The Jenkins service account must have an IAM role attached with ECR push permissions.

**Verify IRSA annotation**:
```bash
kubectl get sa jenkins -n jenkins -o yaml | grep eks.amazonaws.com/role-arn
```

Expected output:
```yaml
eks.amazonaws.com/role-arn: arn:aws:iam::536697238781:role/foundation-terraform-project-jenkins-ecr
```

**IAM Role Details**:
- **Role Name**: `foundation-terraform-project-jenkins-ecr`
- **Created by**: Terraform (`terraform/foundation/iam/main.tf`)
- **Trust Policy**: Allows `system:serviceaccount:jenkins:jenkins` and `system:serviceaccount:jenkins:default`

**Get role ARN from Terraform**:
```bash
cd terraform/foundation
terraform output jenkins_ecr_role_arn
```

**IAM Policy** (automatically created by Terraform):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ecr:GetAuthorizationToken"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:eu-central-1:536697238781:repository/weather-app"
    }
  ]
}
```

### 3. GitHub Credentials in Jenkins

The pipeline requires a GitHub Personal Access Token (PAT) to update the GitOps repository.

**Credential Setup**:
- **Credential ID**: `github-token` (must match this exactly)
- **Type**: Secret text
- **Secret**: Your GitHub PAT with `repo` scope
- **Location**: Already configured via External Secrets Operator (see `gitops/apps/external-secrets-config/templates/jenkins-external-secret.yaml`)

**The credential is automatically created** from AWS Secrets Manager:
```bash
# Verify the credential exists in Jenkins
# Path: /internal-cluster/jenkins/github-token in AWS Secrets Manager
aws secretsmanager get-secret-value \
  --region eu-central-1 \
  --secret-id /internal-cluster/jenkins/github-token \
  --query SecretString
```

**To create/update the GitHub token in AWS Secrets Manager**:
```bash
# Generate a GitHub PAT at: https://github.com/settings/tokens
# Required scopes: repo (full control of private repositories)

# Store in AWS Secrets Manager
aws secretsmanager put-secret-value \
  --region eu-central-1 \
  --secret-id /internal-cluster/jenkins/github-token \
  --secret-string "ghp_YourGitHubPersonalAccessToken"
```

### 4. ECR Repository

Verify the ECR repository exists:
```bash
aws ecr describe-repositories \
  --region eu-central-1 \
  --repository-names weather-app
```

---

## Jenkins Job Configuration

### Create Pipeline Job via Web UI

1. **Access Jenkins**:
   - Open: https://jenkins.matanweisz.xyz
   - Login with admin credentials

2. **Create New Job**:
   - Click "New Item"
   - Enter name: `weather-app-ci`
   - Select: "Pipeline"
   - Click "OK"

3. **Configure Pipeline**:

   **General Section**:
   - ✅ Check "GitHub project"
   - Project URL: `https://github.com/YOUR_USERNAME/weather-app/`

   **Build Triggers**:
   - ✅ Check "Poll SCM"
   - Schedule: `H/5 * * * *` (every 5 minutes)

   **Or use GitHub webhook** (requires Jenkins to be accessible from GitHub):
   - ✅ Check "GitHub hook trigger for GITScm polling"

   **Pipeline Section**:
   - Definition: `Pipeline script from SCM`
   - SCM: `Git`
   - Repository URL: `https://github.com/YOUR_USERNAME/weather-app.git`
   - Credentials: (none for public repo, or add GitHub PAT)
   - Branch Specifier: `*/main`
   - Script Path: `Jenkinsfile`

4. **Save and Test**:
   - Click "Save"
   - Click "Build Now"
   - Monitor build in "Console Output"

---

## Jenkinsfile Configuration

The `Jenkinsfile` is already configured with all necessary settings:

```groovy
environment {
    AWS_REGION = 'eu-central-1'                                      // ✅ Configured
    ECR_REGISTRY = '536697238781.dkr.ecr.eu-central-1.amazonaws.com' // ✅ Configured
    ECR_REPOSITORY = 'weather-app'                                   // ✅ Configured
    GITOPS_REPO = 'https://github.com/matanweisz/gitops-project.git' // ✅ Configured
    GITOPS_VALUES_PATH = 'apps/weather-app/values.yaml'              // ✅ Configured
}
```

**No manual configuration needed** - the Jenkinsfile is ready to use.

---

## Pipeline Stages Explained

### Stage 1: Checkout
- Clones the weather-app repository
- Displays build information (build number, git commit, image tag)

### Stage 2: Static Analysis (Parallel)
- **Lint Dockerfile**: Runs Hadolint to check Dockerfile best practices
- **Python Analysis**: Runs pylint and bandit for code quality and security

### Stage 3: Build Image
- Uses Buildah (rootless) to build container image
- Tags image with: `BUILD_NUMBER-GIT_COMMIT_SHA`
- Example: `123-a1b2c3d4`

### Stage 4: Push to ECR
- Authenticates to ECR using IRSA (no static credentials)
- Tags image with full ECR path
- Pushes image to ECR registry

### Stage 5: Update GitOps Repo
- Clones GitOps repository
- Updates `apps/weather-app/values.yaml` with new image tag
- Commits and pushes changes
- ArgoCD will detect the change and deploy automatically

---

## Testing the Pipeline

### 1. Manual Trigger

```bash
# Trigger build via CLI (requires Jenkins CLI)
java -jar jenkins-cli.jar -s https://jenkins.matanweisz.xyz/ build weather-app-ci
```

Or click "Build Now" in Jenkins UI.

### 2. Automatic Trigger (Git Push)

```bash
# Make a change to the weather-app
cd weather-app
echo "# Test change" >> README.md
git add README.md
git commit -m "test: Trigger CI pipeline"
git push

# Jenkins will detect the change within 5 minutes and start a build
```

### 3. Monitor Build

**Via Web UI**:
1. Go to https://jenkins.matanweisz.xyz
2. Click on `weather-app-ci` job
3. Click on latest build number
4. Click "Console Output"

**Via CLI**:
```bash
# Watch build logs
kubectl logs -n jenkins -l app.kubernetes.io/name=jenkins -f | grep weather-app-ci
```

---

## Verifying Pipeline Success

### 1. Check ECR Image

```bash
# List images in ECR
aws ecr list-images \
  --region eu-central-1 \
  --repository-name weather-app \
  --query 'imageIds[*].imageTag' \
  --output table

# Expected output includes: 123-a1b2c3d4, 124-b2c3d4e5, etc.
```

### 2. Check GitOps Repo

```bash
# Clone GitOps repo
git clone https://github.com/matanweisz/gitops-project.git
cd gitops-project

# Check latest commit
git log -1 --oneline
# Expected: "chore(weather-app): Update image to 123-a1b2c3d4"

# Check values.yaml
cat apps/weather-app/values.yaml | grep tag
# Expected: tag: "123-a1b2c3d4"
```

### 3. Check ArgoCD Deployment

```bash
# Check ArgoCD application status
kubectl get application prod-weather-app -n argocd

# Expected:
# NAME               SYNC STATUS   HEALTH STATUS
# prod-weather-app   Synced        Healthy
```

### 4. Check Running Pods

```bash
# Check pods in production cluster
kubectl --context prod-cluster get pods -n prod

# Verify image tag
kubectl --context prod-cluster get deployment prod-weather-app -n prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}'

# Expected: 536697238781.dkr.ecr.eu-central-1.amazonaws.com/weather-app:123-a1b2c3d4
```

---

## Troubleshooting

### Build Fails at "Push to ECR"

**Error**: `denied: User is not authorized to perform: ecr:PutImage`

**Solution**: Verify IRSA role has ECR permissions:
```bash
# Check service account annotation
kubectl get sa jenkins -n jenkins -o yaml

# Verify IAM role trust policy allows the service account
aws iam get-role --role-name foundation-terraform-project-jenkins-ecr --query 'Role.AssumeRolePolicyDocument'
```

### Build Fails at "Update GitOps Repo"

**Error**: `fatal: could not read Username for 'https://github.com'`

**Solution**: Verify GitHub token credential exists:
```bash
# Check External Secret status
kubectl get externalsecret jenkins-secrets -n jenkins -o yaml

# Verify secret was created
kubectl get secret jenkins-secrets -n jenkins -o jsonpath='{.data.github-token}' | base64 -d
```

### Pipeline Doesn't Trigger Automatically

**Issue**: Polling not working

**Solution 1**: Check SCM polling configuration:
- Go to Jenkins job → Configure → Build Triggers
- Verify "Poll SCM" is checked with schedule: `H/5 * * * *`

**Solution 2**: Set up GitHub webhook for instant triggers:
1. In GitHub repo: Settings → Webhooks → Add webhook
2. Payload URL: `https://jenkins.matanweisz.xyz/github-webhook/`
3. Content type: `application/json`
4. Events: "Just the push event"
5. Save webhook

### Image Not Deploying to Cluster

**Issue**: GitOps repo updated but ArgoCD not syncing

**Solution**: Check ArgoCD sync status:
```bash
# Force ArgoCD to sync
kubectl patch application prod-weather-app -n argocd --type merge \
  -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'

# Check ArgoCD logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller | grep weather-app
```

---

## Pipeline Optimization Tips

### 1. Use Multibranch Pipeline

For feature branch support:
- Create "Multibranch Pipeline" job instead of regular Pipeline
- Jenkins automatically creates builds for each branch
- Useful for testing before merging to main

### 2. Add Notifications

Send notifications on build success/failure:

```groovy
post {
    success {
        // Send Slack notification
        slackSend channel: '#deployments',
                  color: 'good',
                  message: "✓ Build ${BUILD_NUMBER} succeeded"
    }
    failure {
        // Send email
        emailext to: 'team@example.com',
                 subject: "Build Failed: ${JOB_NAME}",
                 body: "Build ${BUILD_NUMBER} failed. Check Jenkins."
    }
}
```

### 3. Add Test Stage

Insert after "Build Image":

```groovy
stage('Test Image') {
    steps {
        container('buildah') {
            sh """
                # Run image and test health endpoint
                podman run -d --name test-app -p 5000:5000 ${ECR_REPOSITORY}:${IMAGE_TAG}
                sleep 10
                curl http://localhost:5000/health
                podman stop test-app
                podman rm test-app
            """
        }
    }
}
```

---

## Security Best Practices

✅ **Implemented**:
- IRSA for AWS credentials (no static keys)
- GitHub token stored in AWS Secrets Manager
- Non-root container builds (Buildah)
- Immutable image tags
- Security scanning with Bandit

⚠️ **Recommended Additions**:
- Image vulnerability scanning (Trivy)
- SBOM generation
- Signed commits
- Image signing (Cosign)

---

## Summary

**Pipeline Components**:
- ✅ Jenkinsfile configured
- ✅ IRSA for ECR access
- ✅ GitHub token for GitOps updates
- ✅ Automatic polling every 5 minutes
- ✅ Multi-stage build process
- ✅ GitOps integration

**Deployment Flow**:
```
Git Push → Jenkins Detects Change → Build Image →
Push to ECR → Update GitOps Repo → ArgoCD Syncs → Deploy
```

**Expected Build Time**: 3-5 minutes

**Monitoring**: https://jenkins.matanweisz.xyz

For deployment monitoring, see `gitops/CD_SETUP.md`.
