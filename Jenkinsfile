// Multi-Environment CI/CD Pipeline for Weather App
// This pipeline builds, tests, scans, and pushes container images to AWS ECR,
// then updates the GitOps repo for ArgoCD to deploy to the appropriate environment.
//
// Branch Strategy:
//   - dev  → dev environment  → weather-app-dev ECR
//   - stg  → stg environment  → weather-app-stg ECR
//   - main → prod environment → weather-app-prod ECR
//
// Prerequisites:
// - Jenkins service account with IRSA role for ECR push
// - GitHub token in Jenkins credentials (id: 'github-creds')
// - Environment-specific ECR repositories (weather-app-dev, weather-app-stg, weather-app-prod)

pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  namespace: jenkins
spec:
  serviceAccountName: jenkins
  containers:
  - name: jnlp
    image: jenkins/inbound-agent:latest-jdk21
    resources:
      requests:
        cpu: "100m"
        memory: "256Mi"
      limits:
        cpu: "300m"
        memory: "512Mi"

  - name: buildah
    image: quay.io/buildah/stable:v1.37
    command: ['cat']
    tty: true
    env:
    - name: STORAGE_DRIVER
      value: overlay
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
      capabilities:
        add: ['SETUID', 'SETGID']
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "1000m"
        memory: "1Gi"
    volumeMounts:
    - name: varlibcontainers
      mountPath: /var/lib/containers
    - name: shared-data
      mountPath: /data

  - name: python
    image: python:slim
    command: ['cat']
    tty: true
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"

  - name: hadolint
    image: hadolint/hadolint:v2.14.0-debian
    command: ['cat']
    tty: true
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"

  - name: trivy
    image: aquasec/trivy:0.68.1
    command: ['cat']
    tty: true
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
    volumeMounts:
    - name: varlibcontainers
      mountPath: /var/lib/containers
      readOnly: true

  - name: git
    image: alpine/git:2.49.1
    command: ['cat']
    tty: true
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"

  - name: aws
    image: amazon/aws-cli:2.32.8
    command: ['cat']
    tty: true
    env:
    - name: AWS_ROLE_ARN
      value: arn:aws:iam::536697238781:role/foundation-terraform-project-jenkins-ecr
    - name: AWS_WEB_IDENTITY_TOKEN_FILE
      value: /var/run/secrets/eks.amazonaws.com/serviceaccount/token
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"
    volumeMounts:
    - name: shared-data
      mountPath: /data
    - name: aws-iam-token
      mountPath: /var/run/secrets/eks.amazonaws.com/serviceaccount
      readOnly: true

  volumes:
  - name: varlibcontainers
    emptyDir: {}
  - name: shared-data
    emptyDir: {}
  - name: aws-iam-token
    projected:
      sources:
      - serviceAccountToken:
          audience: sts.amazonaws.com
          expirationSeconds: 86400
          path: token
"""
        }
    }

    environment {
        // AWS Configuration
        AWS_REGION = 'eu-central-1'
        AWS_ACCOUNT_ID = '536697238781'

        // Environment-specific ECR repositories
        DEV_ECR_REPO = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/weather-app-dev"
        STG_ECR_REPO = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/weather-app-stg"
        PROD_ECR_REPO = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/weather-app-prod"

        // GitOps Configuration
        GITOPS_REPO = 'https://github.com/matanweisz/gitops-project.git'

        // Build Configuration
        IMAGE_TAG = "${BUILD_NUMBER}-${GIT_COMMIT.take(8)}"

        // Environment determination (set dynamically in Determine Environment stage)
        TARGET_ENV = ''
        ECR_REGISTRY = ''
        ECR_REPOSITORY = ''
        FULL_IMAGE_NAME = ''
        GITOPS_VALUES_PATH = ''
        DEPLOY_ENABLED = ''
    }

    stages {
        stage('Determine Environment') {
            steps {
                script {
                    // Map branch to environment
                    def branchToEnv = [
                        'dev': 'dev',
                        'stg': 'stg',
                        'main': 'prod'
                    ]

                    env.TARGET_ENV = branchToEnv[env.BRANCH_NAME] ?: 'unknown'

                    // Set environment-specific ECR repository
                    if (env.TARGET_ENV == 'dev') {
                        env.ECR_REGISTRY = env.DEV_ECR_REPO.split('/')[0]
                        env.ECR_REPOSITORY = 'weather-app-dev'
                        env.FULL_IMAGE_NAME = env.DEV_ECR_REPO
                    } else if (env.TARGET_ENV == 'stg') {
                        env.ECR_REGISTRY = env.STG_ECR_REPO.split('/')[0]
                        env.ECR_REPOSITORY = 'weather-app-stg'
                        env.FULL_IMAGE_NAME = env.STG_ECR_REPO
                    } else if (env.TARGET_ENV == 'prod') {
                        env.ECR_REGISTRY = env.PROD_ECR_REPO.split('/')[0]
                        env.ECR_REPOSITORY = 'weather-app-prod'
                        env.FULL_IMAGE_NAME = env.PROD_ECR_REPO
                    }

                    // Only deploy for known branches
                    if (env.TARGET_ENV == 'unknown') {
                        env.DEPLOY_ENABLED = 'false'
                        echo "⚠️  Branch '${BRANCH_NAME}' is not mapped to an environment. Build only, no deployment."
                    } else {
                        env.DEPLOY_ENABLED = 'true'
                        env.GITOPS_VALUES_PATH = "apps/applications/weather-app/environments/${env.TARGET_ENV}.yaml"
                    }

                    echo """
