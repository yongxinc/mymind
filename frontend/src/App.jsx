import { useState, useRef, useEffect, useCallback } from "react";

const API = "http://localhost:8001";

// ─── Design tokens ────────────────────────────────────────────────────────────
const T = {
  bgBase:    "#09080F",
  bgSurf:    "#0D0C1A",
  bgCard:    "#110F20",
  bgInput:   "#0C0B18",
  brd:       "#1E1C32",
  brdFaint:  "#141228",
  amber:     "#C07820",
  amberLt:   "#E09A30",
  amberGlow: "#B8701820",
  blue:      "#4878C8",
  blueLt:    "#6898E0",
  blueGlow:  "#3060C020",
  text:      "#CBC2DC",
  textSub:   "#554E72",
  textDim:   "#221D38",
  mono:      "'Space Mono', monospace",
  serif:     "'Lora', Georgia, serif",
  display:   "'Cormorant Garamond', Georgia, serif",
};

const KB_COLOR = {
  thesis:   "#9880F0",
  meetings: "#5898F0",
  study:    "#48C890",
  tech:     "#E09840",
  general:  "#707888",
};

const KB_LABEL = {
  thesis: "論文", meetings: "會議", study: "學習", tech: "技術", general: "一般",
};

const INTENT_META = {
  query:  { label: "知識查詢", color: T.blue,    Icon: SearchIcon },
  ingest: { label: "新增文件", color: "#48C890", Icon: InboxIcon },
  plan:   { label: "學習計畫", color: T.amber,   Icon: CalendarIcon },
  "":     { label: "分析中",   color: T.textSub, Icon: SettingsIcon },
};

const SUGGESTED = [
  { text: "我的論文裡 Fuzzy Extractor 的參數設定是什麼？", intent: "query" },
  { text: "上次 TIE 會議討論了什麼結論？",                  intent: "query" },
  { text: "幫我規劃 TOEIC 5/31 前的讀書計畫，目標 860 分", intent: "plan"  },
  { text: "TOEIC Part 5 我筆記了哪些文法重點？",           intent: "query" },
];

// ─── SVG Icons ────────────────────────────────────────────────────────────────
function SearchIcon({ size = 13, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ display: "block", flexShrink: 0 }}>
      <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
    </svg>
  );
}
function InboxIcon({ size = 13, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ display: "block", flexShrink: 0 }}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
function CalendarIcon({ size = 13, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ display: "block", flexShrink: 0 }}>
      <rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}
function SettingsIcon({ size = 13, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ display: "block", flexShrink: 0 }}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
function PaperclipIcon({ size = 16, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ display: "block" }}>
      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}
function ChevronDownIcon({ size = 11, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ display: "block" }}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}
function SendIcon({ size = 14, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ display: "block" }}>
      <polygon points="22 2 15 22 11 13 2 9 22 2" fill={color} />
    </svg>
  );
}

// ─── Logo Mark ────────────────────────────────────────────────────────────────
function LogoMark({ size = 28 }) {
  return (
    <div style={{
      width: size, height: size, flexShrink: 0,
      background: `linear-gradient(135deg, ${T.amber} 0%, #8B4FD0 100%)`,
      borderRadius: Math.round(size * 0.28),
      display: "flex", alignItems: "center", justifyContent: "center",
      boxShadow: `0 0 18px ${T.amberGlow}`,
    }}>
      <svg width={size * 0.56} height={size * 0.56} viewBox="0 0 16 16" fill="none">
        <path d="M2 12 L5 4 L8 9 L11 4 L14 12" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.95"/>
      </svg>
    </div>
  );
}

