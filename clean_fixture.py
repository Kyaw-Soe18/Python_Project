import json

# Open your original data.json file
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Loop through all objects in the JSON data
for obj in data:
    # Check if the object is a Course model (adjust if your app name is different)
    if obj['model'].endswith('.course'):
        # Remove the 'section' field if it exists
        obj['fields'].pop('section', None)

# Save the cleaned data to a new file
with open('data_clean.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Cleaned data saved to data_clean.json")
