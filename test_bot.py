#!/usr/bin/env python3
"""Test script to verify bot can import and start up"""

import os
import time
from dotenv import load_dotenv
load_dotenv()

from discord_bot import NFTScraper

def test_scraper():
    """Test the NFT scraper"""
    print("🔍 Testing NFT scraper...")
    try:
        scraper = NFTScraper()
        results = scraper.scrape_nfts()
        print(f"✅ Scraper worked, found {len(results)} NFTs")
        if results:
            print(f"Sample NFT: {results[0]}")
        return True
    except Exception as e:
        print(f"❌ Scraper failed: {e}")
        return False

def test_imports():
    """Test core imports"""
    print("📦 Testing imports...")
    try:
        import discord
        from discord.ext import commands
        import selenium
        try:
            import psutil
        except ImportError:
            print("⚠️  psutil not available (optional)")
        print(f"✅ Core imports successful, discord version: {discord.__version__}")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running bot tests...")
    imports_ok = test_imports()
    if imports_ok:
        scraper_ok = test_scraper()
        if scraper_ok:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Imports work but scraper has issues")
    else:
        print("❌ Import tests failed")
