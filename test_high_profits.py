import requests

def get_bz():
    r = requests.get('https://api.hypixel.net/v2/skyblock/bazaar')
    data = r.json().get('products', {})
    
    crops = ['DEVOURER', 'SHELLFRUIT', 'ZOMBUD', 'ALL_IN_ALOE', 'MAGIC_JELLYBEAN', 'BLASTBERRY', 'TURTLELLINI']
    for bz_id in crops:
        price = data.get(bz_id, {}).get('quick_status', {}).get('sellPrice', 0)
        print(f"{bz_id}: {price:,.2f} coins")

if __name__ == "__main__":
    get_bz()
