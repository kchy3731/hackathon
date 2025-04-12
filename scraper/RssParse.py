import requests
import xml.etree.ElementTree as ET
import csv
from datetime import datetime

csv_file = 'Parsed.csv'
csv_headers = ['URL', 'Author', 'Title', 'Link', 'Timestamp']

with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_headers)
    writer.writeheader()

    with open('RSS.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    for url in urls:
        print(f"\nScraping: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
            
            row_data = {'URL': url}
            
            # Get author
            author = root.find('.//atom:author/atom:name', namespaces)
            row_data['Author'] = author.text.strip() if author is not None else "N/A"
            
            # Get latest entry
            entry = root.find('.//atom:entry', namespaces)
            if entry is not None:
                row_data['Title'] = entry.find('./atom:title', namespaces).text.strip() if entry.find('./atom:title', namespaces) is not None else "N/A"
                row_data['Link'] = entry.find('./atom:link', namespaces).attrib['href'].strip() if entry.find('./atom:link', namespaces) is not None else "N/A"
            else:
                row_data['Title'] = "N/A"
                row_data['Link'] = "N/A"
            
            # Add timestamp
            row_data['Timestamp'] = datetime.now().isoformat()
            
            # Write to CSV
            writer.writerow(row_data)
            
            # Print to console
            print(f"Author: {row_data['Author']}")
            print(f"Title: {row_data['Title']}")
            print(f"Link: {row_data['Link']}")
            
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            print(error_msg)
            writer.writerow({'URL': url, 'Author': 'ERROR', 'Title': error_msg, 'Link': 'ERROR', 'Timestamp': datetime.now().isoformat()})
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            print(error_msg)
            writer.writerow({'URL': url, 'Author': 'ERROR', 'Title': error_msg, 'Link': 'ERROR', 'Timestamp': datetime.now().isoformat()})

print(f"\nScraping complete. Results saved to {csv_file}")