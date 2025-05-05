# worker/worker.py
import boto3
import json
import os
import whisper
import tempfile
import time
import logging
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROCESSING_QUEUE_URL = os.environ.get('PROCESSING_QUEUE_URL')
AUDIO_BUCKET_NAME = os.environ.get('AUDIO_BUCKET_NAME')
TRANSCRIPTION_TABLE = os.environ.get('TRANSCRIPTION_TABLE')
NOTES_TABLE = os.environ.get('NOTES_TABLE')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Initialize AWS clients with optional local endpoints
s3_client = boto3.client('s3', endpoint_url=os.environ.get('S3_ENDPOINT'))
sqs_client = boto3.client('sqs', endpoint_url=os.environ.get('SQS_ENDPOINT'))
dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('DYNAMODB_ENDPOINT'))

# Initialize DynamoDB tables
transcription_table = dynamodb.Table(TRANSCRIPTION_TABLE)
notes_table = dynamodb.Table(NOTES_TABLE)

# Initialize Whisper model
logger.info("Loading Whisper model...")
model = whisper.load_model("base")
logger.info("Whisper model loaded successfully.")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def process_message():
    """
    Process a single message from the SQS queue.
    Returns True if a message was processed, False otherwise.
    """
    try:
        # Receive message from SQS
        response = sqs_client.receive_message(
            QueueUrl=PROCESSING_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        
        # Check if there are any messages to process
        if 'Messages' not in response:
            logger.info("No messages to process")
            return False
        
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']
        
        try:
            # Parse message body
            body = json.loads(message['Body'])
            job_id = body['job_id']
            file_path = body['file_path']
            
            logger.info(f"Processing job {job_id}, file {file_path}")
            
            # Update job status in DynamoDB
            try:
                transcription_table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression="set job_status = :s",
                    ExpressionAttributeValues={':s': 'downloading'}
                )
            except Exception as e:
                logger.warning(f"Failed to update DynamoDB: {e}")
            
            # Download file from S3 to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                try:
                    logger.info(f"Downloading file from S3: {file_path}")
                    s3_client.download_file(AUDIO_BUCKET_NAME, file_path, temp_file.name)
                    
                    # Update job status in DynamoDB
                    try:
                        transcription_table.update_item(
                            Key={'job_id': job_id},
                            UpdateExpression="set job_status = :s",
                            ExpressionAttributeValues={':s': 'transcribing'}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update DynamoDB: {e}")
                    
                    # Transcribe audio file
                    logger.info(f"Transcribing file: {temp_file.name}")
                    result = model.transcribe(temp_file.name, beam_size=5, best_of=5)
                    transcription = result["text"]
                    
                    logger.info(f"Transcription complete for job {job_id}")
                    
                    # Store transcription in DynamoDB
                    try:
                        transcription_table.update_item(
                            Key={'job_id': job_id},
                            UpdateExpression="set transcription = :t, job_status = :s",
                            ExpressionAttributeValues={
                                ':t': transcription,
                                ':s': 'generating_note'
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update DynamoDB: {e}")
                    
                    # Generate diary note
                    logger.info(f"Generating diary note for job {job_id}")
                    diary_note = generate_personal_diary(transcription, OPENAI_API_KEY)
                    
                    # Store diary note in DynamoDB
                    try:
                        notes_table.put_item(
                            Item={
                                'job_id': job_id,
                                'diary_note': diary_note,
                                'created_at': int(time.time())
                            }
                        )
                        
                        # Update job status to completed
                        transcription_table.update_item(
                            Key={'job_id': job_id},
                            UpdateExpression="set job_status = :s",
                            ExpressionAttributeValues={':s': 'completed'}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update DynamoDB: {e}")
                    
                    logger.info(f"Processing complete for job {job_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}")
                    # Update job status to error
                    try:
                        transcription_table.update_item(
                            Key={'job_id': job_id},
                            UpdateExpression="set job_status = :s, error = :e",
                            ExpressionAttributeValues={
                                ':s': 'error',
                                ':e': str(e)
                            }
                        )
                    except Exception as db_err:
                        logger.warning(f"Failed to update DynamoDB with error status: {db_err}")
                finally:
                    # Delete temporary file
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary file: {e}")
            
            # Delete message from queue
            sqs_client.delete_message(
                QueueUrl=PROCESSING_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message body: {e}")
            # Move message to DLQ by not deleting it and letting visibility timeout expire
            # In production, you'd use a proper DLQ
            return False
        
    except Exception as e:
        logger.error(f"Error receiving message: {str(e)}")
        return False

def generate_personal_diary(transcription: str, openai_api_key: str, model: str = "gpt-3.5-turbo") -> str:
    """
    Converts a transcription string into a structured personal diary journaling note using OpenAI's LLM.
    """
    try:
        # Create a simple but effective prompt
        prompt = (
            "Convert the following transcription into a structured personal diary journaling note. "
            "Include clear sections such as Date, Mood, Key Events, and Reflections. "
            "Ensure the note feels personal and reflective.\n\n"
            f"Transcription:\n{transcription}"
        )
        
        # Call the OpenAI ChatCompletion endpoint
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an assistant that helps convert plain text into a structured personal diary entry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500,
        )
        
        # Extract and return the resulting structured note
        diary_note = response.choices[0].message.content.strip()
        return diary_note
    except Exception as e:
        logger.error(f"Error generating diary note: {str(e)}")
        return f"Error generating diary note: {str(e)}"

def main():
    """
    Main function to continuously process messages from the queue.
    """
    logger.info("Worker service started")
    
    while True:
        try:
            if not process_message():
                # If no message was processed, sleep briefly to avoid tight polling
                time.sleep(1)
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}")
            time.sleep(5)  # Sleep longer on unexpected errors

if __name__ == "__main__":
    main()