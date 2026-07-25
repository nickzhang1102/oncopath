import redis
import os
from dotenv import load_dotenv
load_dotenv()

r = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', '') or None,
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)
keys = list(r.scan_iter('consultation:global:*'))
for key in keys:
    r.delete(key)
    print(f'Deleted: {key}')
if not keys:
    print('No consultation locks found')
print('Done')
