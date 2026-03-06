"""Module for storing recommendations in Notion."""
import json
import requests
from notion_client import Client
from config import NOTION_API_KEY, NOTION_DATABASE_ID
from datetime import datetime


class NotionStorage:
    def __init__(self):
        self.client = Client(auth=NOTION_API_KEY)
        self.database_id = NOTION_DATABASE_ID
    
    def _upload_file_to_notion(self, file_bytes: bytes, mime_type: str, filename: str) -> dict:
        """Upload file to Notion using Direct Upload API.
        
        Returns dict with 'file_id' and 'url' or None if upload fails.
        According to: https://developers.notion.com/docs/uploading-small-files
        """
        try:
            from image_processor import get_file_extension_from_mime_type
            
            # Step 1: Create file upload request
            # Using newer API version for file uploads support
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            # Ensure filename has correct extension
            if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                ext = get_file_extension_from_mime_type(mime_type)
                filename = f"{filename.rsplit('.', 1)[0] if '.' in filename else filename}.{ext}"
            
            create_upload_data = {
                "name": filename,
                "type": mime_type
            }
            
            response = requests.post(
                "https://api.notion.com/v1/file_uploads",
                headers=headers,
                json=create_upload_data
            )
            
            if response.status_code != 200:
                print(f"Error creating file upload: {response.status_code} - {response.text}")
                return None
            
            upload_info = response.json()
            upload_url = upload_info.get("upload_url")
            file_id = upload_info.get("id")  # Notion API returns "id", not "file_id"
            
            # Check if we have the required fields
            if upload_url and file_id:
                # Both fields are present, proceed with upload
                pass
            else:
                print(f"Missing upload_url or id in response: {upload_info}")
                print(f"  upload_url: {upload_url}")
                print(f"  file_id: {file_id}")
                return None
            
            # Step 2: Upload file content to the upload_url
            # According to Notion API docs, use POST with multipart/form-data
            # The upload_url endpoint is /send which expects POST
            # Authorization header is required even for presigned URLs
            files = {
                'file': (filename, file_bytes, mime_type)
            }
            
            upload_headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28"
            }
            
            # Use POST request with multipart/form-data
            upload_response = requests.post(
                upload_url,
                files=files,
                headers=upload_headers
            )
            
            if upload_response.status_code not in (200, 201, 204):
                print(f"Error uploading file content: {upload_response.status_code} - {upload_response.text}")
                print(f"  Upload URL: {upload_url}")
                print(f"  File size: {len(file_bytes)} bytes, MIME: {mime_type}")
                return None
            
            print(f"✅ File uploaded successfully: {filename} ({len(file_bytes)} bytes)")
            # Return file_id to use in file block
            # According to Notion API, use file_id directly in the file block
            return {
                "file_id": file_id
            }
                
        except Exception as e:
            print(f"Error uploading file to Notion: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_by_category(self, category: str) -> list:
        """Get all items for a given category."""
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={"property": "Category", "select": {"equals": category}},
                sorts=[{"property": "Timestamp", "direction": "descending"}]
            )
            results = []
            for page in response.get("results", []):
                props = page["properties"]
                title = props.get("Title", {}).get("title", [{}])
                context = props.get("Context", {}).get("rich_text", [{}])
                results.append({
                    "title": title[0].get("plain_text", "") if title else "",
                    "context": context[0].get("plain_text", "") if context else "",
                })
            return results
        except Exception as e:
            print(f"Error fetching category {category}: {e}")
            return []

    def save_recommendation(
        self,
        category: str,
        title: str,
        context: str,
        url: str,
        tags: list,
        confidence: float,
        raw_input: str,
        telegram_chat_id: int,
        telegram_message_id: int,
        image_url: str = None,
        image_bytes: bytes = None
    ):
        """Save recommendation to Notion database."""
        try:
            properties = {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Timestamp": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                },
                "Category": {
                    "select": {
                        "name": category
                    }
                }
            }

            # Add tags if provided
            if tags and len(tags) > 0:
                tags_str = ", ".join([str(tag) for tag in tags[:10]])  # Convert to comma-separated string
                properties["Tags"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": tags_str
                            }
                        }
                    ]
                }

            # Add URL if provided (extracted from text or image)
            if url:
                properties["URL"] = {
                    "url": url
                }

            # Add context if provided
            if context:
                properties["Context"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": context[:2000]  # Limit to 2000 chars
                            }
                        }
                    ]
                }

            # Add confidence
            properties["Confidence"] = {
                "number": min(max(float(confidence), 0.0), 1.0)  # Clamp between 0 and 1
            }

            # Add raw input
            if raw_input:
                properties["Raw Input"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": raw_input[:2000]  # Limit to 2000 chars
                            }
                        }
                    ]
                }

            # Add Telegram IDs
            properties["Telegram Chat ID"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": str(telegram_chat_id)
                        }
                    }
                ]
            }
            properties["Telegram Message ID"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": str(telegram_message_id)
                        }
                    }
                ]
            }

            # Upload image and add to Preview property if image_bytes provided
            if image_bytes:
                try:
                    from image_processor import get_image_mime_type, get_file_extension_from_mime_type
                    
                    mime_type = get_image_mime_type(image_bytes)
                    ext = get_file_extension_from_mime_type(mime_type)
                    filename = f"image.{ext}"
                    
                    # Upload file to Notion
                    upload_result = self._upload_file_to_notion(image_bytes, mime_type, filename)
                    
                    if upload_result and upload_result.get("file_id"):
                        # Add image to Preview property
                        file_id = upload_result["file_id"]
                        properties["Preview"] = {
                            "files": [
                                {
                                    "name": filename,
                                    "file_upload": {
                                        "id": file_id
                                    }
                                }
                            ]
                        }
                        print(f"✅ Image uploaded and added to Preview property")
                    else:
                        print(f"⚠️ Failed to upload image, skipping Preview property")
                except Exception as e:
                    print(f"⚠️ Error uploading image to Preview: {e}")
                    import traceback
                    traceback.print_exc()
            elif image_url:
                # Fallback: try to add external URL to Preview (may not work for Telegram URLs)
                try:
                    properties["Preview"] = {
                        "files": [
                            {
                                "name": "image.jpg",
                                "external": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                    print(f"✅ Image URL added to Preview (may not display if requires auth)")
                except Exception as e:
                    print(f"⚠️ Error adding image URL to Preview: {e}")

            # Create page with all properties including Preview
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            return True
        except Exception as e:
            print(f"Error saving to Notion: {e}")
            import traceback
            traceback.print_exc()
            return False


