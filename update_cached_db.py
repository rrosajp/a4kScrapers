# -*- coding: utf-8 -*-

import os
import sys
import importlib
import requests

A4KSCRAPERS_ENV = os.getenv('A4KSCRAPERS_ENV')
if A4KSCRAPERS_ENV:
  for env_var in A4KSCRAPERS_ENV.split('|==|'):
    if env_var == '':
      continue
    env_var_sep_index = env_var.index('=')
    env_var_name = env_var[:env_var_sep_index]
    env_var_value = env_var[env_var_sep_index+1:]
    os.environ[env_var_name] = env_var_value

dir_name = os.path.dirname(__file__)
providers = os.path.join(dir_name, 'providers')
a4kScrapers = os.path.join(providers, 'a4kScrapers')
en = os.path.join(a4kScrapers, 'en')
torrent = os.path.join(en, 'torrent')

providerModules = os.path.join(dir_name, 'providerModules')
a4kScrapers2 = os.path.join(providerModules, 'a4kScrapers')
third_party = os.path.join(a4kScrapers2, 'third_party')

sys.path.append(dir_name)
sys.path.append(providers)
sys.path.append(a4kScrapers)
sys.path.append(en)
sys.path.append(torrent)

sys.path.append(providerModules)
sys.path.append(a4kScrapers2)
sys.path.append(third_party)

from providerModules.a4kScrapers import core, cache
from providers.a4kScrapers.en import torrent as torrent_module

torrent_scrapers = {}
for scraper in torrent_module.__all__:
    if scraper in ['bitsearch', 'kickass', 'magnetdl', 'nyaa', 'piratebay', 'torrentio', 'torrentz2', 'yts']:
        torrent_scrapers[scraper] = importlib.import_module('providers.a4kScrapers.en.torrent.%s' % scraper)

url = os.getenv('A4KSCRAPERS_TRAKT_API_URL')
if not url:
    print("Error: A4KSCRAPERS_TRAKT_API_URL environment variable is not set")
    sys.exit(1)

headers_env = os.getenv('A4KSCRAPERS_TRAKT_HEADERS')
if not headers_env:
    print("Error: A4KSCRAPERS_TRAKT_HEADERS environment variable is not set")
    sys.exit(1)

headers_array = headers_env.split(';')
headers = { 'Content-Type': 'application/json' }
for header in headers_array:
    if '=' in header:
        key, value = header.split('=', 1)
        headers[key] = value

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raises an HTTPError for bad responses
    
    if not response.text.strip():
        print("Error: API returned empty response")
        sys.exit(1)
    
    movies = response.json()
    
    if not isinstance(movies, list):
        print(f"Error: Expected list from API, got {type(movies).__name__}")
        print(f"Response content: {response.text[:500]}...")
        sys.exit(1)
        
except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
    sys.exit(1)
except ValueError as e:
    print(f"Error parsing JSON response: {e}")
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.text[:500]}...")
    sys.exit(1)

sources_dict = {}

for movie_result in movies:
    try:
        full_query = ''
        scraper_results = {}

        if 'movie' not in movie_result:
            print(f"Warning: Skipping invalid movie result: {movie_result}")
            continue
            
        movie = movie_result['movie']
        
        # Validate required movie fields
        if not all(key in movie for key in ['title', 'year', 'ids']):
            print(f"Warning: Skipping movie with missing fields: {movie}")
            continue
            
        if 'imdb' not in movie['ids']:
            print(f"Warning: Skipping movie without IMDB ID: {movie}")
            continue
        
        for scraper in torrent_scrapers:
            try:
                sources = sources_dict.setdefault(scraper, torrent_scrapers[scraper].sources())
                results = sources.movie(movie['title'], str(movie['year']), movie['ids']['imdb'])

                if not isinstance(sources.scraper, core.NoResultsScraper):
                    full_query = sources.scraper.full_query
                    scraper_results[scraper] = results
                    
            except Exception as e:
                print(f"Warning: Error with scraper {scraper} for movie {movie['title']}: {e}")
                continue

        if full_query and scraper_results:
            try:
                cache.set_cache(full_query, scraper_results)
            except Exception as e:
                print(f"Warning: Error caching results for query '{full_query}': {e}")
                
    except Exception as e:
        print(f"Warning: Error processing movie result: {e}")
        continue

print(f"Successfully processed {len(movies)} movies")
