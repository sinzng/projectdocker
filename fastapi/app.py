from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware  # CORSMiddleware 임포트
from fastapi import File, UploadFile, Form
from pydantic import BaseModel
import aiohttp
import boto3
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError, PartialCredentialsError
import os
from dotenv import load_dotenv
import uvicorn
import json
from datetime import datetime
from openai import OpenAI
import shutil
from time import sleep  # 추가
import requests



app = FastAPI()
# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OpenAI.api_key = os.getenv("OPENAI_API_KEY")

# client = OpenAI(api_key=OpenAI.api_key)
# train_data_file= client.files.create(
#     file=Path("train_data.jsonl"),
#     purpose = "fine-tune"
# )
# validation_data_file = client.files.create(
#     file = Path("validation_data.jsonl"),
#     purpose = "fine-tune"
# )

# def fine_tune(train_file_id, validation_file_id):

BUCKET_NAME = 'kibwa07'
PREFIX1 = 'dailychat/'
PREFIX2 = 'summarziedchat/'
def savechat_s3(message: str, response: str, prefix=PREFIX1):
    try:
        # S3 클라이언트 생성
        s3 = boto3.client('s3')
        
        # 대화 내용을 JSON 형식으로 저장
        chat_log = {
            "message": message, 
            "response": response, 
            "timestamp": str(datetime.now())
        }
        conversation_start_time = datetime.now()
        # 파일 이름에 대화 시작 날짜를 포함하여 생성
        file_name = f"chat_log_{conversation_start_time.strftime('%Y-%m-%d')}.json"
        
        # S3의 지정된 폴더(PREFIX)에 파일 저장
        chat_filepath = prefix + file_name
        # 기존 파일에서 내용을 읽어옴
        try:
            existing_content = s3.get_object(Bucket=BUCKET_NAME, Key=chat_filepath)['Body'].read().decode('utf-8')
            chat_history = json.loads(existing_content)
            if not isinstance(chat_history, list):
                chat_history = [chat_history]
        except s3.exceptions.NoSuchKey:
            chat_history = []
        # 새로운 대화를 기존 기록에 추가
        chat_history.append(chat_log)
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=chat_filepath,
            Body=json.dumps(chat_history, ensure_ascii=False, indent=4),
            ContentType='application/json'
        )
        print(f"데이터가 {BUCKET_NAME} 버킷의 {chat_filepath}에 성공적으로 저장되었습니다.")
    except (NoCredentialsError, PartialCredentialsError):
        print("에러: AWS 자격 증명을 찾을 수 없습니다.")
    except Exception as e:
        print(f"에러: {str(e)}")

def saveSummaryS3(message: str, response: str, file_name: str, prefix=PREFIX2):
    try:
        # S3 클라이언트 생성
        s3 = boto3.client('s3')
        
        # 대화 내용을 JSON 형식으로 저장
        chat_log = {
            "message": message, 
            "response": response, 
            "timestamp": str(datetime.now())
        }
        
        # 새로운 파일에 대화 내용 저장
        
        chat_filepath = prefix + file_name
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=chat_filepath,
            Body=json.dumps([chat_log], ensure_ascii=False, indent=4),
            ContentType='application/json'
        )
        print(f"데이터가 {BUCKET_NAME} 버킷의 {chat_filepath}에 성공적으로 저장되었습니다.")
    except (NoCredentialsError, PartialCredentialsError):
        print("에러: AWS 자격 증명을 찾을 수 없습니다.")
    except Exception as e:
        print(f"에러: {str(e)}") 

class ChatRequest(BaseModel):
    message: str