// ─── Agent Step ───────────────────────────────────────────────────────────────
function AgentStep({ node, intent, kb, active, isLast }) {
  const meta = INTENT_META[intent] || INTENT_META[""];
  const kbColor = KB_COLOR[kb] || KB_COLOR.general;
  const nodeLabels = {
    classify_intent: "意圖分類",
    query_agent:     "查詢知識庫",
    ingest_agent:    "新增文件",
    plan_agent:      "生成計畫",
    calendar_read:   "讀取行事曆",
    notion_write:    "寫入 Notion",
  };

  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
      {/* Timeline column */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
        <div style={{
          width: 6, height: 6, borderRadius: 1,
          background: active ? meta.color : T.brd,
          boxShadow: active ? `0 0 8px ${meta.color}88` : "none",
          transform: "rotate(45deg)",
          transition: "all 0.3s",
          marginTop: 1,
        }} />
        {!isLast && (
          <div style={{ width: 1, height: 16, background: T.brdFaint, marginTop: 3 }} />
        )}
      </div>
      {/* Content */}
      <div style={{
        display: "flex", alignItems: "center", gap: 7, paddingBottom: isLast ? 0 : 4,
        fontSize: 10.5, fontFamily: T.mono,
        color: active ? T.text : T.textSub,
        letterSpacing: "0.01em",
        transition: "color 0.2s",
      }}>
        <span>{nodeLabels[node] || node}</span>
        {intent && (
          <span style={{
            display: "flex", alignItems: "center", gap: 3,
            padding: "1px 6px", borderRadius: 3,
            background: meta.color + "15", color: meta.color,
            fontSize: 9, letterSpacing: "0.05em",
          }}>
            <meta.Icon size={8} color={meta.color} />
            {meta.label}
          </span>
        )}
        {kb && kb !== "general" && (
          <span style={{
            padding: "1px 6px", borderRadius: 3,
            background: kbColor + "15", color: kbColor,
            fontSize: 9,
          }}>{KB_LABEL[kb] || kb}</span>
        )}
      </div>
    </div>
  );
}

// ─── Source Card ─────────────────────────────────────────────────────────────
function SourceCard({ source }) {
  const [open, setOpen] = useState(false);
  const kbColor = KB_COLOR[source.kb] || KB_COLOR.general;

  return (
    <div style={{
      borderLeft: `2px solid ${kbColor}30`,
      transition: "border-color 0.2s",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = kbColor + "60"}
      onMouseLeave={e => e.currentTarget.style.borderColor = kbColor + "30"}
    >
      <button onClick={() => setOpen(!open)} style={{
        width: "100%", padding: "6px 10px", background: "transparent",
        border: "none", cursor: "pointer", display: "flex",
        alignItems: "center", gap: 8, color: T.textSub,
        fontFamily: T.mono, fontSize: 10.5, textAlign: "left",
        transition: "color 0.15s",
      }}
        onMouseEnter={e => e.currentTarget.style.color = T.text}
        onMouseLeave={e => e.currentTarget.style.color = T.textSub}
      >
        <span style={{
          color: kbColor, fontWeight: 700, fontSize: 9,
          letterSpacing: "0.08em", flexShrink: 0,
        }}>{KB_LABEL[source.kb] || source.kb}</span>
        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {source.source}
        </span>
        <span style={{ transform: open ? "rotate(180deg)" : "none", transition: "0.2s", flexShrink: 0 }}>
          <ChevronDownIcon size={10} color="currentColor" />
        </span>
      </button>
      {open && (
        <div style={{
          padding: "6px 10px 10px",
          borderTop: `1px solid ${T.brdFaint}`,
          fontFamily: T.serif, fontSize: 12,
          color: T.textSub, lineHeight: 1.75,
        }}>{source.content}</div>
      )}
    </div>
  );
}

// ─── Notion Link ─────────────────────────────────────────────────────────────
function NotionLink({ url }) {
  if (!url) return null;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      fontFamily: T.mono, fontSize: 9.5, letterSpacing: "0.07em",
      color: "#8868C8", textDecoration: "none",
      padding: "3px 9px 3px 7px", borderRadius: 3,
      border: "1px solid #4A3A8830",
      background: "#16103A",
      transition: "all 0.15s",
    }}
      onMouseEnter={e => { e.currentTarget.style.color = "#A888E8"; e.currentTarget.style.borderColor = "#6A50C840"; }}
      onMouseLeave={e => { e.currentTarget.style.color = "#8868C8"; e.currentTarget.style.borderColor = "#4A3A8830"; }}
    >
      <svg width={9} height={9} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
      </svg>
      已記錄到 Notion
    </a>
  );
}

