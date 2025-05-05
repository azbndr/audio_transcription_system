# api/app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os
import uuid
import json
from typing import Optional

app = FastAPI(title="Audio Transcription API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
AUDIO_BUCKET_NAME = os.environ.get("AUDIO_BUCKET_NAME", "audio-files")
PROCESSING_QUEUE_URL = os.environ.get("PROCESSING_QUEUE_URL")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT")
SQS_ENDPOINT = os.environ.get("SQS_ENDPOINT")
DYNAMODB_ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT")

# Initialize AWS clients with optional local endpoints
s3_client = boto3.client('s3', endpoint_url=S3_ENDPOINT)
sqs_client = boto3.client('sqs', endpoint_url=SQS_ENDPOINT)
dynamodb = boto3.resource('dynamodb', endpoint_url=DYNAMODB_ENDPOINT)

# DynamoDB tables
try:
    transcription_table = dynamodb.Table('AudioTranscriptions')
    notes_table = dynamodb.Table('DiaryNotes')
except Exception as e:
    print(f"Warning: DynamoDB tables not available: {e}")

@app.get("/")
async def root():
    return {"message": "Audio Transcription API is running"}

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile):
    """
    Upload an audio file for transcription and note generation.
    """
    try:
        # Generate unique ID for this job
        job_id = str(uuid.uuid4())
        
        # Create S3 file path
        file_path = f"uploads/{job_id}/{file.filename}"
        
        # Upload file to S3
        s3_client.upload_fileobj(
            file.file, 
            AUDIO_BUCKET_NAME, 
            file_path
        )
        
        # Initialize job status in DynamoDB
        try:
            transcription_table.put_item(
                Item={
                    'job_id': job_id,
                    'file_name': file.filename,
                    'file_path': file_path,
                    'job_status': 'queued'
                }
            )
        except Exception as e:
            print(f"Warning: Could not write to DynamoDB: {e}")
        
        # Send message to SQS for processing
        sqs_client.send_message(
            QueueUrl=PROCESSING_QUEUE_URL,
            MessageBody=json.dumps({
                'job_id': job_id,
                'file_path': file_path,
                'file_name': file.filename
            })
        )
        
        return {"job_id": job_id, "status": "queued"}
    
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def check_status(job_id: str):
    """
    Check the status of a transcription job.
    """
    try:
        response = transcription_table.get_item(
            Key={'job_id': job_id}
        )
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job_id,
            "status": response['Item'].get('job_status', 'unknown'),
            "file_name": response['Item'].get('file_name', '')
        }
    
    except Exception as e:
        if str(e).startswith("An error occurred (ResourceNotFoundException)"):
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    """
    Get the results of a completed transcription and note generation job.
    """
    try:
        # First check job status
        status_response = transcription_table.get_item(
            Key={'job_id': job_id}
        )
        
        if 'Item' not in status_response:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if status_response['Item'].get('job_status') != 'completed':
            return {
                "job_id": job_id,
                "status": status_response['Item'].get('job_status', 'unknown'),
                "message": "Processing not yet complete"
            }
        
        # Get diary note
        note_response = notes_table.get_item(
            Key={'job_id': job_id}
        )
        
        if 'Item' not in note_response:
            return {
                "job_id": job_id,
                "status": "completed",
                "transcription": status_response['Item'].get('transcription', ''),
                "message": "Note generation pending"
            }
        
        return {
            "job_id": job_id,
            "status": "completed",
            "transcription": status_response['Item'].get('transcription', ''),
            "diary_note": note_response['Item'].get('diary_note', '')
        }
    
    except Exception as e:
        if str(e).startswith("An error occurred (ResourceNotFoundException)"):
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    API_HOST = os.environ.get("API_HOST")
    API_PORT = os.environ.get("API_PORT")
    
    uvicorn.run("app:app", host=API_HOST, port=API_PORT, reload=True)