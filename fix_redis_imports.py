#!/usr/bin/env python3
"""Fix Redis imports in all Python service files"""

import os
import re

# Files to update
service_files = [
    "services/websocket-server/websocket_server.py",
    "services/audio-processor/audio_processor.py",
    "services/trigger-llm/trigger_llm_handler.py",
    "services/tts-service/tts_service.py",
    "services/document-generator/document_generator.py",
]

def fix_redis_imports(filepath):
    """Replace aioredis imports with modern redis.asyncio"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace the import
    original_content = content
    content = re.sub(r'import aioredis as redis', 'import redis.asyncio as redis', content)
    
    # Fix Redis connection initialization
    # Replace redis.Redis() calls to handle environment variables properly
    content = re.sub(
        r"await redis\.Redis\(",
        "redis.Redis(",
        content
    )
    
    # Add environment variable handling for Redis host
    if 'redis_host = os.getenv' not in content and 'self.redis_client = redis.Redis(' in content:
        content = re.sub(
            r"(self\.redis_client = redis\.Redis\()\s*\n?\s*(host=)'localhost'",
            r"redis_host = os.getenv('REDIS_URL', 'redis://localhost:6379').replace('redis://', '').split(':')[0]\n        \1\n        \2redis_host",
            content
        )
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Fixed: {filepath}")
        return True
    else:
        print(f"ℹ️  No changes needed: {filepath}")
        return False

def main():
    print("Fixing Redis imports in all service files...\n")
    
    fixed_count = 0
    for filepath in service_files:
        if fix_redis_imports(filepath):
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} files")
    
    # Also update requirements files
    print("\nUpdating requirements.txt files...")
    
    req_files = []
    for root, dirs, files in os.walk("services"):
        for file in files:
            if file == "requirements.txt":
                req_files.append(os.path.join(root, file))
    
    for req_file in req_files:
        with open(req_file, 'r') as f:
            content = f.read()
        
        # Remove aioredis line
        lines = content.split('\n')
        new_lines = [line for line in lines if 'aioredis' not in line]
        
        if len(lines) != len(new_lines):
            with open(req_file, 'w') as f:
                f.write('\n'.join(new_lines))
            print(f"✅ Updated: {req_file}")

if __name__ == "__main__":
    main()