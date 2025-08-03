# keywordExposure/src/notion_manager.py
import os
from typing import List, Dict, Any, Optional
import logging # 로깅 임포트

from notion_client import Client, APIResponseError
from dotenv import load_dotenv

class NotionAPIError(Exception):
    """Custom exception for Notion API related errors."""
    pass

class NotionClient:
    """
    A wrapper class for the Notion API client to handle database operations.
    """
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initializes the NotionClient.

        It loads the API key and database ID from environment variables
        (.env file is supported for local development).

        Args:
            api_key (Optional[str]): The Notion API key. If not provided, it will be
                                     loaded from the NOTION_API_KEY environment variable.
            database_id (Optional[str]): The Notion Database ID. If not provided, it will be
                                         loaded from the NOTION_DATABASE_ID environment variable.

        Raises:
            NotionAPIError: If the API key or database ID is not found.
        """
        load_dotenv()  # Loads .env file if it exists

        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID")

        if not self.api_key:
            raise NotionAPIError("NOTION_API_KEY not found in environment variables or .env file.")
        if not self.database_id:
            raise NotionAPIError("NOTION_DATABASE_ID not found in environment variables or .env file.")

        self.client = Client(auth=self.api_key)
        logging.info("NotionClient 초기화 완료.") # print 대신 logging 사용

    def query_all_pages(self) -> List[Dict[str, Any]]:
        """
        Queries and returns all pages from the configured database.
        Handles pagination automatically to fetch all results.

        Returns:
            List[Dict[str, Any]]: A list of all page objects from the database.

        Raises:
            NotionAPIError: If the API call fails.
        """
        all_pages = []
        next_cursor = None
        has_more = True

        logging.info("⏳ 데이터베이스의 모든 페이지를 쿼리 중...") # print 대신 logging 사용
        while has_more:
            try:
                response = self.client.databases.query(
                    database_id=self.database_id,
                    start_cursor=next_cursor
                )
                all_pages.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                logging.info(f"HTTP Request: POST https://api.notion.com/v1/databases/{self.database_id}/query \"HTTP/1.1 200 OK\"") # 로그에서 확인된 HTTP 요청 추가
            except APIResponseError as e:
                logging.error(f"데이터베이스 쿼리 실패: {e}", exc_info=True) # print 대신 logging 사용, 트레이스백 포함
                raise NotionAPIError(f"Failed to query database: {e}") from e
        
        logging.info(f"✅ 총 {len(all_pages)}개의 페이지를 성공적으로 가져왔습니다.") # print 대신 logging 사용
        return all_pages

    def create_page(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new page in the configured database with the given properties.

        Args:
            properties (Dict[str, Any]): A dictionary representing the page properties.

        Returns:
            Dict[str, Any]: The created page object from the Notion API.

        Raises:
            NotionAPIError: If the API call fails.
        """
        logging.info("⏳ 새로운 페이지 생성 중...") # print 대신 logging 사용
        try:
            parent = {"database_id": self.database_id}
            created_page = self.client.pages.create(parent=parent, properties=properties)
            logging.info(f"✅ 페이지 성공적으로 생성. URL: {created_page.get('url')}") # print 대신 logging 사용
            return created_page
        except APIResponseError as e:
            logging.error(f"페이지 생성 실패: {e}", exc_info=True) # print 대신 logging 사용, 트레이스백 포함
            raise NotionAPIError(f"Failed to create page: {e}") from e

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates properties of an existing page in Notion.

        Args:
            page_id (str): The ID of the page to update.
            properties (Dict[str, Any]): A dictionary representing the properties to update.

        Returns:
            Dict[str, Any]: The updated page object from the Notion API.

        Raises:
            NotionAPIError: If the API call fails.
        """
        logging.info(f"⏳ 페이지 ID: {page_id} 업데이트 중...") # print 대신 logging 사용
        try:
            updated_page = self.client.pages.update(page_id=page_id, properties=properties)
            logging.info(f"✅ 페이지 성공적으로 업데이트. URL: {updated_page.get('url')}") # print 대신 logging 사용
            return updated_page
        except APIResponseError as e:
            logging.error(f"페이지 {page_id} 업데이트 실패: {e}", exc_info=True) # print 대신 logging 사용, 트레이스백 포함
            raise NotionAPIError(f"Failed to update page {page_id}: {e}") from e

    def get_database_schema(self) -> Dict[str, Any]:
        """
        Retrieves and returns the schema (properties) of the configured database.

        Returns:
            Dict[str, Any]: A dictionary representing the database schema.

        Raises:
            NotionAPIError: If the API call fails.
        """
        logging.info("⏳ 데이터베이스 스키마 가져오는 중...") # print 대신 logging 사용
        try:
            database_info = self.client.databases.retrieve(database_id=self.database_id)
            logging.info("✅ 데이터베이스 스키마 성공적으로 가져왔습니다.") # print 대신 logging 사용
            return database_info.get("properties", {})
        except APIResponseError as e:
            logging.error(f"데이터베이스 스키마 가져오기 실패: {e}", exc_info=True) # print 대신 logging 사용, 트레이스백 포함
            raise NotionAPIError(f"Failed to retrieve database schema: {e}") from e