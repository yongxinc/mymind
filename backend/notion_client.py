"""
MyMind — Notion API integration
Writes ingest summaries and study plans to a Notion database.

Setup:
  1. https://www.notion.so/my-integrations → New integration → copy token
  2. Open your database → ⋯ → Add connections → select integration
  3. Copy database ID from URL: notion.so/.../<DATABASE_ID>?v=...
  4. Set NOTION_TOKEN and NOTION_DATABASE_ID in .env
"""
import os
import requests
from datetime import datetime, timezone

NOTION_TOKEN       = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
NOTION_API_URL     = "https://api.notion.com/v1"
NOTION_VERSION     = "2022-06-28"


class NotionClient:
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN", NOTION_TOKEN)
        self.database_id = os.getenv("NOTION_DATABASE_ID", NOTION_DATABASE_ID)
        self._properties_ensured = False

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.database_id)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    # ── Block helpers ─────────────────────────────────────────────────────────
    @staticmethod
    def _heading(text: str, level: int = 2) -> dict:
        key = f"heading_{level}"
        return {"object": "block", "type": key,
                key: {"rich_text": [{"text": {"content": text}}]}}

    @staticmethod
    def _paragraph(text: str) -> dict:
        return {"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": text[:2000]}}]}}

    @staticmethod
    def _divider() -> dict:
        return {"object": "block", "type": "divider", "divider": {}}

    @staticmethod
    def _callout(text: str) -> dict:
        return {"object": "block", "type": "callout",
                "callout": {"rich_text": [{"text": {"content": text[:2000]}}],
                            "icon": {"type": "emoji", "emoji": "ℹ️"}}}

    # ── Property setup ────────────────────────────────────────────────────────
    def ensure_properties(self):
        """Create Type, KB, Date properties on the database if missing."""
        if self._properties_ensured or not self.enabled:
            return
        try:
            resp = requests.get(
                f"{NOTION_API_URL}/databases/{self.database_id}",
                headers=self._headers(), timeout=8,
            )
            if not resp.ok:
                return
            existing = set(resp.json().get("properties", {}).keys())
            updates = {}
            if "Type" not in existing:
                updates["Type"] = {"select": {}}
            if "KB" not in existing:
                updates["KB"] = {"select": {}}
            if "Date" not in existing:
                updates["Date"] = {"date": {}}
            if updates:
                requests.patch(
                    f"{NOTION_API_URL}/databases/{self.database_id}",
                    json={"properties": updates},
                    headers=self._headers(), timeout=8,
                )
            self._properties_ensured = True
        except Exception:
            pass

    # ── Writers ───────────────────────────────────────────────────────────────
    def _create_page(self, title: str, props: dict, children: list) -> str:
        """Create a Notion page; returns page URL or '' on failure."""
        if not self.enabled:
            return ""
        self.ensure_properties()

        base_props = {"Name": {"title": [{"text": {"content": title[:100]}}]}}
        base_props.update(props)

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": base_props,
            "children": children[:100],  # Notion max 100 blocks per request
        }
        resp = requests.post(
            f"{NOTION_API_URL}/pages",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        if resp.ok:
            return resp.json().get("url", "")

        # Fallback: title-only (skip custom properties if schema mismatch)
        payload["properties"] = {"Name": base_props["Name"]}
        resp = requests.post(
            f"{NOTION_API_URL}/pages",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        return resp.json().get("url", "") if resp.ok else ""

    def write_ingest_summary(
        self, source: str, kb: str, chunks: int, summary: str
    ) -> str:
        """Write an ingested-document summary. Returns Notion page URL."""
        title = f"[{kb.upper()}] {source}"
        props = {
            "Type": {"select": {"name": "Ingest"}},
            "KB":   {"select": {"name": kb}},
            "Date": {"date": {"start": datetime.now(timezone.utc).date().isoformat()}},
        }
        summary_lines = [l for l in summary.split("\n") if l.strip()]
        children = [
            self._heading("文件資訊"),
            self._callout(f"來源：{source}  ·  知識庫：{kb}  ·  片段數：{chunks}"),
            self._divider(),
            self._heading("文件摘要"),
        ] + [self._paragraph(line) for line in (summary_lines or ["（無摘要）"])]

        return self._create_page(title, props, children)

    def write_study_plan(
        self, goal: str, plan: str, calendar_events: list | None = None
    ) -> str:
        """Write a study plan. Returns Notion page URL."""
        title = f"[計畫] {goal}"
        props = {
            "Type": {"select": {"name": "Plan"}},
            "Date": {"date": {"start": datetime.now(timezone.utc).date().isoformat()}},
        }
        plan_lines = [l for l in plan.split("\n") if l.strip()]
        children = [
            self._heading("學習目標"),
            self._paragraph(goal),
            self._divider(),
            self._heading("學習計畫"),
        ] + [self._paragraph(line) for line in (plan_lines[:40] or ["（無計畫內容）"])]

        if calendar_events:
            event_text = "\n".join(
                f"• {e.get('summary', '(無標題)')}: "
                f"{str(e.get('start', ''))[:16].replace('T', ' ')} ~ "
                f"{str(e.get('end', ''))[:16].replace('T', ' ')}"
                for e in calendar_events[:10]
            )
            children += [
                self._divider(),
                self._heading("行事曆參考"),
                self._paragraph(event_text),
            ]

        return self._create_page(title, props, children)
