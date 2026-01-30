pipeline {
    agent { label 'Agent-01' }

    options {
        disableConcurrentBuilds(abortPrevious: true)
        timestamps()
    }

    environment {
        DOCKER_IMAGE_PREFIX = 'qena_baas/'
        PROJECT_NAME = 'multi-tenant-notification-service-frontend'
        TARGET_FOLDER_DEV = '/root/source/containers/multi-tenant-notification-service-frontend'
        GIT_URL = 'https://gitlab.kifiya.et/ifi/bpass/multi-tenant-notification-service-frontend.git'
        GIT_CREDENTIALS_ID = 'gitlab-credentials'
        SSH_CRED_ID = 'DEV_SERVER_IP'
        CONTAINER_NAME = 'multi-tenant-notification-service'
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/development']],
                    userRemoteConfigs: [[
                        url: env.GIT_URL,
                        credentialsId: env.GIT_CREDENTIALS_ID
                    ]]
                ])
            }
        }

        stage('Build and Push Docker Image') {
            steps {
                withCredentials([
                    string(credentialsId: 'Registry_url', variable: 'DOCKER_REGISTRY'),
                    usernamePassword(
                        credentialsId: 'HARBOR_CREDENTIALS',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh """
                        echo "$DOCKER_PASS" | docker login $DOCKER_REGISTRY -u $DOCKER_USER --password-stdin
                        docker build -t $DOCKER_REGISTRY/${DOCKER_IMAGE_PREFIX}${PROJECT_NAME}:dev .
                        docker push $DOCKER_REGISTRY/${DOCKER_IMAGE_PREFIX}${PROJECT_NAME}:dev
                    """
                }
            }
        }

        stage('Deploy to Development Server') {
            steps {
                withCredentials([
                    string(credentialsId: 'DEV_SERVER_IP_1', variable: 'DEV_SERVER'),
                    string(credentialsId: 'Registry_url', variable: 'DOCKER_REGISTRY'),
                    usernamePassword(
                        credentialsId: 'HARBOR_CREDENTIALS',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    ),
                    sshUserPrivateKey(
                        credentialsId: 'DEV_SERVER_IP',
                        keyFileVariable: 'SSH_KEY_PATH',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {
                    sh """
                        chmod 400 ${SSH_KEY_PATH}

                        # Copy the compose file to the target server
                        scp -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no \
                          docker-compose.yml \
                          ${SSH_USER}@${DEV_SERVER}:${TARGET_FOLDER_DEV}/docker-compose.yml

                        # Execute Deployment on Remote Server
                        ssh -i ${SSH_KEY_PATH} -o StrictHostKeyChecking=no ${SSH_USER}@${DEV_SERVER} << EOF
                            set -e
                            cd ${TARGET_FOLDER_DEV}
                            
                            # 1. Login to Registry
                            echo "${DOCKER_PASS}" | docker login ${DOCKER_REGISTRY} -u ${DOCKER_USER} --password-stdin
                            
                            # 2. Pull latest images
                            docker compose pull
                            
                            # 3. Deploy (Without -v to preserve data)
                            # We use up -d which recreates only what changed.
                            docker compose up -d --remove-orphans
                            
                            # 4. Cleanup
                            docker logout ${DOCKER_REGISTRY}
                            docker image prune -f
EOF
                    """
                }
            }
        }
    }

    post {
        success {
            echo "✅ Successfully deployed ${PROJECT_NAME} to Development Server!"
        }
        failure {
            echo "❌ Pipeline failed. Check console output."
        }
        always {
            sh 'docker logout || true'
        }
    }
}