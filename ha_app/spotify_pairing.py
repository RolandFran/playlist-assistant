"""Shared, versioned cryptography for the local Spotify token handoff."""
from __future__ import annotations
import base64, json, secrets
from datetime import UTC, datetime, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
PROTOCOL_VERSION=1; PAIRING_LIFETIME=timedelta(minutes=10); MAX_IMPORT_BYTES=64*1024; LOOPBACK_REDIRECT='http://127.0.0.1:8888/callback'
def _b64(v): return base64.urlsafe_b64encode(v).decode('ascii').rstrip('=')
def _unb64(v, length=None):
    if not isinstance(v,str) or not v or len(v)>1024: raise ValueError('Invalid encoded cryptographic value.')
    try: raw=base64.urlsafe_b64decode(v+'='*(-len(v)%4))
    except Exception as error: raise ValueError('Invalid encoded cryptographic value.') from error
    if length is not None and len(raw)!=length: raise ValueError('Invalid cryptographic value length.')
    return raw
def utc_now(): return datetime.now(UTC)
def encode_time(v): return v.astimezone(UTC).isoformat().replace('+00:00','Z')
def parse_time(v):
    if not isinstance(v,str): raise ValueError('Invalid expiry time.')
    try: result=datetime.fromisoformat(v.replace('Z','+00:00'))
    except ValueError as error: raise ValueError('Invalid expiry time.') from error
    if result.tzinfo is None: raise ValueError('Invalid expiry time.')
    return result.astimezone(UTC)
def derive_key(private, peer, secret, session):
    shared=private.exchange(X25519PublicKey.from_public_bytes(peer))
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=secret.encode(),info=('playlist-assistant/spotify-token/'+session).encode()).derive(shared)
class PairingSession:
    def __init__(self,client_id,scopes):
        self.session_id=secrets.token_urlsafe(32); self.transfer_secret=secrets.token_urlsafe(32); self.private_key=X25519PrivateKey.generate(); self.expires_at=utc_now()+PAIRING_LIFETIME; self.client_id=client_id; self.scopes=scopes
    @property
    def expired(self): return utc_now()>=self.expires_at
    def public_document(self):
        return {'version':PROTOCOL_VERSION,'session_id':self.session_id,'expires_at':encode_time(self.expires_at),'public_key':_b64(self.private_key.public_key().public_bytes_raw()),'transfer_secret':self.transfer_secret,'spotify_client_id':self.client_id,'spotify_scopes':self.scopes,'loopback_redirect':LOOPBACK_REDIRECT}
    def decrypt_import(self,document):
        if not isinstance(document,dict) or document.get('version')!=PROTOCOL_VERSION: raise ValueError('Unsupported token import format.')
        if not secrets.compare_digest(str(document.get('session_id','')),self.session_id): raise ValueError('The token import belongs to another pairing session.')
        if self.expired: raise ValueError('The pairing session has expired.')
        peer=_unb64(document.get('ephemeral_public_key'),32); nonce=_unb64(document.get('nonce'),12); ciphertext=_unb64(document.get('ciphertext'))
        if len(ciphertext)<17: raise ValueError('Invalid encrypted token import.')
        try: payload=json.loads(AESGCM(derive_key(self.private_key,peer,self.transfer_secret,self.session_id)).decrypt(nonce,ciphertext,f'{PROTOCOL_VERSION}:{self.session_id}'.encode()))
        except Exception as error: raise ValueError('The encrypted token import could not be verified.') from error
        if not isinstance(payload,dict) or not isinstance(payload.get('refresh_token'),str) or not payload['refresh_token']: raise ValueError('Invalid encrypted token import.')
        return payload
def validate_pairing_document(d):
    fields={'version','session_id','expires_at','public_key','transfer_secret','spotify_client_id','spotify_scopes','loopback_redirect'}
    if not isinstance(d,dict) or set(d)!=fields: raise ValueError('Invalid pairing file.')
    if d['version']!=PROTOCOL_VERSION or d['loopback_redirect']!=LOOPBACK_REDIRECT: raise ValueError('Unsupported pairing file.')
    if any(not isinstance(d[k],str) or not d[k] or len(d[k])>512 for k in ('session_id','transfer_secret','spotify_client_id','spotify_scopes')): raise ValueError('Invalid pairing file.')
    _unb64(d['public_key'],32)
    if parse_time(d['expires_at'])<=utc_now(): raise ValueError('The pairing file has expired.')
    return d
def encrypt_import(pairing,refresh_token,scopes=None):
    pairing=validate_pairing_document(pairing); ephemeral=X25519PrivateKey.generate(); nonce=secrets.token_bytes(12); payload={'refresh_token':refresh_token,'created_at':encode_time(utc_now())}
    if scopes: payload['scopes']=scopes
    ciphertext=AESGCM(derive_key(ephemeral,_unb64(pairing['public_key'],32),pairing['transfer_secret'],pairing['session_id'])).encrypt(nonce,json.dumps(payload,separators=(',',':')).encode(),f'{PROTOCOL_VERSION}:{pairing["session_id"]}'.encode())
    return {'version':PROTOCOL_VERSION,'session_id':pairing['session_id'],'ephemeral_public_key':_b64(ephemeral.public_key().public_bytes_raw()),'nonce':_b64(nonce),'ciphertext':_b64(ciphertext)}
