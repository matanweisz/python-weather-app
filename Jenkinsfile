// Multi-Environment CI/CD Pipeline for Weather App
// Simplified multibranch pipeline following 2024-2025 best practices
//
// Branch Strategy:
//   - dev  → dev environment  → weather-app-dev ECR
//   - stg  → stg environment  → weather-app-stg ECR
//   - main → prod environment → weather-app-prod ECR

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
            retries 2
        }
    }

    options {
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        // AWS Configuration
        AWS_REGION = 'eu-central-1'
        AWS_ACCOUNT_ID = '536697238781'
        ECR_REGISTRY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

        // Dynamic variables set in stages
        IMAGE_TAG = ''
    }

    stages {
        stage('Static Analysis') {
            parallel {
                stage('Lint Dockerfile') {
                    steps {
                        container('hadolint') {
                            sh 'hadolint Dockerfile || true'
                        }
                    }
                }

                stage('Python Lint') {
                    steps {
                        container('python') {
                            sh '''
                                pip install --quiet pylint bandit
                                pip install --quiet -r requirements.txt
                                pylint app.py || true
                                bandit -r . -ll || true
                            '''
                        }
                    }
                }
            }
        }

        stage('Test') {
            steps {
                container('python') {
                    sh '''
                        pip install --quiet pytest
                        pip install --quiet -r requirements.txt
                        export PYTHONPATH="${PYTHONPATH}:$(pwd)"
                        pytest tests/ -v
                    '''
                }
            }
        }

        stage('Build Image') {
            steps {
                container('git') {
                    script {
                        gitCommit = sh(script: 'git rev-parse --short=8 HEAD', returnStdout: true).trim()
                        env.IMAGE_TAG = "${BUILD_NUMBER}-${gitCommit}"
                    }
                }
                container('buildah') {
                    script {
                        echo "Building image with tag: ${IMAGE_TAG}"
                        sh """
                            buildah --storage-driver \${STORAGE_DRIVER} bud \\
                                --format docker \\
                                -f Dockerfile \\
                                -t weather-app:${IMAGE_TAG} \\
                                .

                            # Export image as OCI archive for security scanning
                            buildah --storage-driver \${STORAGE_DRIVER} push \\
                                weather-app:${IMAGE_TAG} \\
                                oci-archive:/data/weather-app.tar
                        """
                    }
                }
            }
        }

        stage('Security Scan') {
            steps {
                container('trivy') {
                    sh """
                        trivy image --input /data/weather-app.tar \\
                            --severity HIGH,CRITICAL \\
                            --exit-code 1 \\
                            --no-progress \\
                            --format table

                        echo ""
                        echo "✓ Security scan passed: No HIGH/CRITICAL vulnerabilities found"
                    """
                }
            }
        }

        stage('Push to ECR') {
            when {
                beforeAgent true
                anyOf {
                    branch 'dev'
                    branch 'stg'
                    branch 'main'
                }
            }
            steps {
                script {
                    // Map branch to ECR repository
                    def envSuffix = BRANCH_NAME == 'main' ? 'prod' : BRANCH_NAME
                    def ecrRepo = "${ECR_REGISTRY}/weather-app-${envSuffix}"

                    container('aws') {
                        sh "aws ecr get-login-password --region ${AWS_REGION} > /data/ecr_password"
                    }

                    container('buildah') {
                        sh """
                            cat /data/ecr_password | buildah login --username AWS --password-stdin ${ECR_REGISTRY}
                            buildah --storage-driver \${STORAGE_DRIVER} tag weather-app:${IMAGE_TAG} ${ecrRepo}:${IMAGE_TAG}
                            buildah --storage-driver \${STORAGE_DRIVER} push ${ecrRepo}:${IMAGE_TAG}
                        """
                        echo "✓ Pushed to ${envSuffix}: ${ecrRepo}:${IMAGE_TAG}"
                    }
                }
            }
        }

        stage('Approve Production') {
            when {
                beforeAgent true
                branch 'main'
            }
            steps {
                timeout(time: 15, unit: 'MINUTES') {
                    input message: "Deploy ${IMAGE_TAG} to production?", ok: 'Deploy'
                }
            }
        }

        stage('Update GitOps') {
            when {
                beforeAgent true
                anyOf {
                    branch 'dev'
                    branch 'stg'
                    branch 'main'
                }
            }
            steps {
                container('git') {
                    withCredentials([usernamePassword(
                        credentialsId: 'github-creds',
                        usernameVariable: 'GIT_USERNAME',
                        passwordVariable: 'GIT_PASSWORD'
                    )]) {
                        script {
                            // Map branch to environment
                            def env = BRANCH_NAME == 'main' ? 'prod' : BRANCH_NAME
                            def valuesPath = "apps/applications/weather-app/environments/${env}.yaml"

                            sh """
                                apk add --no-cache yq
                                git config --global user.name "Jenkins CI"
                                git config --global user.email "jenkins@matanweisz.xyz"

                                git clone --depth 1 https://\${GIT_USERNAME}:\${GIT_PASSWORD}@github.com/matanweisz/gitops-project.git gitops
                                cd gitops

                                yq eval -i '.image.tag = "${IMAGE_TAG}"' ${valuesPath}

                                git add ${valuesPath}
                                git commit -m "ci: Update weather-app ${env} to ${IMAGE_TAG}"
                                git push origin main
                            """
                            echo "✓ GitOps updated for ${env} environment"
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            script {
                def isDeployBranch = BRANCH_NAME in ['dev', 'stg', 'main']
                def env = BRANCH_NAME == 'main' ? 'prod' : BRANCH_NAME

                if (isDeployBranch) {
                    echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✓ PIPELINE SUCCESS                            ║
╚════════════════════════════════════════════════════════════════╝

Branch:       ${BRANCH_NAME}
Environment:  ${env}
Image Tag:    ${IMAGE_TAG}
Status:       Deployed via GitOps

Next: ArgoCD will sync to ${env} (~5 min)
"""
                } else {
                    echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✓ BUILD SUCCESS                               ║
╚════════════════════════════════════════════════════════════════╝

Branch:       ${BRANCH_NAME}
Image Tag:    ${IMAGE_TAG}
Status:       Built (no deployment for this branch)
"""
                }
            }
        }

        failure {
            echo """
╔════════════════════════════════════════════════════════════════╗
║                  ✗ PIPELINE FAILED                             ║
╚════════════════════════════════════════════════════════════════╝

Branch:       ${BRANCH_NAME}
Build:        ${BUILD_NUMBER}

Check console output for details.
"""
        }
    }
}
