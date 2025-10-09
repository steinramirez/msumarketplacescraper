#!/usr/bin/env python3
"""Test script to check if bot can start up without errors"""

import os
from dotenv import load_dotenv
load_dotenv()

def test_bot_imports():
    """Test that all bot components can be imported"""
    try:
        import discord
        from discord.ext import commands
        from discord_bot import NFTScraper
        print("✅ Bot imports successful")
        return True
    except Exception as e:
        print(f"❌ Bot import failed: {e}")
        return False

def test_discord_token():
    """Test if Discord token is available"""
    token = os.getenv('DISCORD_TOKEN')
    if token and len(token) > 50:  # Basic validation
        print("✅ Discord token found and seems valid")
        return True
    else:
        print("❌ Discord token not found or invalid")
        return False

def test_scraper_class():
    """Test NFTScraper class instantiation"""
    try:
        from discord_bot import NFTScraper
        scraper = NFTScraper()
        print("✅ NFTScraper instantiated successfully")
        return True
    except Exception as e:
        print(f"❌ NFTScraper failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing bot startup components...")
    tests = [
        test_bot_imports,
        test_discord_token,
        test_scraper_class,
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    if passed == len(tests):
        print("🎉 All startup tests passed! Bot should be ready to run.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
