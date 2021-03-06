import pandas as pd
import csv, json, os, requests, shutil

# create dataframe 
# base_path = os.path.join("c:", os.sep,"Users", "khana", "OneDrive", "Documents", "Cindy_Synthea") # different computer
base_path = os.path.join("/Users", "home", "Documents", "Cindy_Synthea")
df = pd.read_excel(os.path.join(base_path, "eMERGE_List.xlsx"), mode = 'r', sheet_name='NUJHU Positive Sample List')

# modify df to make it more general, add more if searching for certain indications is hard
for row in range(len(df.index)):
    if df.loc[row, 'race'] == 'Black or African American':
        df.loc[row, 'race'] = 'Black'
    if df.loc[row, 'race'] == 'Unknown':
        df.loc[row, 'race'] = 'NONE'
    if df.loc[row, 'race'] == 'Unspecified':
        df.loc[row, 'race'] = 'NONE'
    if df.loc[row, 'gender'] == 'Male':
        df.loc[row, 'gender'] = 'M'
    if df.loc[row, 'gender'] == 'Female':
        df.loc[row, 'gender'] = 'F'
    if df.loc[row, 'indication'] == 'Colorectal Cancer / Polyps':
        df.loc[row, 'indication'] = 'colon cancer'
    if df.loc[row, 'indication'] == 'Breast carcinoma':
        df.loc[row, 'indication'] = 'breast cancer'
    if df.loc[row, 'indication'] == 'Ovarian Cancer, Epithelial, Included':
        df.loc[row, 'indication'] = 'ovarian cancer'
    if df.loc[row, 'indication'] == 'Not selected for trait' or df.loc[row, 'indication'] == 'Healthy':
        df.loc[row, 'indication'] = 'NONE'
# add last column   
df["Freq of Unique Codes"] = " "
df.to_csv(os.path.join(base_path, "eMERGE_List.csv"), index=False) 


# Find all value of specified key of nested JSON into array 
def extract_values(obj, key):
    arr = []
    def extract(obj, arr, key):
        # Recursively search for values of key in JSON tree
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results


# access ohdsi API to find all SNOMED codes
def findSNOMED_ohdsi(txt): 
    url_con = "http://api.ohdsi.org/WebAPI/vocabulary/search"
    headers = {'content-type': 'application/json'}
    params = {"QUERY": txt,
              "VOCABULARY_ID": ['SNOMED']}
    response = requests.post(url_con, data=json.dumps(params), headers=headers)
    data = json.loads(response.text)
    return [d["CONCEPT_CODE"] for d in data]


# create array of csv information
info = []
with open(os.path.join(base_path, "eMERGE_List.csv"), mode = 'r') as csvfile:
    reader = csv.reader(csvfile) # change contents to floats
    next(reader, None)
    for row in reader: # each row is a list
        info.append(row)
        
#create list of indication and convert to set to get unique indications
indication_list = []
for row in info:
    indication_list.append(row[6])
unique_indications = set(indication_list)

# create dictionary of indications and corresponding SNOMED codes
codes_indications = dict.fromkeys(unique_indications, [])
for key, val in codes_indications.items():
    if key == 'NONE': val == [162673000]
    else: val = findSNOMED_ohdsi(key)
        
        
# create place to store eventual directories
all_output = os.path.join(base_path, "all")
if not os.path.exists(all_output):
    os.makedirs(all_output)
accepted_output = os.path.join(base_path, "accepted")
if not os.path.exists(accepted_output):
    os.makedirs(accepted_output)
    

# loop through each patient    
for index, row_content in enumerate(info):
    row_output = os.path.join(base_path, "all", str(index))
    if not os.path.exists(row_output):
        os.makedirs(row_output)
    # find match for each patient
    check = True
    while check:
        os.chdir(row_output)
        os.system(' '.join(['java', '-jar', os.path.join(base_path, "synthea-with-dependencies.jar"),'-p 10', '-a ' + row_content[3] + '-' + row_content[3], '-g ' + row_content[5]]))
        filelist = os.listdir(os.path.join(row_output, "output", "fhir"))
        for file in filelist:
            with open(os.path.join(row_output, "output", "fhir", file), 'r', encoding='utf8', errors='replace') as f:
                json_text = json.load(f)
                try: 
                    print(json_text['entry'][0]['resource']['extension'][0]['extension'][1]['valueString'] + "\n")
                    race = json_text['entry'][0]['resource']['extension'][0]['extension'][1]['valueString']
                    if race == row_content[4] or row_content[4] == 'NONE':
                        codes = extract_values(f, 'code')
                        for code in codes:
                            if len(code) != 9 or not code.isdigit():
                                codes.pop(code)
                        if set(codes) & set(codes_indications[row_content[6]]):
                            info[row,0] = json_text['entry'][0]['resource']['id']
                            shutil.move(os.path.join(row_output, "output", "fhir", file), os.path.join(row_output, "output", "fhir", file), os.path.join(base_path, "accepted"))
                            check = False
                            break
                except KeyError: # since some seem to not the race dictionary key??
                    check = False
                    
                os.remove(os.path.join(row_output, "output", "fhir", file))
                      
info.to_csv(os.path.join(base_path, "matchdf.csv"), index=False)


