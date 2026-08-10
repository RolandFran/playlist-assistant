"""One-time local Spotify login; it never prints or stores a token in clear text."""
from __future__ import annotations
import argparse, base64, hashlib, json, secrets, sys, threading, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from spotify_pairing import encrypt_import, validate_pairing_document

LOOPBACK_HOST = '127.0.0.1'
LOOPBACK_PORT = 8888
LOOPBACK_REDIRECT = 'http://127.0.0.1:8888/callback'

def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode('ascii').rstrip('=')

def validate_callback(path: str, expected_state: str) -> str:
    parsed=urllib.parse.urlsplit(path)
    if parsed.path!='/callback': raise ValueError('Unexpected callback path.')
    values=urllib.parse.parse_qs(parsed.query, strict_parsing=True)
    if values.get('state',[None])[0]!=expected_state: raise ValueError('The callback could not be verified.')
    if values.get('error'): raise RuntimeError('Spotify login was cancelled or denied.')
    code=values.get('code',[None])[0]
    if not code: raise ValueError('Spotify did not return an authorization code.')
    return code

def exchange_code(pairing, code, redirect_uri, verifier):
    data=urllib.parse.urlencode({'grant_type':'authorization_code','code':code,'redirect_uri':redirect_uri,'client_id':pairing['spotify_client_id'],'code_verifier':verifier}).encode()
    request=urllib.request.Request('https://accounts.spotify.com/api/token',data=data,headers={'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=20) as response: result=json.loads(response.read())
    except Exception as error: raise RuntimeError('Spotify could not complete the login.') from error
    token=result.get('refresh_token') if isinstance(result,dict) else None
    if not isinstance(token,str) or not token: raise RuntimeError('Spotify did not provide a refresh token.')
    return token, result.get('scope') if isinstance(result.get('scope'),str) else None

def create_listener(handler):
    try: return ThreadingHTTPServer((LOOPBACK_HOST, LOOPBACK_PORT), handler)
    except OSError as error: raise RuntimeError('Port 8888 on 127.0.0.1 is unavailable. Close the application using it and try again.') from error

def authorization_url(pairing, state, verifier):
    query=urllib.parse.urlencode({'response_type':'code','client_id':pairing['spotify_client_id'],'redirect_uri':LOOPBACK_REDIRECT,'scope':pairing['spotify_scopes'],'state':state,'code_challenge_method':'S256','code_challenge':pkce_challenge(verifier)})
    return 'https://accounts.spotify.com/authorize?'+query

def run(pairing_path: Path, output_path: Path, timeout: int=300):
    try: pairing=validate_pairing_document(json.loads(pairing_path.read_text(encoding='utf-8')))
    except (OSError,json.JSONDecodeError,ValueError) as error: raise ValueError('The pairing file is invalid or expired.') from error
    state=secrets.token_urlsafe(32); verifier=secrets.token_urlsafe(64); received={}; done=threading.Event()
    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            try: received['code']=validate_callback(self.path,state); body=b'<p>Spotify login completed. You may close this window.</p>'
            except Exception as error: received['error']=error; body=b'<p>Spotify login failed. Return to the terminal.</p>'
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); done.set()
        def log_message(self,*_): pass
    server=create_listener(Callback); redirect=LOOPBACK_REDIRECT
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        if not webbrowser.open(authorization_url(pairing,state,verifier)): print('Open the Spotify authorization page in your browser.',file=sys.stderr)
        if not done.wait(timeout): raise RuntimeError('Spotify login timed out.')
        if 'error' in received: raise received['error']
        refresh,scopes=exchange_code(pairing,received['code'],redirect,verifier)
        output_path.write_text(json.dumps(encrypt_import(pairing,refresh,scopes),separators=(',',':'))+'\n',encoding='utf-8')
    finally: server.shutdown(); server.server_close(); thread.join(timeout=2)

def main():
    parser=argparse.ArgumentParser(description='Create an encrypted Playlist Assistant Spotify token import.')
    parser.add_argument('--pairing',required=True,type=Path); parser.add_argument('--output',type=Path,default=Path('spotify-token-import.json')); parser.add_argument('--timeout',type=int,default=300)
    args=parser.parse_args()
    try: run(args.pairing,args.output,args.timeout)
    except (ValueError,RuntimeError) as error: print(str(error),file=sys.stderr); raise SystemExit(1)
    print(f'Encrypted import file created: {args.output}')
if __name__=='__main__': main()
