import urllib.request
import json

def test():
    # JSON Login
    url = 'http://127.0.0.1:8000/auth/login'
    payload = json.dumps({'email': 'benhamdaomar21@gmail.com', 'password': '04508468'}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')

    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        token = res.get('access_token')
        print('LOGIN SUCCESSFUL! Token:', token[:25] + '...')

    # POST /recommendations
    rec_url = 'http://127.0.0.1:8000/recommendations'
    rec_payload = json.dumps({}).encode('utf-8')
    req = urllib.request.Request(rec_url, data=rec_payload, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req) as resp:
        rec = json.loads(resp.read().decode())
        print('\nGENERATE RECOMMENDATION RESULT:')
        print('Outfit ID:', rec.get('outfit_id'))
        print('Score:', rec.get('compatibility_score'))
        print('Occasion:', rec.get('occasion'))
        print('Weather:', rec.get('weather'), rec.get('temperature'))
        print('Explanation:', rec.get('explanation'))
        print('Items in Outfit:')
        for it in rec.get('items', []):
            print(f"  - [{it['category']}] {it['name']} ({it['color']}) -> {it['image_url']}")

    # GET /outfits
    outfits_url = 'http://127.0.0.1:8000/outfits'
    req = urllib.request.Request(outfits_url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as resp:
        outfits = json.loads(resp.read().decode())
        print(f'\nHISTORY OF {len(outfits)} OUTFITS:')
        for o in outfits:
            print(f"  Tenue #{o['id']} ({o['datePrevue']}) - Occasion: {o['occasion']} - Score: {o['scoreCompatibilite']}/100")

    # GET /shopping/suggestions
    sug_url = 'http://127.0.0.1:8000/shopping/suggestions'
    req = urllib.request.Request(sug_url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as resp:
        sugs = json.loads(resp.read().decode())
        print(f'\nFETCHED {len(sugs)} SHOPPING SUGGESTIONS:')
        for s in sugs:
            art = s.get('article', {})
            print(f"  [{art.get('nom')}] - {art.get('prix')} € - Image: {art.get('imageUrl')}")

if __name__ == '__main__':
    test()
