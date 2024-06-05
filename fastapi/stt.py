from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.openapi.utils import get_openapi
from typing import List
import boto3
import requests
import os
import time
import uuid
import uvicorn

app = FastAPI()

transcribe_client = boto3.client('transcribe')
s3_client = boto3.client('s3')

@app.post('/transcribe')
async def transcribeAudio(file:UploadFile = File(...)):
    headers = {
        'Content-Type': 'audio/l16; rate=16000'
    }

    response = transcribe_client.start_stream_transcription(
        Language= 'ko-KR', 
        MediaSampleRateHertz=16000,
        MediaFormat = 'pcm',
        AudioStream = io.BytesIO(await file.read())
    )
    transcription = ''
    while True:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=response['TranscriptionJob']['TranscriptionJobName'])
        if response['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(5)
    
        # Transcribe 결과를 가져와서 반환
    if response['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_url = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
        transcript_response = requests.get(transcript_url)
        transcript = transcript_response.json()
        transcription = transcript['results']['transcripts'][0]['transcript']

    return {'transcription': transcription}

