// CI\CD Pipeline for my python Weather App project:
// This pipeline builds, tests, and pushes container images to AWS ECR, then updates GitOps repo for ArgoCD to deploy automatically.
//
// Prerequisites:
// - Jenkins service account with IRSA role for ECR push
// - GitHub token in Jenkins credentials (id: 'github-token')

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
    image: python:3.11-slim
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

  - name: git
    image: alpine/git:latest
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
    image: amazon/aws-cli:2.17.6
    command: ['cat']
    tty: true
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

  volumes:
  - name: varlibcontainers
    emptyDir: {}
  - name: shared-data
    emptyDir: {}
"""
        }
    }

    triggers {
        // Poll SCM every 5 minutes
        pollSCM('H/5 * * * *')
    }

    environment {
        // AWS Configuration
        AWS_REGION = 'eu-central-1'
        ECR_REGISTRY = '536697238781.dkr.ecr.eu-central-1.amazonaws.com'
        ECR_REPOSITORY = 'weather-app'

        // GitOps Configuration
        GITOPS_REPO = 'https://github.com/matanweisz/gitops-project.git'
        GITOPS_VALUES_PATH = 'apps/weather-app/values.yaml'

        // Build Configuration
        IMAGE_TAG = "${BUILD_NUMBER}-${GIT_COMMIT.take(8)}"
    }

    stages {
        stage('Checkout') {
            steps {
                echo "Checking out source code..."
                checkout scm

                script {
                    echo "=== Build Information ==="
                    echo "Build Number: ${BUILD_NUMBER}"
                    echo "Git Commit:   ${GIT_COMMIT}"
                    echo "Image Tag:    ${IMAGE_TAG}"
                    echo "ECR Image:    ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
                }
            }
        }

        // Static Analysis (Runs in parallel)
        stage('Static Analysis') {
            parallel {
                // Check Dockerfile syntax
                stage('Lint Dockerfile') {
                    steps {
                        container('hadolint') {
                            echo "Linting Dockerfile..."
                            sh 'hadolint Dockerfile || true'
                        }
                    }
                }

                // Check Python syntax and security
                stage('Python Analysis') {
                    steps {
                        container('python') {
                            echo "Running Python static analysis..."
                            sh '''
                                pip install --quiet pylint bandit
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

        // Building docker container image using Buildah for daemonless build
        stage('Build Image') {
            steps {
                container('buildah') {
                    echo "Building container image with Buildah..."
                    sh """
                        buildah --storage-driver overlay bud \
                            -f Dockerfile \
                            -t ${ECR_REPOSITORY}:${IMAGE_TAG} \
                            .
                    """
                    echo "Image built: ${ECR_REPOSITORY}:${IMAGE_TAG}"
                }
            }
        }

        // Push the container image to AWS ECR
        stage('Push to ECR') {
            steps {
                script {
                    echo "Authenticating to ECR..."
                    container('aws') {
                        sh "aws ecr get-login-password --region ${AWS_REGION} > /data/ecr_password"
                    }

                    echo "Pushing image with Buildah..."
                    container('buildah') {
                        sh """
                            # Authenticate to ECR using the password from the shared volume
                            cat /data/ecr_password | buildah login --username AWS --password-stdin ${ECR_REGISTRY}

                            # Tag with full ECR path
                            buildah tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}

                            # Push image
                            buildah push --storage-driver overlay ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
                        """
                    }
                    echo "The image ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG} has been pushed to ECR"
                }
            }
        }

        // Updating the GitOps repo to deploy the new image using yq
        stage('Update GitOps') {
            steps {
                container('git') {
                    withCredentials([string(credentialsId: 'github-token', variable: 'GITHUB_TOKEN')]) {
                        echo "Updating GitOps repository..."
                        sh '''
                            # Install yq for YAML manipulation
                            apk add --no-cache yq

                            # Configure Git
                            git config --global user.name "jenkins-user"
                            git config --global user.email "jenkins-user@matanweisz.xyz"

                            # Clone GitOps repo using token (shallow clone for efficiency)
                            git clone --depth 1 https://${GITHUB_TOKEN}@github.com/matanweisz/gitops-project.git gitops-repo
                            cd gitops-repo

                            # Update image tag
                            echo "Updating image tag to: ${IMAGE_TAG}"
                            yq eval -i '.image.tag = "'${IMAGE_TAG}'"' ${GITOPS_VALUES_PATH}

                            # Commit and push
                            git add ${GITOPS_VALUES_PATH}
                            git commit -m "Jenkins updated the weather-app image to ${IMAGE_TAG}

Built from commit: ${GIT_COMMIT}
Jenkins build number: ${BUILD_NUMBER}
Image: ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

                            git push origin main
                        '''
                        echo "GitOps repository updated successfully"
                    }
                }
            }
        }
    }

    // Post-Build Actions
    post {
        success {
            echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✓ PIPELINE SUCCESS                            ║
╚════════════════════════════════════════════════════════════════╝

Image:     ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
GitOps:    Updated successfully
Next:      ArgoCD will deploy automatically (~5 min)

Check ArgoCD: https://argocd.matanweisz.xyz
Check the GitOps repo: https://github.com/matanweisz/gitops-project
Check the website: https://matanweisz.xyz
"""
        }

        failure {
            echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✗ PIPELINE FAILED                             ║
╚════════════════════════════════════════════════════════════════╝

Check logs above for error details.
"""
        }

        cleanup {
            // Clean up cloned GitOps repository
            sh 'rm -rf gitops-repo || true'
        }
    }
}