// ─── Message ─────────────────────────────────────────────────────────────────
function Message({ msg }) {
  const isUser = msg.role === "user";
  const meta   = INTENT_META[msg.intent || ""] || INTENT_META[""];

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      alignItems: isUser ? "flex-end" : "flex-start",
      gap: 10, marginBottom: 40,
      animation: "msgIn 0.35s cubic-bezier(0.16,1,0.3,1) both",
    }}>
      {/* Sender label */}
      <div style={{
        display: "flex", alignItems: "center", gap: 7,
        fontFamily: T.mono, fontSize: 9, letterSpacing: "0.12em",
        color: isUser ? T.amber + "99" : T.textDim + "DD",
        textTransform: "uppercase",
      }}>
        {isUser ? "You" : (
          <>
            <span style={{ color: T.textDim }}>MyMind</span>
            {msg.intent && (
              <>
                <span style={{ color: T.brd }}>—</span>
                <span style={{ display: "flex", alignItems: "center", gap: 4, color: meta.color + "BB" }}>
                  <meta.Icon size={9} color={meta.color + "BB"} />
                  {meta.label}
                </span>
              </>
            )}
          </>
        )}
      </div>

      {/* Agent trace */}
      {!isUser && msg.steps && msg.steps.length > 0 && (
        <div style={{
          maxWidth: 460, paddingLeft: 4,
          animation: "fadeIn 0.2s ease both",
        }}>
          {msg.steps.map((step, i) => (
            <AgentStep
              key={i} {...step}
              active={i === msg.steps.length - 1 && msg.streaming}
              isLast={i === msg.steps.length - 1}
            />
          ))}
        </div>
      )}

      {/* Message body */}
      {isUser ? (
        <div style={{
          maxWidth: "70%",
          background: `linear-gradient(135deg, #1A1208 0%, #140E06 100%)`,
          border: `1px solid ${T.amber}28`,
          borderRadius: "12px 2px 12px 12px",
          padding: "11px 16px",
          fontFamily: T.serif, fontSize: 14, lineHeight: 1.8,
          color: "#D8C8A0",
        }}>
          {msg.content}
        </div>
      ) : (
        <div style={{
          maxWidth: "88%",
          borderLeft: `2px solid ${T.blue}22`,
          paddingLeft: 16,
          fontFamily: T.serif, fontSize: 14.5, lineHeight: 1.95,
          color: T.text,
          whiteSpace: "pre-wrap", wordBreak: "break-word",
        }}>
          {msg.content}
          {msg.streaming && (
            <span style={{
              display: "inline-block", width: 2, height: 16,
              background: T.blueLt, marginLeft: 4, borderRadius: 1,
              animation: "blink 0.65s step-end infinite",
              verticalAlign: "text-bottom",
            }} />
          )}
        </div>
      )}

      {/* Sources */}
      {msg.sources && msg.sources.length > 0 && (
        <div style={{ maxWidth: "88%", width: "100%", display: "flex", flexDirection: "column", gap: 0 }}>
          <div style={{
            fontFamily: T.mono, fontSize: 8.5, color: T.textDim,
            letterSpacing: "0.14em", textTransform: "uppercase",
            marginBottom: 6, paddingLeft: 12,
          }}>
            {msg.sources.length} 個參考來源
          </div>
          {msg.sources.map((s, i) => <SourceCard key={i} source={s} />)}
        </div>
      )}

      {/* Notion link */}
      {!isUser && msg.notion_url && <NotionLink url={msg.notion_url} />}
    </div>
  );
}