# OpenAI API 호출 함수
async def fetch_ai_response(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    api_endpoint = 'https://api.openai.com/v1/chat/completions'

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 1024,
        "top_p": 1,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.5,
        "stop": ["Human"]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(api_endpoint, json=payload, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"HTTP error! status: {response.status}")
            data = await response.json()
            if not data.get("choices"):
                raise Exception("API response is empty")
            return data["choices"][0]["message"]["content"]

def summarizeChatFileFromS3(bucket_name, chat_filepath, max_tokens=1000):
    try:
        # S3 클라이언트 생성
        s3 = boto3.client('s3')

        # S3에서 파일 가져오기
        obj = s3.get_object(Bucket=bucket_name, Key=chat_filepath)
        dialogue_data = json.loads(obj['Body'].read().decode('utf-8'))

        # 시스템 지시사항 설정
        system_instruction = "\n".join(["Summarize the overall conversation flow concisely, capturing the main topic and key points discussed. Summarize the conversation in Korean."])

        # 메시지 구성
        messages = [{"role": "system", "content": system_instruction}]

        for item in dialogue_data:
            messages.append({"role": "user", "content": item["message"]})
            messages.append({"role": "assistant", "content": item["response"]})

        # OpenAI 클라이언트 생성 및 응답 요청
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0,
            max_tokens=1000
        )

        return response.choices[0].message.content.strip()
    except (NoCredentialsError, PartialCredentialsError):
        print("에러: AWS 자격 증명을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"에러: {str(e)}")
        return None


@app.get("/")
def read_root():
    return {"Hello" : "World"}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        ai_response = await fetch_ai_response(request.message)

        # 대화 내용과 API 응답을 로컬에 저장
        # savechat_local(request.message, ai_response)
        # s3에 저장
        savechat_s3(request.message, ai_response)

        return {"response": ai_response}
    except Exception as e:
        return {"error": str(e)}


@app.get("/getdialogsummary")
async def getSummary(file_path: str):
    try:
        summarized_text = summarizeChatFile(file_path)
        return {"summary": summarized_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summarizechat")
async def summarizeChat(file_name: str ):
    try:
        # S3 파일 경로 설정
        chat_filepath = PREFIX1 + file_name
        
        # S3에서 파일을 가져와 요약
        summary = summarizeChatFileFromS3(BUCKET_NAME, chat_filepath)
        
        if summary is not None:
            # PREFIX2로 저장하도록 savechat_s3 함수 호출
            saveSummaryS3(summary, "", file_name, prefix=PREFIX2)
            return {"summary": summary}
        else:
            return {"error": "파일을 요약하는 동안 오류가 발생했습니다."}
    except Exception as e:
        return {"error": str(e)}

@app.get("/getsummaryfroms3")
async def getSummaryFromS3(file_name:str):
    try:
        # S3 파일 경로 설정
        s3_filepath = PREFIX2 + file_name
        # S3에서 파일을 가져옴
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_filepath)
        file_content = response['Body'].read().decode('utf-8')
        
        # JSON으로 파싱하여 message 부분만 추출
        summary = json.loads(file_content)
        messages = [item['message'] for item in summary]
        
        return {"summary": messages}
    except Exception as e:
        return {"error": str(e)}

@app.get("/getchatfroms3")
async def getChatFromS3(file_name:str):
    try:
        # S3 파일 경로 설정
        s3_filepath = PREFIX1 + file_name
        # S3에서 파일을 가져옴
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_filepath)
        file_content = response['Body'].read().decode('utf-8')

        # JSON 파싱
        chat_data = json.loads(file_content)
        # 메시지와 응답을 교대로 가져와서 처리
        result = []
        for item in chat_data:
            result.append({"message": item['message'], "response": item['response']})
        return json.dumps({"chat": result}, ensure_ascii=False, indent=4)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=4)


s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')

class TranscriptionResponse(BaseModel):
    success: bool
    transcription: str = None
    error: str = None

@app.post("/upload/")
async def upload_file(file: UploadFile = UploadFile(...)):
    try:
        # 현재 시간을 기반으로 파일 이름 생성
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f'{current_time}_{file.filename}'
        
        s3_key = f'sound/{file_name}' 
        # 클라이언트에서 업로드된 파일을 임시 디렉토리에 저장
        with open(f'/tmp/{file_name}', "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # 임시 디렉토리에 저장된 파일을 S3에 업로드
        s3_client.upload_file(f'/tmp/{file_name}', 'kibwa07', s3_key)

        # 업로드 완료 후 임시 파일 삭제
        os.remove(f'/tmp/{file_name}')

        # Transcribe 작업 시작
        transcribe_job_name = f"transcribe_{current_time}"
        transcribe_client.start_transcription_job(
            TranscriptionJobName=transcribe_job_name,
            Media={'MediaFileUri': f's3://kibwa07/{s3_key}'},
            MediaFormat='wav',  # 음성 파일 포맷에 따라 변경
            LanguageCode='ko-KR'  # 한국어 코드로 변경
        )

        # Transcribe 작업 완료 대기
        while True:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=transcribe_job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            sleep(10)

        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            transcript_response = requests.get(transcript_uri)
            transcript_text = transcript_response.json()['results']['transcripts'][0]['transcript']
            return {"success": True, "transcription": transcript_text}
        else:
            raise HTTPException(status_code=500, detail="Transcription job failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)