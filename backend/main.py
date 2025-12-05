from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import os
import httpx
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google_auth_oauthlib.flow import InstalledAppFlow
from starlette.responses import RedirectResponse
from googleapiclient.discovery import build

load_dotenv()

app = FastAPI(title="AI Email Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Global variable to store Gmail service
gmail_service = None

class EmailData(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    reply: Optional[str] = None

class SendEmailRequest(BaseModel):
    email_id: str
    reply_text: str

class EditDraftRequest(BaseModel):
    email_id: str
    draft_reply: str

def get_gmail_service():
    """Authenticate and return Gmail service"""
    global gmail_service
    
    if gmail_service:
        return gmail_service
    
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Falling back to requiring an explicit OAuth flow via /authenticate
            raise Exception("No valid credentials. Call /authenticate to start OAuth flow.")
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    gmail_service = build('gmail', 'v1', credentials=creds)
    return gmail_service

def extract_email_body(payload):
    """Extract email body from message payload"""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        data = payload['body'].get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8')
    return ""

async def generate_reply(sender, subject, body):
    """Generate AI reply using Groq"""
    if not GROQ_API_KEY:
        return "Error: Groq API key not configured"
    
    prompt = f"""You are a professional email assistant. Generate a polite, helpful reply to this email.

From: {sender}
Subject: {subject}
Body: {body}

Generate a professional reply that:
- Addresses the sender's concerns
- Is concise and clear
- Has a friendly but professional tone
- Includes a proper greeting and closing

Reply:"""

    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error generating reply: {e}")
    
    return "Error generating reply"

@app.get("/")
async def root():
    return {
        "message": "AI Email Agent API",
        "status": "active",
        "groq_configured": bool(GROQ_API_KEY)
    }

@app.post("/authenticate")
async def authenticate():
    """Start OAuth flow. If already authenticated, return status; otherwise return auth URL."""
    try:
        # If tokens exist and valid, return authenticated status
        if os.path.exists('token.json'):
            try:
                service = get_gmail_service()
                profile = service.users().getProfile(userId='me').execute()
                return {"status": "authenticated", "email": profile.get('emailAddress')}
            except Exception:
                # fall through to generate auth url
                pass

        # Create an OAuth flow and return auth URL. Frontend should navigate to this URL.
        flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES, redirect_uri='http://localhost:8000/oauth2callback')
        auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        return {"status": "needs_auth", "auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/oauth2callback')
async def oauth2callback(request):
    """OAuth2 callback to complete the flow and save credentials, then redirect back to frontend."""
    try:
        # Build flow with same redirect URI
        state = request.query_params.get('state')
        flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES, state=state, redirect_uri='http://localhost:8000/oauth2callback')
        # Exchange the authorization response for credentials
        authorization_response = str(request.url)
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

        # Redirect back to frontend app; include a query flag
        return RedirectResponse(url='http://localhost:3000/?auth=success')
    except Exception as e:
        return RedirectResponse(url=f'http://localhost:3000/?auth=error&detail={str(e)}')

@app.get("/emails/unread")
async def get_unread_emails():
    """✅ Feature 1: Read all unread emails"""
    try:
        service = get_gmail_service()
        
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {"emails": [], "message": "No unread emails"}
        
        emails = []
        for msg in messages:
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            
            body = extract_email_body(message['payload'])
            
            # ✅ Feature 2: AI generates replies using Groq
            reply = await generate_reply(sender, subject, body[:500])
            
            emails.append({
                "id": msg['id'],
                "sender": sender,
                "subject": subject,
                "body": body[:500],
                "reply": reply,
                "status": "pending_approval"
            })
        
        return {
            "emails": emails,
            "total": len(emails),
            "message": "✅ Unread emails with AI-generated drafts ready for approval"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/drafts")
async def get_email_drafts():
    """✅ Feature 3: Show you the drafts (all pending approval)"""
    try:
        service = get_gmail_service()
        
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {"drafts": [], "message": "No drafts pending approval"}
        
        drafts = []
        for msg in messages:
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            
            body = extract_email_body(message['payload'])
            reply = await generate_reply(sender, subject, body[:500])
            
            drafts.append({
                "id": msg['id'],
                "sender": sender,
                "subject": subject,
                "original_email": body[:500],
                "draft_reply": reply,
                "status": "pending_approval"
            })
        
        return {
            "drafts": drafts,
            "total": len(drafts),
            "message": "📝 Review these drafts before sending"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emails/edit-draft")
async def edit_draft(request: EditDraftRequest):
    """Edit AI-generated draft before approval"""
    try:
        return {
            "status": "draft_updated",
            "email_id": request.email_id,
            "draft_reply": request.draft_reply,
            "message": "✏️ Draft updated. Ready to approve and send"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emails/send")
async def send_email(request: SendEmailRequest):
    """✅ Feature 4: You approve before sending"""
    try:
        service = get_gmail_service()
        
        # Get original message
        original = service.users().messages().get(
            userId='me',
            id=request.email_id,
            format='full'
        ).execute()
        
        headers = original['payload']['headers']
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        
        # Create reply
        message = MIMEText(request.reply_text)
        message['to'] = sender
        message['subject'] = f"Re: {subject}"
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send email
        service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': original['threadId']}
        ).execute()
        
        # Mark as read
        service.users().messages().modify(
            userId='me',
            id=request.email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return {
            "status": "sent",
            "message": "✅ Email sent successfully",
            "to": sender,
            "subject": f"Re: {subject}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)