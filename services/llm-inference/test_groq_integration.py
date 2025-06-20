# test_groq_integration.py
import redis
import time
import json
import uuid

def test_llm_service():
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    # Test query
    test_query = {
        'text': 'I\'m working on a voice-first AI project. What do you think about the challenges?',
        'session_id': str(uuid.uuid4()),
        'context_needed': 'true',
        'timestamp': time.time()
    }
    
    print("Sending test query...")
    redis_client.xadd('query_stream', test_query)
    
    # Listen for response
    print("Waiting for response...")
    response = redis_client.xread({'response_stream': '$'}, block=10000)
    
    if response:
        print("Response received:")
        print(json.dumps(dict(response[0][1][0][1]), indent=2))
    else:
        print("No response received")

if __name__ == "__main__":
    test_llm_service()