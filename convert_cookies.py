import json
import re

def parse_netscape_cookie_file(filepath):
    cookies = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 7:
                continue
            domain, flag, path, secure, expires, name, value = parts[:7]
            cookie = {
                "domain": domain,
                "httpOnly": False,  # не указано в формате, можно оставить False
                "name": name,
                "path": path,
                "secure": secure == 'TRUE',
                "value": value,
                "expires": int(expires)
            }
            cookies.append(cookie)
    return cookies

if __name__ == '__main__':
    cookies = parse_netscape_cookie_file('cookies.json')
    with open('cookies.json', 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2)
    print("Конвертация завершена. Файл cookies.json создан.")