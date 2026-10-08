"""
MyMind — LangGraph Multi-Agent Core

Graph:
  classify_intent
      ↓
  route ──→ query_agent  ─────────────────→ END
        ──→ ingest_agent ──→ notion_write ──→ END
        ──→ calendar_read → plan_agent ───→ notion_write ──→ END
"""
import os
import logging
from datetime import datetime
from typing import TypedDict, Literal, Annotated
from pathlib import Path
import operator

from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END

from notion_client import NotionClient
from calendar_client import CalendarClient

logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────
LLM_MODEL       = os.getenv("OLLAMA_MODEL",      "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL",   "http://localhost:11434")
EMBED_MODEL     = os.getenv("EMBED_MODEL",        "all-MiniLM-L6-v2")
CHROMA_DIR      = os.getenv("CHROMA_DIR",         "./chroma_db")

VALID_KBS = ["thesis", "meetings", "study", "tech", "general"]

# ─── State ───────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages:      Annotated[list, operator.add]   # full conversation history
    intent:        str                              # query | ingest | plan
    kb:            str                              # which knowledge base
    ingest_source: str                              # path/url for ingestion
    source_name:   str                              # display name (e.g. original upload filename)
    result:        dict                             # agent output
    needs_notion:  bool                             # write to Notion?
    calendar_data: dict                             # calendar events / busy slots
    error:         str

# ─── Prompts ─────────────────────────────────────────────────────────────────
CLASSIFY_PROMPT = PromptTemplate.from_template("""
You are a router for a personal knowledge assistant.
The user may write in Traditional Chinese, English, or a mix of both.
Classify the intent into exactly one of: query, ingest, plan

Definitions:
- query:  user wants to search, find, or ask about their stored documents
- ingest: user wants to add/import a document, file, URL, or text to the knowledge base
- plan:   user wants a study plan, schedule, timetable, or progress tracking

Return ONLY "intent,kb" on one line. No explanation.
Knowledge bases: thesis, meetings, study, tech, general

- thesis:   academic papers, research notes, dissertation (論文/研究)
- meetings: meeting records, weekly reports (會議/週報)
- study:    TOEIC, vocabulary, grammar, language learning (學習/英文)
- tech:     technical docs, code, systems (技術/程式/工具)
- general:  everything else

Examples:
"Fuzzy Extractor 的參數是什麼" → query,thesis
"What did my thesis say about key derivation?" → query,thesis
"上次 TIE 會議討論了什麼" → query,meetings
"What was decided in last week's meeting?" → query,meetings
"幫我規劃 TOEIC 讀書計畫" → plan,study
"Make a study schedule for my thesis defense" → plan,thesis
"Add this PDF to my notes" → ingest,general
"把這個網址加進知識庫: https://..." → ingest,tech
"TOEIC Part 5 文法重點" → query,study
"Grafana 怎麼設定 alerting?" → query,tech

User message: {message}
Answer (intent,kb):""")

QUERY_PROMPT = PromptTemplate.from_template("""You are a helpful personal assistant with access to the user's private documents.
Language rules:
- Question in Traditional Chinese → answer in Traditional Chinese
- Question in English → answer in English
- Mixed language question → answer in Traditional Chinese

Be specific and cite which document the information comes from when possible.
If the context doesn't contain enough information, say so clearly rather than guessing.

Context from personal documents:
{context}

Conversation history:
{history}

Question: {question}

Answer:""")

KB_CLASSIFY_PROMPT = PromptTemplate.from_template("""
Classify this document into exactly one knowledge base.
Return ONLY the kb name, nothing else.

Knowledge bases:
- thesis:   academic papers, research notes, dissertation chapters
- meetings: meeting records, weekly reports, discussion summaries
- study:    TOEIC, vocabulary, grammar, language-learning materials
- tech:     technical documentation, code notes, system guides
- general:  anything else

Document preview:
{preview}

Knowledge base:""")

INGEST_SUMMARY_PROMPT = PromptTemplate.from_template("""
The following text has already been provided to you. Read it and write a summary in Traditional Chinese.
Use 3-5 bullet points (• prefix). Focus on key points useful to recall later.
If the text is very short, just describe what it is about in 1-2 bullet points.
Do NOT say you cannot access the document — the full text is below.

Text:
{content}

Summary (in Traditional Chinese):""")

