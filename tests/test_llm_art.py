import json
import os
from llm import art_director_concept
watch_info = {
    'selected_watch': 'Rolex Submariner',
    'search_query': 'Rolex Submariner high quality face',
    'watch_description': 'A beautiful dive watch.'
}
# Find the downloaded watch image
output_dir = "output"
latest_job = max([f.split('_')[0] for f in os.listdir(output_dir) if '_source.jpg' in f])
watch_image_path = os.path.join(output_dir, f"{latest_job}_source.jpg")
print("Using image:", watch_image_path)
import logging
logging.basicConfig(level=logging.DEBUG)
try:
    res = art_director_concept(watch_image_path, watch_info)
    print("Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
