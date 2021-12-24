import os
import json
import uuid

from PIL import Image
import io

from requests.structures import CaseInsensitiveDict

from google.cloud import secretmanager

from fastapi import FastAPI, Request


import lw

app = FastAPI()


def get_secret_version(project_id, secret_id, version_id='latest'):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    parent = client.secret_path(project_id, secret_id)
    name = "{}/versions/{}".format(parent, version_id)

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Print the secret payload.
    payload = response.payload.data.decode("UTF-8")
    return payload


def put_secret_version(project_id, secret_id, payload):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    parent = client.secret_path(project_id, secret_id)

    encoded_payload = payload.encode("UTF-8")

    # Access the secret version.
    response = client.add_secret_version(
        request={"parent": parent, "payload": {"data": encoded_payload}}
    )

    return response


@app.post("/update_token")
async def update_token():
    gcp_project_id = os.environ.get("GCP_PROJECT_ID")

    client_id = get_secret_version(gcp_project_id, "lw-client-id")
    client_secret = get_secret_version(gcp_project_id, "lw-client-secret")
    refresh_token = get_secret_version(gcp_project_id, "lw-refresh-token")

    if refresh_token == "init":
        print("create access token")
        # AccessToken初回取得
        service_account_id = get_secret_version(gcp_project_id, "lw-service-account-id")
        privatekey = get_secret_version(gcp_project_id, "lw-privatekey")

        scope = "bot,bot.read"

        jwttoken = lw.get_jwt(client_id, service_account_id, privatekey)

        # Server token取得
        res = lw.get_access_token(client_id, client_secret, scope, jwttoken)
        access_token = res["access_token"]
        refresh_token = res["refresh_token"]

        # Refresh token追加
        put_secret_version(gcp_project_id, "lw-refresh-token", refresh_token)
    else:
        print("refresh access token")
        # AccessToken更新
        res = lw.refresh_access_token(client_id, client_secret, refresh_token)
        access_token = res["access_token"]

    # Access Token更新
    print("put access token")
    put_secret_version(gcp_project_id, "lw-access-token", access_token)

    return


@app.post("/chat")
async def chat(request: Request):
    body_raw = await request.body()
    body_json = await request.json()
    headers = CaseInsensitiveDict(request.headers)

    print(body_json)
    print(headers)

    bot_id = headers.get("x-works-botid")

    gcp_project_id = os.environ.get("GCP_PROJECT_ID")
    api_id = get_secret_version(gcp_project_id, "lw-api-id")
    access_token = get_secret_version(gcp_project_id, "lw-access-token")

    msg_type = body_json["type"]
    user_id = body_json["source"]["userId"]
    content = body_json["content"]

    chat_id = uuid.uuid4().hex
    if content["type"] == "image":
        file_id = content["fileId"]
        img_data = lw.get_attachments(bot_id, file_id, access_token)

        img = Image.open(io.BytesIO(img_data))

        msg = "Size: {}\nFormat: {}\nMode: {}\nInfo: {}".format(img.size, img.format, img.mode, img.info)

        res_content = {
            "content": {
                "type": "text",
                "text": msg
            }
        }

    else:
        res_content = {
            "content": {
                "type": "text",
                "text": "Please send an image."
            }
        }

    print(res_content)
    res = lw.send_message(res_content, bot_id, user_id, access_token)

    return {}

@app.get("/")
async def read_root():
    return {"Hello": "World"}
