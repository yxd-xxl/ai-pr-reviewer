/** Simple Markdown renderer: **bold**, *italic*, `code`, [links](url), lists, headers */
export default function MarkdownRenderer({ text }: { text: string }) {
  if (!text) return null;

  const html = text
    // Headers
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    // Bold and italic
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Inline code
    .replace(/`([^`]+)`/g, "<code style='background:#f3f4f6;padding:1px 4px;border-radius:3px;font-size:13px'>$1</code>")
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "<a href='$2' target='_blank' style='color:#2563eb'>$1</a>")
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre style='background:#1e293b;color:#e2e8f0;padding:12px;border-radius:6px;overflow:auto;font-size:12px'><code>$2</code></pre>")
    // Line breaks
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");

  return <div style={{ lineHeight: 1.7, fontSize: 14 }} dangerouslySetInnerHTML={{ __html: html }} />;
}
