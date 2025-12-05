# AI Email Generator Agent

A modern, full-stack email management tool that uses AI (Groq) to generate draft replies to your Gmail inbox. Review, edit, and approve each reply before sending — you always remain in control.

## Features

✅ **Gmail Integration** — Authenticate via OAuth2 and fetch unread emails from your inbox  
✅ **AI-Powered Drafts** — Generate professional email replies using Groq's LLaMA model  
✅ **Draft Review & Edit** — View, modify, or regenerate drafts before approval  
✅ **User-Controlled Sending** — Explicit approval required before any email is sent  
✅ **Modern UI** — Clean, responsive Next.js frontend with dark mode support  
✅ **Search & Filter** — Find emails by sender or subject  
✅ **Non-Destructive Regenerate** — See live draft updates with visual feedback  

## Tech Stack

**Backend**
- FastAPI (Python)
- Google Gmail API (OAuth2, message read/send)
- Groq API (LLaMA 3.3 70B for AI replies)
- CORS-enabled for local frontend development

**Frontend**
- Next.js 16 (App Router, TypeScript)
- React 19
- Tailwind CSS
- Modern card-based UI with smooth interactions

## Project Structure

```
email agent/
├── backend/
│   └── main.py              # FastAPI server, Gmail & Groq integration
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Root page, auth check
│   │   ├── layout.tsx       # Layout wrapper
│   │   ├── globals.css      # Global styles, design tokens
│   │   └── components/
│   │       ├── Auth.tsx     # OAuth login screen
│   │       ├── Dashboard.tsx # Main app shell (sidebar, nav)
│   │       ├── EmailList.tsx # Inbox email list & preview
│   │       └── DraftViewer.tsx # Draft review & send interface
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
├── .gitignore
└── README.md
```

## Setup

### Prerequisites

- Python 3.8+
- Node.js 18+
- Gmail account with [Google OAuth credentials](https://console.cloud.google.com/)
- [Groq API key](https://console.groq.com/)

### 1. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project named "Email Agent"
3. Enable Gmail API
4. Create an OAuth 2.0 Desktop Application credential
5. Download the JSON and save as `backend/credentials.json`

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn python-dotenv google-auth-oauthlib google-auth-httplib2 google-api-python-client httpx pydantic

# Create .env file with your Groq API key
echo GROQ_API_KEY=your_groq_api_key_here > .env

# Run the server
uvicorn main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Usage

1. **Start both servers** (see Setup above)
2. **Open** `http://localhost:3000` in your browser
3. **Click "Connect Gmail"** to authenticate with your Gmail account
   - You'll be redirected to Google's OAuth consent screen
   - After consent, you'll be redirected back to the app
4. **View your unread emails** in the Inbox tab
5. **Select an email** to see the AI-generated draft reply
6. **Edit, regenerate, or approve** the draft
7. **Click "Approve & Send"** to send the reply
   - The original email will be marked as read

## API Endpoints

### Authentication
- `POST /authenticate` — Start OAuth flow or check auth status
  - Response: `{ status: "authenticated", email }` or `{ status: "needs_auth", auth_url }`
- `GET /oauth2callback?code=...&state=...` — OAuth callback (handles token exchange)

### Emails
- `GET /emails/unread` — Fetch unread emails with AI-generated draft replies
- `GET /emails/drafts` — List all pending draft replies
- `POST /emails/edit-draft` — Update a draft reply before sending
- `POST /emails/send` — Send an approved reply and mark original as read

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
GROQ_API_KEY=your_groq_api_key_here
```

**Do not commit `.env` or `credentials.json` to version control.**

## Troubleshooting

### 500 Error on Frontend Load
- Ensure backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify `.env` file exists in `backend/` with a valid `GROQ_API_KEY`

### "Not authenticated" after clicking Connect Gmail
- Check that `token.json` was created in the `backend/` directory after OAuth flow
- Try logging out and reconnecting

### Gmail API returns permission errors
- Ensure your OAuth credentials have the `gmail.modify` scope
- For sensitive operations, the app must be approved or you must add your Gmail account as a test user in Google Cloud Console

### Frontend won't start
- Clear `.next/` directory: `rm -r frontend/.next`
- Reinstall dependencies: `npm install` in `frontend/`
- Ensure Node.js 18+ is installed

## Development Notes

- The frontend uses Next.js App Router with client components for state management
- OAuth callback redirects to `http://localhost:3000/?auth=success` after token exchange
- Drafts are stored in-memory; to persist them, implement a database (Supabase, Firebase, etc.)
- AI replies are generated fresh on each request; consider caching for performance

## Future Enhancements

- [ ] Persist drafts to a database
- [ ] Support for multiple Gmail accounts
- [ ] Custom AI prompt templates
- [ ] Email scheduling
- [ ] Attachment support
- [ ] Analytics dashboard

## License

MIT

## Author

Built by legacyttb using Next.js, FastAPI, and Groq
