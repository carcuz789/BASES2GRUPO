import redis
import json
import pymongo
import unittest

# Redis client (local)
redis_client = redis.StrictRedis(
    host='localhost',
    port=6379,
    decode_responses=True
)

# MongoDB client (local)
mongo_client = pymongo.MongoClient('mongodb://admin:1234@localhost:27017/')
mongo_db = mongo_client['nba_db']
mongo_collection = mongo_db['player_profiles']

# Cache player info
def cache_player_info(player_id):
    player_data = mongo_collection.find_one({"_id": player_id})
    if player_data:
        redis_client.setex(f"player:{player_id}", 3600, json.dumps(player_data))  # Cache for 1 hour
        return player_data
    return None

# Get player info (cache-aside)
def get_player_info(player_id):
    cached_data = redis_client.get(f"player:{player_id}")
    if cached_data:
        return json.loads(cached_data)
    return cache_player_info(player_id)

# Unit tests
class TestRedisCache(unittest.TestCase):
    def setUp(self):
        self.player_id = 1000
        self.test_data = {
            "_id": self.player_id,
            "first_name": "Shandon",
            "last_name": "Anderson",
            "team": {"team_id": 1610612738, "full_name": "Boston Celtics"}
        }
        mongo_collection.insert_one(self.test_data)

    def test_cache_hit(self):
        cache_player_info(self.player_id)
        result = get_player_info(self.player_id)
        self.assertEqual(result["first_name"], "Shandon")

    def test_cache_miss(self):
        redis_client.delete(f"player:{self.player_id}")
        result = get_player_info(self.player_id)
        self.assertEqual(result["first_name"], "Shandon")
        cached = redis_client.get(f"player:{self.player_id}")
        self.assertIsNotNone(cached)

    def tearDown(self):
        mongo_collection.delete_one({"_id": self.player_id})
        redis_client.delete(f"player:{self.player_id}")

if __name__ == "__main__":
    unittest.main()