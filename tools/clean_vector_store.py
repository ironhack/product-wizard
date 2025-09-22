#!/usr/bin/env python3

"""
Clean Vector Store - Remove Berlin Files

This script lists and removes files from the OpenAI vector store.
Specifically designed to clean up Berlin campus files after closure.

Usage:
    python3 tools/clean_vector_store.py --list                    # List all files
    python3 tools/clean_vector_store.py --remove-berlin          # Remove Berlin files
    python3 tools/clean_vector_store.py --remove-file FILE_ID    # Remove specific file

Example:
    python3 tools/clean_vector_store.py --remove-berlin
"""

import os
import sys
import time
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def get_openai_client():
    """Initialize OpenAI client with API key validation"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("   Please set this in your .env file or environment")
        return None
    
    vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
    if not vector_store_id:
        print("❌ Error: OPENAI_VECTOR_STORE_ID environment variable is required")
        print("   Please set this in your .env file or environment")
        return None
    
    client = OpenAI(api_key=api_key)
    return client, vector_store_id

def list_vector_store_files():
    """List all files in the vector store"""
    print("🔍 Vector Store File Cleanup Tool")
    print("=" * 50)
    
    client_info = get_openai_client()
    if not client_info:
        return False
    
    client, vector_store_id = client_info
    
    try:
        print(f"📂 Listing files in vector store: {vector_store_id}")
        print()
        
        # Get all files in the vector store
        vector_store_files = client.vector_stores.files.list(
            vector_store_id
        )
        
        if not vector_store_files.data:
            print("📭 No files found in vector store")
            return True
        
        print(f"📋 Found {len(vector_store_files.data)} files:")
        print()
        
        berlin_files = []
        other_files = []
        
        for file_obj in vector_store_files.data:
            # Get file details
            try:
                file_details = client.files.retrieve(file_obj.id)
                filename = file_details.filename
                file_id = file_obj.id
                status = file_obj.status
                
                file_info = {
                    'id': file_id,
                    'filename': filename,
                    'status': status
                }
                
                if 'berlin' in filename.lower():
                    berlin_files.append(file_info)
                else:
                    other_files.append(file_info)
                    
            except Exception as e:
                print(f"⚠️  Could not get details for file {file_obj.id}: {e}")
        
        # Display results
        if berlin_files:
            print("🎯 BERLIN FILES (to be removed):")
            for file_info in berlin_files:
                print(f"   🔴 {file_info['filename']}")
                print(f"      ID: {file_info['id']}")
                print(f"      Status: {file_info['status']}")
                print()
        
        if other_files:
            print("✅ OTHER FILES (will be kept):")
            for file_info in other_files:
                print(f"   🟢 {file_info['filename']}")
                print(f"      ID: {file_info['id']}")
                print(f"      Status: {file_info['status']}")
                print()
        
        if berlin_files:
            print(f"📊 Summary: {len(berlin_files)} Berlin files found for removal")
        else:
            print("✅ No Berlin files found - vector store is already clean!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing vector store files: {e}")
        return False

def remove_berlin_files():
    """Remove all Berlin-related files from the vector store"""
    print("🧹 Vector Store Berlin Cleanup")
    print("=" * 50)
    
    client_info = get_openai_client()
    if not client_info:
        return False
    
    client, vector_store_id = client_info
    
    try:
        print(f"🔍 Scanning vector store: {vector_store_id}")
        
        # Get all files in the vector store
        vector_store_files = client.vector_stores.files.list(
            vector_store_id
        )
        
        if not vector_store_files.data:
            print("📭 No files found in vector store")
            return True
        
        # Find Berlin files
        berlin_files = []
        for file_obj in vector_store_files.data:
            try:
                file_details = client.files.retrieve(file_obj.id)
                filename = file_details.filename
                
                if 'berlin' in filename.lower():
                    berlin_files.append({
                        'id': file_obj.id,
                        'filename': filename,
                        'status': file_obj.status
                    })
            except Exception as e:
                print(f"⚠️  Could not get details for file {file_obj.id}: {e}")
        
        if not berlin_files:
            print("✅ No Berlin files found - vector store is already clean!")
            return True
        
        print(f"🎯 Found {len(berlin_files)} Berlin files to remove:")
        for file_info in berlin_files:
            print(f"   🔴 {file_info['filename']}")
        print()
        
        # Confirm deletion
        confirmation = input("⚠️  Are you sure you want to delete these files? (type 'yes' to confirm): ")
        if confirmation.lower() != 'yes':
            print("❌ Deletion cancelled")
            return False
        
        print("🗑️  Starting deletion process...")
        
        # Remove each Berlin file
        removed_count = 0
        for file_info in berlin_files:
            try:
                print(f"   Removing: {file_info['filename']}")
                
                # Remove from vector store
                client.vector_stores.files.delete(
                    file_id=file_info['id'],
                    vector_store_id=vector_store_id
                )
                
                # Delete the file itself
                client.files.delete(file_info['id'])
                
                print(f"   ✅ Removed: {file_info['filename']}")
                removed_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed to remove {file_info['filename']}: {e}")
        
        print()
        print(f"🎉 Successfully removed {removed_count}/{len(berlin_files)} Berlin files!")
        print("🧹 Vector store cleanup complete!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

def remove_specific_file(file_id):
    """Remove a specific file by ID"""
    print(f"🗑️  Removing specific file: {file_id}")
    print("=" * 50)
    
    client_info = get_openai_client()
    if not client_info:
        return False
    
    client, vector_store_id = client_info
    
    try:
        # Get file details first
        try:
            file_details = client.files.retrieve(file_id)
            filename = file_details.filename
            print(f"📄 File found: {filename}")
        except:
            filename = file_id
            print(f"📄 File ID: {file_id}")
        
        # Confirm deletion
        confirmation = input(f"⚠️  Are you sure you want to delete '{filename}'? (type 'yes' to confirm): ")
        if confirmation.lower() != 'yes':
            print("❌ Deletion cancelled")
            return False
        
        # Remove from vector store
        client.vector_stores.files.delete(
            file_id=file_id,
            vector_store_id=vector_store_id
        )
        
        # Delete the file itself
        client.files.delete(file_id)
        
        print(f"✅ Successfully removed: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error removing file: {e}")
        return False

def main():
    """Main function to handle command line usage"""
    parser = argparse.ArgumentParser(description="Clean OpenAI Vector Store")
    parser.add_argument("--list", action="store_true", help="List all files in vector store")
    parser.add_argument("--remove-berlin", action="store_true", help="Remove all Berlin files")
    parser.add_argument("--remove-file", type=str, help="Remove specific file by ID")
    
    args = parser.parse_args()
    
    if args.list:
        success = list_vector_store_files()
    elif args.remove_berlin:
        success = remove_berlin_files()
    elif args.remove_file:
        success = remove_specific_file(args.remove_file)
    else:
        print("🚀 OpenAI Vector Store Cleanup Tool")
        print("=" * 50)
        print()
        print("Usage:")
        print("  python3 tools/clean_vector_store.py --list                    # List all files")
        print("  python3 tools/clean_vector_store.py --remove-berlin          # Remove Berlin files")
        print("  python3 tools/clean_vector_store.py --remove-file FILE_ID    # Remove specific file")
        print()
        print("Examples:")
        print("  python3 tools/clean_vector_store.py --list")
        print("  python3 tools/clean_vector_store.py --remove-berlin")
        return
    
    if success:
        print("\n✅ SUCCESS: Operation completed!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Operation did not complete successfully!")
        sys.exit(1)

if __name__ == "__main__":
    main()