╔════════════════════════════════════════════════════════════════╗
║                  BUILD INFORMATION                             ║
╚════════════════════════════════════════════════════════════════╝

Branch:        ${BRANCH_NAME}
Environment:   ${TARGET_ENV}
Build Number:  ${BUILD_NUMBER}
Git Commit:    ${GIT_COMMIT}
Image Tag:     ${IMAGE_TAG}
ECR Registry:  ${ECR_REGISTRY}
ECR Repo:      ${ECR_REPOSITORY}
Full Image:    ${FULL_IMAGE_NAME}:${IMAGE_TAG}
Deploy:        ${DEPLOY_ENABLED}
${DEPLOY_ENABLED == 'true' ? "Values Path:   ${GITOPS_VALUES_PATH}" : ""}
"""
                }
            }
        }

        stage('Checkout') {
            steps {
                echo "Checking out source code from ${BRANCH_NAME}..."
                checkout scm
            }
        }

        // Static Analysis (Runs in parallel)
        stage('Static Analysis') {
            parallel {
                stage('Lint Dockerfile') {
                    steps {
                        container('hadolint') {
                            echo "Linting Dockerfile..."
                            sh 'hadolint Dockerfile || true'
                        }
                    }
                }

                stage('Python Analysis') {
                    steps {
                        container('python') {
                            echo "Running Python static analysis..."
                            sh '''
                                pip install --quiet pylint bandit
                                pip install --quiet -r requirements.txt
                                echo "Running pylint..."
                                pylint app.py || true
                                echo "Running bandit security scan..."
                                bandit -r . -ll || true
                            '''
                        }
                    }
                }
            }
        }

        // Build container image
        stage('Build Image') {
            steps {
                container('buildah') {
                    echo "Building container image with Buildah..."
                    sh """
                        buildah --storage-driver \${STORAGE_DRIVER} bud \\
                            --format docker \\
                            -f Dockerfile \\
                            -t ${ECR_REPOSITORY}:${IMAGE_TAG} \\
                            .
                    """
                    echo "✓ Image built: ${ECR_REPOSITORY}:${IMAGE_TAG}"
                }
            }
        }

        // Security scan with Trivy
        stage('Image Scan') {
            steps {
                container('trivy') {
                    echo "Scanning image for vulnerabilities with Trivy..."
                    sh """
                        # Scan the image built by Buildah
                        # Use the directory-based scanning since image is in Buildah storage
                        trivy rootfs --severity HIGH,CRITICAL \
                            --exit-code 0 \
                            --no-progress \
                            --format table \
                            /var/lib/containers/storage || true

                        echo ""
                        echo "Security scan completed. Review vulnerabilities above."
                        echo "Note: HIGH and CRITICAL vulnerabilities are shown."
                        echo "Pipeline continues regardless of findings (exit-code 0)."
                    """
                }
            }
        }

        // Push to ECR
        stage('Push to ECR') {
            steps {
                script {
                    echo "Authenticating to ECR with IRSA..."
                    container('aws') {
                        sh """
                            echo 'Testing AWS STS Credentials...'
                            aws sts get-caller-identity

                            echo 'Generating ECR Login Password...'
                            aws ecr get-login-password --region ${AWS_REGION} > /data/ecr_password
                            echo "ECR login password generated"
                        """
                    }

                    echo "Pushing image to environment-specific ECR repository..."
                    container('buildah') {
                        sh """
                            # Authenticate to ECR
                            cat /data/ecr_password | buildah login --username AWS --password-stdin ${ECR_REGISTRY}

                            # Tag with full ECR path (environment-specific)
                            buildah --storage-driver \${STORAGE_DRIVER} tag \\
                                ${ECR_REPOSITORY}:${IMAGE_TAG} \\
                                ${FULL_IMAGE_NAME}:${IMAGE_TAG}

                            # Push to environment-specific ECR repository
                            buildah --storage-driver \${STORAGE_DRIVER} push \\
                                ${FULL_IMAGE_NAME}:${IMAGE_TAG}
                        """
                    }
                    echo "✓ Image pushed: ${FULL_IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
        }

        // Production approval gate
        stage('Approve Production Deployment') {
            when {
                expression { env.TARGET_ENV == 'prod' }
            }
            steps {
                script {
                    timeout(time: 15, unit: 'MINUTES') {
                        input(
                            message: "Deploy ${IMAGE_TAG} to PRODUCTION?",
                            ok: 'Deploy to Production',
                            submitter: 'authenticated'
                        )
                    }
                }
            }
        }

        // Update GitOps repository
        stage('Update GitOps') {
            when {
                expression { env.DEPLOY_ENABLED == 'true' }
            }
            steps {
                container('git') {
                    withCredentials([usernamePassword(
                        credentialsId: 'github-creds',
                        usernameVariable: 'GIT_USERNAME',
                        passwordVariable: 'GIT_PASSWORD'
                    )]) {
                        echo "Updating GitOps repository for ${TARGET_ENV} environment..."
                        sh '''
                            # Install yq for YAML manipulation
                            apk add --no-cache yq

                            # Configure Git
                            git config --global user.name "Jenkins CI"
                            git config --global user.email "jenkins@matanweisz.xyz"

                            # Clone GitOps repo (shallow clone for efficiency)
                            git clone --depth 1 https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/matanweisz/gitops-project.git gitops-repo
                            cd gitops-repo

                            # Update image tag in environment-specific values file
                            echo "Updating ${TARGET_ENV} image tag to: ${IMAGE_TAG}"
                            yq eval -i '.image.tag = "'${IMAGE_TAG}'"' ${GITOPS_VALUES_PATH}

                            # Commit and push changes
                            git add ${GITOPS_VALUES_PATH}
                            git commit -m "ci: Update weather-app ${TARGET_ENV} to ${IMAGE_TAG}

Environment: ${TARGET_ENV}
Build: ${BUILD_NUMBER}
Branch: ${BRANCH_NAME}
Commit: ${GIT_COMMIT}
Image: ${FULL_IMAGE_NAME}:${IMAGE_TAG}"

                            git push origin main
                        '''
                        echo "✓ GitOps repository updated for ${TARGET_ENV}"
                    }
                }
            }
        }
    }

    // Post-Build Actions
    post {
        success {
            script {
                if (env.DEPLOY_ENABLED == 'true') {
                    echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✓ PIPELINE SUCCESS                            ║
╚════════════════════════════════════════════════════════════════╝

Branch:        ${BRANCH_NAME}
Environment:   ${TARGET_ENV}
Image:         ${FULL_IMAGE_NAME}:${IMAGE_TAG}
ECR Repo:      ${ECR_REPOSITORY}
GitOps:        Updated successfully
Security Scan: Completed (see Image Scan stage)
Next:          ArgoCD will deploy to ${TARGET_ENV} (~5 min)

Check ArgoCD:      https://argocd.matanweisz.xyz
Check GitOps repo: https://github.com/matanweisz/gitops-project
Check website:     https://matanweisz.xyz
"""
                } else {
                    echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✓ BUILD SUCCESS                               ║
╚════════════════════════════════════════════════════════════════╝

Branch:        ${BRANCH_NAME}
Image:         Built locally (not pushed)
Note:          Branch not mapped to environment - no deployment
"""
                }
            }
        }

        failure {
            echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✗ PIPELINE FAILED                             ║
╚════════════════════════════════════════════════════════════════╝

Branch:        ${BRANCH_NAME}
Environment:   ${TARGET_ENV}

Check logs above for error details.
"""
        }
    }
}
