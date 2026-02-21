import requests

def get_bz():
    r = requests.get('https://api.hypixel.net/v2/skyblock/bazaar')
    data = r.json().get('products', {})
    print("Devourer:", data.get('DEVOURER', {}).get('quick_status', {}).get('sellPrice', 'N/A'))
    print("Shellfruit:", data.get('SHELLFRUIT', {}).get('quick_status', {}).get('sellPrice', 'N/A'))
    print("Zombud:", data.get('ZOMBUD', {}).get('quick_status', {}).get('sellPrice', 'N/A'))

if __name__ == "__main__":
    get_bz()