PLAN_PROMPT = PromptTemplate.from_template("""
You are a personal study coach. Create a detailed, practical study plan in Traditional Chinese.
Today's date: {today}

Goal: {goal}

Relevant notes from knowledge base:
{context}

Calendar schedule for the next {range_days} days:
{calendar_info}

Instructions:
- If calendar data is provided, schedule study sessions around existing events
- Use specific dates (e.g., 04/28 週一 20:00–21:30)
- Each session should be 60–120 minutes
- Group related topics in the same session
- Include a milestone checkpoint every 1–2 weeks
- Aim for at least 3 study sessions per week
- End with a brief summary of total weekly hours

Study Plan:""")

# ─── Agent Class ─────────────────────────────────────────────────────────────
class MyMindAgent:
    def __init__(self):
        self.llm = Ollama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
        )
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)
        self._kbs: dict[str, Chroma] = {}
        self.notion   = NotionClient()
        self.calendar = CalendarClient()
        self._load_existing_kbs()
        self.graph = self._build_graph()

    # ── KB Management ─────────────────────────────────────────────────────────
    def _load_existing_kbs(self):
        base = Path(CHROMA_DIR)
        if not base.exists():
            return
        for kb_path in base.iterdir():
            if kb_path.is_dir() and kb_path.name in VALID_KBS:
                try:
                    self._kbs[kb_path.name] = Chroma(
                        persist_directory=str(kb_path),
                        embedding_function=self.embeddings,
                        collection_name=kb_path.name,
                    )
                except Exception:
                    logger.exception("Failed to load KB %s", kb_path.name)

    def _get_or_create_kb(self, kb_name: str) -> Chroma:
        if kb_name not in self._kbs:
            self._kbs[kb_name] = Chroma(
                persist_directory=os.path.join(CHROMA_DIR, kb_name),
                embedding_function=self.embeddings,
                collection_name=kb_name,
            )
        return self._kbs[kb_name]

    def list_kbs(self) -> dict:
        result = {}
        for kb_name, kb in self._kbs.items():
            try:
                result[kb_name] = kb._collection.count()
            except Exception:
                result[kb_name] = 0
        return result

    # ── Graph Nodes ───────────────────────────────────────────────────────────
    # Keyword shortcuts — avoids LLM misclassification on obvious patterns
    _INGEST_KW = ["加進知識庫", "加入知識庫", "新增到知識庫", "儲存到知識庫",
                  "記錄這段", "把這段", "把這篇", "ingest", "add to knowledge",
                  "save this", "store this"]
    _PLAN_KW   = ["讀書計畫", "學習計畫", "讀書規劃", "幫我規劃", "幫我安排",
                  "study plan", "study schedule", "make a plan", "create a plan",
                  "schedule for"]

    def _keyword_classify(self, msg: str) -> tuple[str, str] | None:
        lower = msg.lower()
        for kw in self._INGEST_KW:
            if kw.lower() in lower:
                return "ingest", "general"
        for kw in self._PLAN_KW:
            if kw.lower() in lower:
                return "plan", "study"
        return None

    def _classify_intent(self, state: AgentState) -> AgentState:
        last_msg = state["messages"][-1]["content"] if state["messages"] else ""

        # Fast-path: keyword match skips LLM call
        shortcut = self._keyword_classify(last_msg)
        if shortcut:
            intent, kb = shortcut
            return {**state, "intent": intent, "kb": kb, "error": ""}

        try:
            result = (CLASSIFY_PROMPT | self.llm).invoke({"message": last_msg}).strip()
            parts  = result.split(",")
            intent = parts[0].strip().lower()
            kb     = parts[1].strip().lower() if len(parts) > 1 else "general"
            if intent not in ["query", "ingest", "plan"]:
                intent = "query"
            if kb not in VALID_KBS:
                kb = "general"
        except Exception:
            logger.exception("Intent classification failed; defaulting to query")
            intent, kb = "query", "general"

        return {**state, "intent": intent, "kb": kb, "error": ""}

    def _route(self, state: AgentState) -> str:
        intent = state["intent"]
        if intent == "plan":
            return "calendar_read"  # always read calendar before planning
        return f"{intent}_agent"

    def _query_agent(self, state: AgentState) -> AgentState:
        question = state["messages"][-1]["content"]
        docs, seen = [], set()

        search_kbs = (
            ([state["kb"]] if state["kb"] in self._kbs else []) +
            [k for k in self._kbs if k != state["kb"]]
        )
        for kb_name in search_kbs:
            try:
                results = self._kbs[kb_name].similarity_search(question, k=3)
                for d in results:
                    key = d.page_content[:80]
                    if key not in seen:
                        seen.add(key)
                        d.metadata["_kb"] = kb_name
                        docs.append(d)
                if len(docs) >= 5:
                    break
            except Exception:
                logger.exception("Search failed in KB %s", kb_name)
                continue

        if not docs:
            answer = "知識庫裡目前沒有找到相關資料。請先新增文件。"
            sources = []
        else:
            context = "\n\n---\n\n".join(
                f"[來源: {d.metadata.get('source', d.metadata.get('_kb', 'unknown'))}]\n{d.page_content}"
                for d in docs
            )
            history = "\n".join(
                f"{'使用者' if m['role'] == 'user' else '助理'}: {m['content']}"
                for m in state["messages"][-6:-1]
            ) or "無"

            answer = (QUERY_PROMPT | self.llm).invoke({
                "context": context, "history": history, "question": question,
            })
            sources = [
                {
                    "content": d.page_content[:200],
                    "source": d.metadata.get("source", d.metadata.get("_kb", "unknown")),
                    "kb": d.metadata.get("_kb", "unknown"),
                }
                for d in docs[:3]
            ]

        return {
            **state,
            "result": {"type": "query", "answer": answer, "sources": sources},
            "messages": state["messages"] + [{"role": "assistant", "content": answer}],
        }

    def _ingest_agent(self, state: AgentState) -> AgentState:
        last_msg = state["messages"][-1]["content"]
        source   = state.get("ingest_source", "")

        # Load document
        try:
            if source.startswith(("http://", "https://")):
                docs         = WebBaseLoader(source).load()
                source_label = source
            elif source and Path(source).exists():
                loader       = PyPDFLoader(source) if source.lower().endswith(".pdf") else TextLoader(source)
                docs         = loader.load()
                source_label = state.get("source_name") or Path(source).name
            else:
                docs         = [Document(page_content=last_msg, metadata={"source": "direct_input"})]
                source_label = "direct_input"
        except Exception as e:
            return {
                **state,
                "error":  f"Failed to load document: {e}",
                "result": {"type": "ingest", "success": False, "error": str(e)},
                "messages": state["messages"] + [
                    {"role": "assistant", "content": f"文件載入失敗：{e}"}
                ],
            }

        # Auto-classify KB
        preview = docs[0].page_content[:500] if docs else ""
        try:
            detected_kb = (KB_CLASSIFY_PROMPT | self.llm).invoke({"preview": preview}).strip().lower()
            if detected_kb not in VALID_KBS:
                detected_kb = state["kb"]
        except Exception:
            logger.exception("KB auto-classification failed; using %s", state["kb"])
            detected_kb = state["kb"]

        # Chunk and store
        chunks = self.splitter.split_documents(docs)
        for chunk in chunks:
            chunk.metadata["source"] = source_label
        self._get_or_create_kb(detected_kb).add_documents(chunks)

        # Generate summary
        try:
            content_preview = " ".join(d.page_content for d in docs)[:3000]
            summary = (INGEST_SUMMARY_PROMPT | self.llm).invoke({"content": content_preview})
        except Exception:
            logger.exception("Summary generation failed")
            summary = "（摘要生成失敗）"

        answer = (
            f"已將文件加入「{detected_kb}」知識庫（{len(chunks)} 個片段）\n\n"
            f"**摘要：**\n{summary}"
        )

        return {
            **state,
            "result": {
                "type":    "ingest",
                "success": True,
                "kb":      detected_kb,
                "chunks":  len(chunks),
                "summary": summary,
                "source":  source_label,
            },
            "needs_notion": True,
            "messages": state["messages"] + [{"role": "assistant", "content": answer}],
        }

    def _calendar_read(self, state: AgentState) -> AgentState:
        """Fetch upcoming calendar events before plan generation."""
        data = self.calendar.get_events(days=21)
        return {**state, "calendar_data": data}

    def _plan_agent(self, state: AgentState) -> AgentState:
        goal      = state["messages"][-1]["content"]
        cal_data  = state.get("calendar_data", {})

        # Build calendar context for the prompt
        today = cal_data.get("today") or datetime.now().strftime("%Y-%m-%d")
        range_days = cal_data.get("range_days", 21)

        if cal_data.get("available") and cal_data.get("events"):
            event_lines = []
            for e in cal_data["events"][:20]:
                start = str(e.get("start", ""))
                # Format: "2024-04-28T20:00:00+08:00" → "04/28 20:00"
                if "T" in start:
                    date_part = start[5:10]   # MM-DD
                    time_part = start[11:16]  # HH:MM
                    label = f"{date_part.replace('-', '/')} {time_part}"
                else:
                    label = start[5:10].replace("-", "/")
                event_lines.append(f"• {e.get('summary', '(無標題)')} [{label}]")
            calendar_info = "\n".join(event_lines) or "無行程資料"
        else:
            calendar_info = "行事曆未連接，請自行安排時段"

        # Fetch relevant notes
        context = ""
        for kb_name in [state["kb"], "study", "thesis"]:
            if kb_name in self._kbs and not context:
                try:
                    docs = self._kbs[kb_name].similarity_search(goal, k=3)
                    context = "\n".join(d.page_content for d in docs)
                except Exception:
                    logger.exception("Note retrieval failed in KB %s", kb_name)

        try:
            plan = (PLAN_PROMPT | self.llm).invoke({
                "goal":          goal,
                "context":       context or "無現有筆記資料",
                "calendar_info": calendar_info,
                "range_days":    range_days,
                "today":         today,
            })
        except Exception as e:
            plan = f"計畫生成失敗：{e}"

        answer = f"**學習計畫**\n\n{plan}"

        return {
            **state,
            "result": {
                "type":           "plan",
                "plan":           plan,
                "goal":           goal,
                "calendar_used":  cal_data.get("available", False),
                "calendar_events": cal_data.get("events", []),
            },
            "needs_notion": True,
            "messages": state["messages"] + [{"role": "assistant", "content": answer}],
        }

    def _notion_write(self, state: AgentState) -> AgentState:
        """Write ingest summary or study plan to Notion."""
        if not state.get("needs_notion") or not self.notion.enabled:
            return state

        result     = state.get("result", {})
        notion_url = ""
        try:
            if result.get("type") == "ingest":
                notion_url = self.notion.write_ingest_summary(
                    source=result.get("source", "unknown"),
                    kb=result.get("kb", "general"),
                    chunks=result.get("chunks", 0),
                    summary=result.get("summary", ""),
                )
            elif result.get("type") == "plan":
                notion_url = self.notion.write_study_plan(
                    goal=result.get("goal", ""),
                    plan=result.get("plan", ""),
                    calendar_events=result.get("calendar_events"),
                )
        except Exception:
            logger.exception("Notion write failed")

        return {**state, "result": {**result, "notion_url": notion_url}}

    # ── Graph Builder ─────────────────────────────────────────────────────────
    def _build_graph(self) -> StateGraph:
        g = StateGraph(AgentState)

        g.add_node("classify_intent", self._classify_intent)
        g.add_node("query_agent",     self._query_agent)
        g.add_node("ingest_agent",    self._ingest_agent)
        g.add_node("calendar_read",   self._calendar_read)
        g.add_node("plan_agent",      self._plan_agent)
        g.add_node("notion_write",    self._notion_write)

        g.set_entry_point("classify_intent")
        g.add_conditional_edges("classify_intent", self._route, {
            "query_agent":  "query_agent",
            "ingest_agent": "ingest_agent",
            "calendar_read": "calendar_read",
        })
        g.add_edge("query_agent",   END)
        g.add_edge("ingest_agent",  "notion_write")
        g.add_edge("calendar_read", "plan_agent")
        g.add_edge("plan_agent",    "notion_write")
        g.add_edge("notion_write",  END)

        return g.compile()

    # ── Public API ────────────────────────────────────────────────────────────
    def _initial_state(self, message: str, ingest_source: str = "", source_name: str = "") -> AgentState:
        return {
            "messages":      [{"role": "user", "content": message}],
            "intent":        "",
            "kb":            "general",
            "ingest_source": ingest_source,
            "source_name":   source_name,
            "result":        {},
            "needs_notion":  False,
            "calendar_data": {},
            "error":         "",
        }

    def run(self, message: str, ingest_source: str = "", source_name: str = "") -> dict:
        final = self.graph.invoke(self._initial_state(message, ingest_source, source_name))
        return {
            "intent":      final["intent"],
            "kb":          final["kb"],
            "result":      final["result"],
            "needs_notion": final["needs_notion"],
            "notion_url":  final["result"].get("notion_url", ""),
            "error":       final.get("error", ""),
        }

    def stream(self, message: str, ingest_source: str = ""):
        """Yield per-node state updates as the graph executes."""
        for event in self.graph.stream(self._initial_state(message, ingest_source)):
            yield event

    def integration_status(self) -> dict:
        return {
            "notion": self.notion.enabled,
            "calendar_credentials": self.calendar.credentials_exist,
            "calendar_authenticated": self.calendar.authenticated,
        }