// ─── KB Status ────────────────────────────────────────────────────────────────
function KBStatus({ kbs }) {
  const entries = Object.entries(kbs);
  if (!entries.length) return null;
  return (
    <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
      {entries.map(([name, count]) => {
        const c = KB_COLOR[name] || KB_COLOR.general;
        return (
          <div key={name} style={{
            display: "flex", alignItems: "center", gap: 4,
            padding: "2px 8px", borderRadius: 2,
            background: c + "10", border: `1px solid ${c}20`,
            fontFamily: T.mono, fontSize: 9.5, letterSpacing: "0.04em",
          }}>
            <span style={{ color: c }}>{KB_LABEL[name]}</span>
            <span style={{ color: T.textSub }}>{count}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Integration Status ───────────────────────────────────────────────────────
function IntegrationStatus({ integrations, onConnectCalendar }) {
  if (!integrations) return null;
  const { notion, calendar_credentials, calendar_authenticated } = integrations;
  const calColor = calendar_authenticated ? "#48C890" : calendar_credentials ? T.amber : null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      {notion && (
        <span style={{
          display: "flex", alignItems: "center", gap: 4,
          fontFamily: T.mono, fontSize: 9, letterSpacing: "0.08em",
          color: "#9070D8", padding: "2px 7px", borderRadius: 2,
          background: "#9070D810", border: "1px solid #9070D820",
        }}>
          <span style={{ width: 3, height: 3, borderRadius: "50%", background: "#9070D8", display: "inline-block" }} />
          NOTION
        </span>
      )}
      {calColor && (
        <button onClick={calendar_authenticated ? undefined : onConnectCalendar} style={{
          display: "flex", alignItems: "center", gap: 4,
          fontFamily: T.mono, fontSize: 9, letterSpacing: "0.08em",
          color: calColor, padding: "2px 7px", borderRadius: 2,
          background: calColor + "10", border: `1px solid ${calColor}20`,
          cursor: calendar_authenticated ? "default" : "pointer",
          transition: "all 0.15s",
        }}>
          <span style={{ width: 3, height: 3, borderRadius: "50%", background: calColor, display: "inline-block" }} />
          {calendar_authenticated ? "CALENDAR" : "CALENDAR (授權)"}
        </button>
      )}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [messages,     setMessages]     = useState([]);
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [kbs,          setKbs]          = useState({});
  const [integrations, setIntegrations] = useState(null);
  const [dragging,     setDragging]     = useState(false);
  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (p.get("calendar_auth") === "success")
      window.history.replaceState({}, "", window.location.pathname);
  }, []);

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json())
      .then(d => { setKbs(d.kbs || {}); setIntegrations(d.integrations || null); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const refreshKbs = async () => {
    const d = await fetch(`${API}/kbs`).then(r => r.json()).catch(() => ({}));
    setKbs(d.kbs || {});
  };

  const handleConnectCalendar = async () => {
    try {
      const d = await fetch(`${API}/auth/google`).then(r => r.json());
      if (d.auth_url) window.open(d.auth_url, "_blank");
    } catch { }
  };

  const sendMessage = useCallback(async (text, ingestSource = "") => {
    if (!text.trim() || loading) return;
    setInput(""); setLoading(true);
    setMessages(prev => [...prev, { role: "user", content: text }]);
    setMessages(prev => [...prev, { role: "assistant", content: "", streaming: true, steps: [], intent: "", sources: [] }]);

    try {
      const res    = await fetch(`${API}/chat/stream`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, ingest_source: ingestSource }),
      });
      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n"); buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw === "[DONE]") {
            setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, streaming: false } : m));
            await refreshKbs(); break;
          }
          try {
            const chunk = JSON.parse(raw);
            setMessages(prev => prev.map((m, i) => {
              if (i !== prev.length - 1) return m;
              const steps = [...(m.steps || [])];
              if (!steps.find(s => s.node === chunk.node))
                steps.push({ node: chunk.node, intent: chunk.intent, kb: chunk.kb });
              return {
                ...m, steps,
                intent:     chunk.intent           || m.intent,
                content:    chunk.answer           || m.content,
                sources:    chunk.result?.sources  || m.sources,
                notion_url: chunk.notion_url || chunk.result?.notion_url || m.notion_url,
              };
            }));
          } catch { }
        }
      }
    } catch (err) {
      setMessages(prev => prev.map((m, i) =>
        i === prev.length - 1 ? { ...m, content: `錯誤：${err.message}`, streaming: false } : m
      ));
    } finally {
      setLoading(false); inputRef.current?.focus();
    }
  }, [loading]);

  const handleUpload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    setLoading(true);
    setMessages(prev => [...prev, { role: "user", content: `上傳文件：${file.name}` }]);
    setMessages(prev => [...prev, { role: "assistant", content: "正在處理文件…", streaming: true, steps: [], sources: [] }]);
    try {
      const res  = await fetch(`${API}/upload`, { method: "POST", body: fd });
      const data = await res.json();
      const answer = data.result?.type === "ingest"
        ? `已加入「${data.result.kb}」知識庫（${data.result.chunks} 個片段）\n\n**摘要：**\n${data.result.summary}`
        : "處理完成";
      setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, content: answer, streaming: false } : m));
      await refreshKbs();
    } catch (err) {
      setMessages(prev => prev.map((m, i) =>
        i === prev.length - 1 ? { ...m, content: `上傳失敗：${err.message}`, streaming: false } : m
      ));
    } finally { setLoading(false); }
  };

  const canSend = !loading && input.trim().length > 0;

  return (
    <div
      style={{ minHeight: "100vh", background: T.bgBase, display: "flex", flexDirection: "column" }}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handleUpload(f); }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Lora:ital,wght@0,400;0,500;1,400&family=Space+Mono:wght@400;700&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${T.brd}; border-radius: 2px; }
        @keyframes blink   { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes fadeIn  { from{opacity:0} to{opacity:1} }
        @keyframes msgIn   { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:none} }
        @keyframes spin    { to{transform:rotate(360deg)} }
        @keyframes shimmer { 0%{opacity:0.4;transform:scale(0.9)} 50%{opacity:1;transform:scale(1)} 100%{opacity:0.4;transform:scale(0.9)} }
        textarea { resize:none; }
        textarea:focus { outline:none; }
        button { font-family:inherit; }
      `}</style>

      {/* ── Header ── */}
      <header style={{
        height: 56, flexShrink: 0, padding: "0 28px",
        borderBottom: `1px solid ${T.brd}`,
        background: T.bgSurf,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <LogoMark size={28} />
          <div>
            <div style={{
              fontFamily: T.display, fontSize: 20, fontWeight: 600,
              color: T.text, letterSpacing: "0.01em", lineHeight: 1,
            }}>MyMind</div>
            <div style={{
              fontFamily: T.mono, fontSize: 8, color: T.textDim,
              letterSpacing: "0.1em", marginTop: 2,
            }}>LANGGRAPH · RAG · OLLAMA</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <IntegrationStatus integrations={integrations} onConnectCalendar={handleConnectCalendar} />
          <KBStatus kbs={kbs} />
        </div>
      </header>

      {/* Drag overlay */}
      {dragging && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: `${T.amber}08`,
          border: `2px dashed ${T.amber}40`,
          backdropFilter: "blur(3px)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{
            fontFamily: T.display, fontStyle: "italic",
            fontSize: 22, color: T.amberLt, letterSpacing: "0.03em",
          }}>
            拖放文件，加入知識庫
          </div>
        </div>
      )}

      {/* ── Messages area ── */}
      <div style={{
        flex: 1, overflowY: "auto",
        padding: "48px 32px",
        maxWidth: 860, width: "100%", margin: "0 auto",
        background: `radial-gradient(ellipse at 30% 0%, #12102808 0%, transparent 60%)`,
      }}>
        {messages.length === 0 ? (
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", minHeight: "60vh", gap: 44,
            animation: "msgIn 0.5s cubic-bezier(0.16,1,0.3,1) both",
          }}>
            {/* Hero */}
            <div style={{ textAlign: "center" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, marginBottom: 14 }}>
                <LogoMark size={40} />
                <div style={{
                  fontFamily: T.display, fontSize: 52, fontWeight: 600,
                  letterSpacing: "-0.01em", lineHeight: 1,
                  background: `linear-gradient(135deg, ${T.amberLt} 0%, #E8D070 40%, ${T.text} 100%)`,
                  WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}>MyMind</div>
              </div>
              <div style={{
                fontFamily: T.serif, fontStyle: "italic", fontSize: 15,
                color: T.textSub, lineHeight: 1.6,
              }}>
                你的個人知識庫 AI 助理
              </div>
              <div style={{
                fontFamily: T.mono, fontSize: 9.5, color: T.textDim,
                marginTop: 8, letterSpacing: "0.08em",
              }}>
                拖放 PDF · 用中文直接問 · 規劃讀書計畫
              </div>
            </div>

            {/* Suggested prompts */}
            <div style={{
              display: "grid", gridTemplateColumns: "repeat(2, 1fr)",
              gap: 10, maxWidth: 640, width: "100%",
            }}>
              {SUGGESTED.map((q, i) => {
                const meta = INTENT_META[q.intent];
                return (
                  <button key={i} onClick={() => sendMessage(q.text)} style={{
                    background: T.bgCard,
                    border: `1px solid ${T.brdFaint}`,
                    borderRadius: 6, padding: "13px 16px",
                    cursor: "pointer", textAlign: "left",
                    display: "flex", flexDirection: "column", gap: 8,
                    transition: "all 0.2s",
                    animationDelay: `${i * 0.06}s`,
                    animation: "msgIn 0.4s cubic-bezier(0.16,1,0.3,1) both",
                  }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = meta.color + "35";
                      e.currentTarget.style.background  = T.bgSurf;
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = T.brdFaint;
                      e.currentTarget.style.background  = T.bgCard;
                    }}
                  >
                    <span style={{
                      display: "flex", alignItems: "center", gap: 5,
                      fontFamily: T.mono, fontSize: 9, letterSpacing: "0.08em",
                      color: meta.color + "A0",
                    }}>
                      <meta.Icon size={9} color={meta.color + "A0"} />
                      {meta.label}
                    </span>
                    <span style={{
                      fontFamily: T.serif, fontSize: 13, lineHeight: 1.55,
                      color: T.textSub,
                    }}>{q.text}</span>
                  </button>
                );
              })}
            </div>

            <div style={{ fontFamily: T.mono, fontSize: 9, color: T.textDim, letterSpacing: "0.08em" }}>
              知識庫為空時請先新增文件
            </div>
          </div>
        ) : (
          messages.map((msg, i) => <Message key={i} msg={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div style={{
        borderTop: `1px solid ${T.brd}`,
        background: T.bgSurf,
        padding: "16px 28px 18px", flexShrink: 0,
      }}>
        <div style={{ maxWidth: 860, margin: "0 auto", display: "flex", gap: 8, alignItems: "flex-end" }}>
          {/* Upload */}
          <button
            onClick={() => fileInputRef.current?.click()}
            title="上傳 PDF"
            style={{
              width: 40, height: 40, borderRadius: 6, flexShrink: 0,
              background: "transparent", border: `1px solid ${T.brd}`,
              color: T.textSub, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = T.amber + "50"; e.currentTarget.style.color = T.amberLt; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.brd;          e.currentTarget.style.color = T.textSub; }}
          >
            <PaperclipIcon size={15} color="currentColor" />
          </button>
          <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md" style={{ display: "none" }}
            onChange={e => { handleUpload(e.target.files[0]); e.target.value = ""; }} />

          {/* Textarea */}
          <div style={{
            flex: 1, background: T.bgInput,
            border: `1px solid ${loading ? T.blue + "30" : T.brd}`,
            borderRadius: 8, transition: "border-color 0.2s",
          }}
            onFocusCapture={e => e.currentTarget.style.borderColor = T.amber + "40"}
            onBlurCapture={e  => e.currentTarget.style.borderColor = loading ? T.blue + "30" : T.brd}
          >
            <textarea
              ref={inputRef} value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
              placeholder="問問題、新增文件網址、或要求規劃讀書計畫…"
              rows={1}
              style={{
                width: "100%", background: "transparent", border: "none",
                padding: "11px 14px", color: T.text, fontSize: 14,
                fontFamily: T.serif, lineHeight: 1.5,
                maxHeight: 130, overflow: "auto",
              }}
            />
          </div>

          {/* Send */}
          <button
            onClick={() => sendMessage(input)} disabled={!canSend}
            style={{
              width: 40, height: 40, borderRadius: 6, flexShrink: 0,
              background: canSend ? `linear-gradient(135deg, ${T.amber}, #8B4FD0)` : "transparent",
              border: canSend ? "none" : `1px solid ${T.brd}`,
              color: canSend ? "#FFF" : T.textSub,
              cursor: canSend ? "pointer" : "default",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s",
              boxShadow: canSend ? `0 2px 16px ${T.amberGlow}` : "none",
            }}
            onMouseEnter={e => { if (canSend) e.currentTarget.style.boxShadow = `0 4px 24px ${T.amber}40`; }}
            onMouseLeave={e => { if (canSend) e.currentTarget.style.boxShadow = `0 2px 16px ${T.amberGlow}`; }}
          >
            {loading
              ? <div style={{ width: 13, height: 13, border: `2px solid ${T.textSub}`, borderTopColor: T.blueLt, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
              : <SendIcon size={13} color="currentColor" />
            }
          </button>
        </div>

        <div style={{
          maxWidth: 860, margin: "7px auto 0",
          fontFamily: T.mono, fontSize: 9, color: T.textDim,
          textAlign: "center", letterSpacing: "0.06em",
        }}>
          ENTER 送出 · SHIFT+ENTER 換行 · 拖放 PDF 直接上傳
        </div>
      </div>
    </div>
  );
}
