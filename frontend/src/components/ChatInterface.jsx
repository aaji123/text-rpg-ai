import { useState } from "react";

/** Render the active exchange and keep action entry usable during requests. */
export default function ChatInterface({ messages, onSend, onRoll, busy }) {
  const [text, setText] = useState("");

  /** Route a slash roll to the dice endpoint; send all other text to the narrator. */
  async function submit(event) {
    event.preventDefault();
    const action = text.trim();
    if (!action || busy) return;
    setText("");
    if (action.startsWith("/roll ")) await onRoll(action.slice(6).trim());
    else await onSend(action);
  }

  return (
    <section className="chat-panel">
      <div className="chat-heading"><div><span className="eyebrow">THE CHRONICLE</span><h2>What do you do?</h2></div><span className="save-indicator">● Saved locally</span></div>
      <div className="messages" aria-live="polite">
        {messages.length === 0 && <div className="welcome-card"><span className="welcome-mark">✦</span><h3>Your story is waiting.</h3><p>Describe an action to begin. Use <code>/roll 1d20</code> when you need a roll.</p></div>}
        {messages.map((message, index) => <article className={`message ${message.role}`} key={`${index}-${message.text.slice(0, 12)}`}><span className="message-label">{message.role === "player" ? "YOU" : message.role === "roll" ? "DICE" : "NARRATOR"}</span><p>{message.text}</p></article>)}
        {busy && <div className="typing"><i /><i /><i /> <span>The narrator is thinking</span></div>}
      </div>
      <form className="composer" onSubmit={submit}>
        <input value={text} onChange={(event) => setText(event.target.value)} placeholder="Describe your action…" aria-label="Your action" disabled={busy} />
        <button type="submit" disabled={busy || !text.trim()} aria-label="Send action">↗</button>
      </form>
      <div className="composer-hint">ENTER TO SEND <span>·</span> TRY <code>/roll 2d6+3</code></div>
    </section>
  );
}
