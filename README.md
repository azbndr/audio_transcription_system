# Scalable Audio Transcription and Note Generation System

This project implements a scalable system for processing audio files, transcribing them using Whisper, and generating structured personal diary notes from the transcriptions using OpenAI's LLM.

## 🔉 Audio Transcription System
A scalable cloud-based solution for transcribing audio files using OpenAI Whisper, deployed with FastAPI (API service) and Celery (worker queues). Features:

1. **End-to-End Pipeline**: Upload → Transcribe → Store
2. **Infrastructure**: Dockerized microservices (API + Workers)
3. **Cloud-Ready**: Integrates with AWS S3/SQS (LocalStack for dev)
4. **Load Test Included**: Simulate high-volume requests

**Tech Stack**: Python, FastAPI, OpenAI Whisper, Docker, AWS (S3/SQS), LocalStack


## System Features

- **High Throughput**: Designed to process 10,000 hours of audio per hour
- **Scalable Architecture**: Leverages serverless components and auto-scaling
- **Resilient Design**: Handles variable load and includes error recovery mechanisms
- **Cost-Effective**: Optimizes resource usage based on demand

## Architecture Overview

The system follows a microservice-based architecture with the following components:

1. **API Service**: Handles file uploads and result retrieval
2. **Worker Service**: Processes transcription and note generation tasks
3. **Storage Components**: AWS S3 for audio files, DynamoDB for metadata and results
4. **Queue System**: AWS SQS for task distribution and load balancing

## Getting Started

### Prerequisites

- Docker and Docker Compose
- OpenAI API Key
- Sample audio file/s for testing

### Environment Setup

1. Clone this repository
   ```bash
   git clone https://github.com/azbndr/audio_transcription_system.git
   ```
2. Create `.env` file from the `.env.template` file


### Running Locally

1. Start the services:
   ```bash
   docker-compose up -d
   ```

2. The API service will be available at `http://localhost:8000`

3. Use the following endpoints:
   - `POST /upload-audio/`: Upload an audio file for processing
   - `GET /status/{job_id}`: Check the status of a processing job
   - `GET /result/{job_id}`: Get the results of a completed job

### Testing

You can use the included load testing script to test the system:

```bash
# Install dependencies
pip install requests

# Run the load test
python ./tests/load_test.py --requests 10 --workers 5 --monitor
```

## Production Deployment Considerations

For deploying to a production environment, additional considerations include:

### Scaling
- Use AWS ECS with auto-scaling for workers
- Configure SQS with appropriate visibility timeouts
- Scale DynamoDB read/write capacity units as needed

### Security
- Implement proper IAM roles and permissions
- Secure API endpoints with authentication
- Encrypt data at rest and in transit

### Monitoring
- Set up CloudWatch alarms for key metrics
- Implement detailed logging and tracing
- Create dashboards for system visibility

### Cost Optimization
- Use Spot Instances for non-critical workloads
- Implement automatic scaling down during low-demand periods
- Transition to infrequent access storage tiers for older files

## Directory Structure

```
├── api/                    # API service files
│   ├── app.py              # FastAPI application
│   ├── Dockerfile          # API service Dockerfile
│   └── requirements.txt    # API dependencies
├── worker/                 # Worker service files
│   ├── worker.py           # Worker implementation
│   ├── Dockerfile          # Worker service Dockerfile
│   └── requirements.txt    # Worker dependencies
├── localstack/             # LocalStack initialization scripts
│   └── init-aws.sh         # AWS resource initialization
├── test_sample/            # Sample data 
|   └── sample.mp3          # Sample audio to be used in the stress test
├── tests/                  # Tests
|   └── load_test.py        # Load testing script
├── .env                    # Environment varibles file     
├── docker-compose.yaml     # Local development setup
└── README.md               # This file 
```
