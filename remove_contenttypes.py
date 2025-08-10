import json

input_file = 'data_clean.json'
output_file = 'data_clean_no_contenttypes.json'

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filter out contenttypes entries
filtered_data = [obj for obj in data if obj.get('model') != 'contenttypes.contenttype']

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(filtered_data, f, indent=2)

print(f"Filtered fixture saved to {output_file}")
