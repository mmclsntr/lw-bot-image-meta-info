import json

import hashlib
import hmac
from base64 import b64encode, b64decode

import jwt
from datetime import datetime
import urllib
import requests


def validate_request(body, signature, client_id):
    """LINE WORKS リクエスト検証"""
    # API IDを秘密鍵に利用
    secretKey = client_id.encode()
    payload = body

    # HMAC-SHA256 アルゴリズムでエンコード
    encoded_body = hmac.new(secretKey, payload, hashlib.sha256).digest()
    # BASE64 エンコード
    encoded_b64_body = b64encode(encoded_body).decode()

    # 比較
    return encoded_b64_body == signature


def get_jwt(client_id, service_account_id, privatekey):
    """アクセストークンのためのJWT取得"""
    current_time = datetime.now().timestamp()
    iss = client_id
    sub = service_account_id
    iat = current_time
    exp = current_time + (60 * 60) # 1時間

    jwstoken = jwt.encode(
        {
            "iss": iss,
            "sub": sub,
            "iat": iat,
            "exp": exp
        }, privatekey, algorithm="RS256")

    return jwstoken


def get_access_token(client_id, client_secret, scope, jwttoken):
    """アクセストークン取得"""
    url = 'https://auth.worksmobile.com/oauth2/v2.0/token'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    params = {
        "assertion": jwttoken,
        "grant_type": urllib.parse.quote("urn:ietf:params:oauth:grant-type:jwt-bearer"),
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
    }

    form_data = params

    r = requests.post(url=url, data=form_data, headers=headers)

    body = json.loads(r.text)

    return body


def refresh_access_token(client_id, client_secret, refresh_token):
    """アクセストークン更新"""
    url = 'https://auth.worksmobile.com/oauth2/v2.0/token'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    params = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    form_data = params

    r = requests.post(url=url, data=form_data, headers=headers)

    body = json.loads(r.text)

    return body


def send_message(content, bot_id, user_id, access_token):
    """メッセージ送信"""
    url = "https://www.worksapis.com/v1.0/bots/{}/users/{}/messages".format(bot_id, user_id)

    headers = {
          'Content-Type' : 'application/json',
          'Authorization' : "Bearer {}".format(access_token)
        }

    params = content
    form_data = json.dumps(params)

    r = requests.post(url=url, data=form_data, headers=headers)

    r.raise_for_status()


def get_attachments(bot_id, file_id, access_token):
    """コンテンツダウンロード"""
    url = "https://www.worksapis.com/v1.0/bots/{}/attachments/{}".format(bot_id, file_id)

    headers = {
          'Authorization' : "Bearer {}".format(access_token)
        }

    r = requests.get(url=url, headers=headers)

    r.raise_for_status()

    return r.content


def post_attachments(file_name, bot_id, access_token):
    url = "https://www.worksapis.com/v1.0/bots/{}/attachments".format(bot_id)

    headers = {
          'Content-Type' : 'application/json',
          'Authorization' : "Bearer {}".format(access_token)
        }

    params = {
        "fileName": file_name
    }
    form_data = json.dumps(params)

    r = requests.post(url=url, data=form_data, headers=headers)

    r.raise_for_status()

    return r.json()


def upload_file(url, file_data, access_token):
    headers = {
        'Authorization' : "Bearer {}".format(access_token),
    }

    file = {
        'FileData': file_data,
    }

    r = requests.post(url=url, files=file, headers=headers, timeout=180)

    r.raise_for_status()

    return r.json()
