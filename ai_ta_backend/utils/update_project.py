import os
from supabase import create_client
from dotenv import load_dotenv
from urllib.parse import urlparse
import json

load_dotenv()



def webscrape_documents(project_name: str):
    print(f"Scraping documents for project: {project_name}")

    # create Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_API_KEY")
    supabase_client = create_client(supabase_url, supabase_key)

    # use RPC to get unique base_urls
    # response = supabase_client.rpc("get_distinct_base_urls", {"p_course_name": project_name}).execute()   # this only returns base_urls
    response = supabase_client.rpc("get_base_url_with_doc_groups", {"p_course_name": project_name}).execute()   # this returns base_urls with document groups
    print(f"Base urls: {response}")
    base_urls = response.data
    print(f"Total base_urls: {len(base_urls)}")

    #webcrawl_url = "https://crawlee.kastan.ai/crawl"
    webcrawl_url = "https://crawlee-production.up.railway.app/crawl"

    payload = {
        "params": {
            "url": "",
            "scrapeStrategy": "equal-and-below",
            "match": "",
            "maxPagesToCrawl": 5,
            "maxTokens": 2000000,
            "courseName": project_name
        }
    }

    for base_url in base_urls:
        print(f"Base URL: {base_url}")
        print(f"Document Group: {base_urls[base_url]}")
        payload["params"]["url"] = base_url
        domain = urlparse(base_url).netloc
        print(f"Domains: {domain}")
        payload["params"]["match"] = "http?(s)://" + domain + "/**"
        payload["params"]["documentGroups"] = base_urls[base_url]
        print("Payload: ", payload)
        break
        # response = requests.post(webcrawl_url, json=payload)
        # print("Response from crawl: ", response.json())



    return "Webscrape done."