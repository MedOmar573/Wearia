import os
import urllib.request
import json
import mimetypes
import uuid

def test_classify():
    # 1. Login to get token
    login_url = "http://127.0.0.1:8000/auth/login"
    payload = json.dumps({"email": "benhamdaomar21@gmail.com", "password": "04508468"}).encode("utf-8")
    req = urllib.request.Request(login_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read().decode())["access_token"]
    print("Login OK")

    # 2. Test classify with multipart form
    classify_url = "http://127.0.0.1:8000/ai/classify"
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    
    imgs_to_test = [
        "4f7fa19c-4042-47ff-8b0e-f70994641311.jpg",
        "chemise_oxford_blanche.jpg",
        "baskets_blanches.jpg",
        "pantalon_noir.jpg",
        "jean_slim_bleu.jpg"
    ]

    for fname in imgs_to_test:
        test_file_path = f"c:\\Users\\DELL\\Desktop\\L3DSI\\projet\\Wearia\\wearia_backend\\uploads\\{fname}"
        if not os.path.exists(test_file_path):
            continue

        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
        with open(test_file_path, "rb") as f:
            file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            classify_url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            },
            method="POST"
        )

        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode())
            print(f"[{fname}] -> Cat: {res.get('category')} (TypeID: {res.get('suggested_type_id')}) | Col: {res.get('color')} (ColID: {res.get('suggested_color_id')}) | Mat: {res.get('matiere')} | Sais: {res.get('saison')}")


if __name__ == "__main__":
    test_classify()
