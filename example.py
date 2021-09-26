import aiofiles
import os
import json

lines = None

# for dirpath, _, filenames in os.walk("/storage/output.second.null"):
#     for filename in filenames:
#         filepath = os.path.join(dirpath, filename)
#         with open(filepath, "r") as f:
#             content = f.read()

#             content = content.replace("null", "")
#             content = content.replace("None", "")
#             delimiter = '{"category":'
#             lines = (delimiter+l for l in content.split(delimiter) if l)

#         with open(filepath, "w") as f:
#             for l in lines:
#                 f.write(l)
#                 f.write(os.linesep)


for dirpath, _, filenames in os.walk("/storage/output.firsttime"):
    for filename in filenames:
        category_id = filename.split("_")[0]
        filepath = os.path.join(dirpath, filename)
        with open(filepath, "r") as f:
            content = f.read()
            data = json.loads(content)
            
        with open(filepath, "w") as f:
            for d in data:
                if not d:
                    continue
                d["category"] = category_id
                f.write(json.dumps(d))
                f.write(os.linesep)