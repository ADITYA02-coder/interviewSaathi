import { useRef } from "react";

/* A dependency-free code editor: line numbers, Tab / Shift+Tab, auto-indent, Ctrl/Cmd+Enter to run. */
export default function CodeEditor({ value, onChange, language = "python", readOnly = false, onRun, minRows = 14 }) {
  const ta = useRef(null), gutter = useRef(null);
  const unit = "    ";
  const lines = Math.max(minRows, value.split("\n").length + 1);

  const edit = (start, end, text, caret) => {
    const next = value.slice(0, start) + text + value.slice(end);
    onChange(next);
    requestAnimationFrame(() => { if (ta.current) ta.current.selectionStart = ta.current.selectionEnd = caret; });
  };

  const onKeyDown = (e) => {
    if (readOnly) return;
    const el = e.target, { selectionStart: a, selectionEnd: b } = el;
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); onRun?.(); return; }
    if (e.key === "Tab") {
      e.preventDefault();
      const ls = value.lastIndexOf("\n", a - 1) + 1;
      if (a !== b && value.slice(a, b).includes("\n") || e.shiftKey) {
        const block = value.slice(ls, b), out = block.split("\n").map((l) => (e.shiftKey ? (l.startsWith(unit) ? l.slice(4) : l.replace(/^ {1,3}/, "")) : unit + l)).join("\n");
        const delta = out.length - block.length;
        onChange(value.slice(0, ls) + out + value.slice(b));
        requestAnimationFrame(() => { el.selectionStart = Math.max(ls, a + (e.shiftKey ? Math.min(0, delta) : 4)); el.selectionEnd = b + delta; });
      } else edit(a, b, unit, a + unit.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const ls = value.lastIndexOf("\n", a - 1) + 1, line = value.slice(ls, a);
      let indent = line.match(/^\s*/)[0];
      if (/[:{(\[]\s*$/.test(line)) indent += unit;
      const after = value[b], closing = (line.trimEnd().endsWith("{") && after === "}") ? "\n" + line.match(/^\s*/)[0] : "";
      edit(a, b, "\n" + indent + closing, a + 1 + indent.length);
    }
  };

  return (
    <div className={`editor ${readOnly ? "ro" : ""}`}>
      <div className="gutter" ref={gutter} aria-hidden="true">{Array.from({ length: lines }, (_, i) => <div key={i}>{i + 1}</div>)}</div>
      <textarea ref={ta} value={value} readOnly={readOnly} spellCheck={false} autoCapitalize="off" autoCorrect="off" wrap="off" rows={lines}
        aria-label={`${language} code editor`} onChange={(e) => onChange(e.target.value)} onKeyDown={onKeyDown}
        onScroll={(e) => { if (gutter.current) gutter.current.scrollTop = e.target.scrollTop; }} />
    </div>
  );
}
