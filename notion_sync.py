
import requests

NOTION_TOKEN = "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"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

SOURCE_DB_ID = "20aa2e37-ed82-805b-9381-e4c881b8a6ac"
TARGET_DB_ID = "20aa2e37-ed82-8040-8bcf-fc4fdcc5842c"

def get_source_data():
    url = f"https://api.notion.com/v1/databases/{SOURCE_DB_ID}/query"
    response = requests.post(url, headers=HEADERS)
    return response.json()["results"]

def summarize_data(pages):
    summary = {}

    for page in pages:
        props = page["properties"]
        try:
            material = props["材料編號"]["title"][0]["plain_text"]
            number = props["數量"]["number"]
            location = props["位置"]["multi_select"][0]["name"] if props["位置"]["multi_select"] else ""
            name = props["姓名"]["rich_text"][0]["plain_text"] if props["姓名"]["rich_text"] else ""

            # 🔧 新增欄位
            description = props["說明"]["rich_text"][0]["plain_text"] if props["說明"]["rich_text"] else ""
            spec = props["規格"]["rich_text"][0]["plain_text"] if props["規格"]["rich_text"] else ""

            if material not in summary:
                summary[material] = {
                    "total": number,
                    "location": location,
                    "name": name,
                    "description": description,  # 🔧
                    "spec": spec                 # 🔧
                }
            else:
                summary[material]["total"] += number
                # 其他欄位保留第一次出現的值

        except Exception as e:
            print(f"資料欄位讀取錯誤: {e}")

    return summary

def get_existing_materials():
    url = f"https://api.notion.com/v1/databases/{TARGET_DB_ID}/query"
    existing = {}
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        response = requests.post(url, headers=HEADERS, json=payload)
        data = response.json()

        for page in data["results"]:
            props = page["properties"]
            try:
                material = props["材料編號"]["title"][0]["plain_text"]
                existing[material] = page["id"]
            except Exception as e:
                print(f"讀取目標表單錯誤: {e}")

        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    return existing

def write_to_target_db(summary):
    existing = get_existing_materials()

    for material, info in summary.items():
        total = info["total"]
        location = info["location"]
        name = info["name"]
        description = info["description"]  # 🔧
        spec = info["spec"]                # 🔧

        data = {
            "properties": {
                "材料編號": {
                    "title": [{"text": {"content": material}}]
                },
                "數量": {
                    "number": total
                },
                "位置": {
                    "multi_select": [{"name": location}] if location else []
                },
                "姓名": {
                    "rich_text": [{"text": {"content": name}}] if name else []
                },
                # 🔧 加入說明與規格
                "說明": {
                    "rich_text": [{"text": {"content": description}}] if description else []
                },
                "規格": {
                    "rich_text": [{"text": {"content": spec}}] if spec else []
                }
            }
        }

        if material in existing:
            page_id = existing[material]
            url = f"https://api.notion.com/v1/pages/{page_id}"
            response = requests.patch(url, headers=HEADERS, json=data)
            print(f"✅ 更新 {material}，數量: {total}，狀態碼: {response.status_code}")
        else:
            data["parent"] = {"database_id": TARGET_DB_ID}
            url = "https://api.notion.com/v1/pages"
            response = requests.post(url, headers=HEADERS, json=data)
            print(f"➕ 新增 {material}，數量: {total}，狀態碼: {response.status_code}")

# 主流程
pages = get_source_data()
summary = summarize_data(pages)
write_to_target_db(summary)
