# ./tests/load_test.py
import requests
import os
import time
import random
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API endpoint
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Statistics
stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "upload_times": [],
    "start_time": None,
    "end_time": None
}

# Sample audio files for testing
SAMPLE_AUDIO_FILES = ["../test_sample/sample.mp3"]

def upload_audio(file_path):
    """Upload an audio file and return the job id"""
    try:
        start_time = time.time()
        
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            response = requests.post(f"{API_URL}/upload-audio/", files=files)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        if response.status_code == 200:
            job_id = response.json().get("job_id")
            stats["successful_requests"] += 1
            stats["upload_times"].append(elapsed)
            logger.info(f"File {file_path} uploaded successfully. Job ID: {job_id}, Time: {elapsed:.2f}s")
            return job_id
        else:
            stats["failed_requests"] += 1
            logger.error(f"Failed to upload {file_path}. Status code: {response.status_code}, Response: {response.text}")
            return None
    
    except Exception as e:
        stats["failed_requests"] += 1
        logger.error(f"Error uploading {file_path}: {str(e)}")
        return None

def check_job_status(job_id):
    """Check the status of a job"""
    try:
        response = requests.get(f"{API_URL}/status/{job_id}")
        if response.status_code == 200:
            return response.json().get("status")
        else:
            logger.error(f"Failed to check status for job {job_id}. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error checking status for job {job_id}: {str(e)}")
        return None

def monitor_job(job_id, timeout=300):
    """Monitor a job until completion or timeout"""
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            logger.warning(f"Job {job_id} timed out after {timeout} seconds")
            return False
        
        status = check_job_status(job_id)
        if status == "completed":
            logger.info(f"Job {job_id} completed successfully")
            return True
        elif status == "error":
            logger.error(f"Job {job_id} failed with error")
            return False
        
        time.sleep(5)  # Check every 5 seconds

def run_load_test(num_requests, max_workers, monitor=False):
    """Run a load test with the specified number of requests and workers"""
    logger.info(f"Starting load test with {num_requests} requests and {max_workers} workers")
    
    stats["start_time"] = time.time()
    stats["total_requests"] = num_requests
    
    sample_files = [random.choice(SAMPLE_AUDIO_FILES) for _ in range(num_requests)]
    job_ids = []
    
    # Upload files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for job_id in executor.map(upload_audio, sample_files):
            if job_id:
                job_ids.append(job_id)
    
    # Optionally monitor jobs until completion
    if monitor and job_ids:
        logger.info(f"Monitoring {len(job_ids)} jobs until completion")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(monitor_job, job_ids))
        
        completed = results.count(True)
        failed = results.count(False)
        logger.info(f"Jobs completed: {completed}, Jobs failed: {failed}")
    
    stats["end_time"] = time.time()
    
    # Calculate and print statistics
    total_time = stats["end_time"] - stats["start_time"]
    avg_upload_time = sum(stats["upload_times"]) / len(stats["upload_times"]) if stats["upload_times"] else 0
    
    logger.info("\n--- Load Test Results ---")
    logger.info(f"Total requests: {stats['total_requests']}")
    logger.info(f"Successful requests: {stats['successful_requests']}")
    logger.info(f"Failed requests: {stats['failed_requests']}")
    logger.info(f"Total time: {total_time:.2f} seconds")
    logger.info(f"Average upload time: {avg_upload_time:.2f} seconds")
    logger.info(f"Requests per second: {stats['successful_requests'] / total_time:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load test for audio transcription API')
    parser.add_argument('--requests', type=int, default=10, help='Number of requests to send')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent workers')
    parser.add_argument('--monitor', action='store_true', help='Monitor jobs until completion')
    
    args = parser.parse_args()
    
    run_load_test(args.requests, args.workers, args.monitor)