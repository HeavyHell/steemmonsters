import random
import string
import hashlib


def generate_key(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def generate_team_hash(summoner, monsters, secret):
    m = hashlib.md5()
    m.update((summoner + ',' + ','.join(monsters) + ',' + secret).encode("utf-8"))
    team_hash = m.hexdigest()
    return team_hash
