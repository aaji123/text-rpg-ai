import { useState } from "react";
import HelpTip from "./HelpTip.jsx";

/** Render the active exchange and keep action entry usable during requests. */
export default function ChatInterface({ messages, onSend, onRoll, onRecap, busy }) {
  const [text, setText] = useState("");

  /** Route a slash roll to the dice endpoint; send all other text to the narrator. */
  async function submit(event) {
    event.preventDefault();
    const action = text.trim();
    if (!action || busy) return;
    setText("");
    if (action.toLowerCase() === "/recap") await onRecap();
    else if (action.startsWith("/roll ")) await onRoll(action.slice(6).trim());
    else await onSend(action);
  }

  return (
    <section className="chat-panel">
      <div className="chat-heading"><div><span className="eyebrow">THE CHRONICLE</span><h2>What do you do?</h2></div><div className="chat-tools"><span className="save-indicator">● Saved locally</span><button className="recap-button" type="button" onClick={onRecap} disabled={busy}>Recap</button></div></div>
      <div className="messages" aria-live="polite">
        {messages.length === 0 && <div className="welcome-card"><span className="welcome-mark">✦</span><h3>Your story is waiting.</h3><p>Describe an action to begin. Use <code>/roll 1d20</code> when you need a roll.</p></div>}
        {messages.map((message, index) => <article className={`message ${message.role}`} key={`${index}-${message.text.slice(0, 12)}`}><span className="message-label">{message.role === "player" ? "YOU" : message.role === "roll" ? "DICE" : message.role === "summary" ? "SESSION RECAP" : message.role === "ooc" ? "OUT OF CHARACTER" : "NARRATOR"}</span><p>{message.text}</p>{message.actions?.length > 0 && <div className="suggested-actions" aria-label="Suggested actions">{message.actions.map((action) => <button type="button" key={action} disabled={busy} onClick={() => onSend(action)}>{action}</button>)}</div>}</article>)}
        {busy && <div className="typing"><i /><i /><i /> <span>The narrator is thinking</span></div>}
      </div>
      <form className="composer" onSubmit={submit}>
        <div className="action-input-wrap"><input value={text} onChange={(event) => setText(event.target.value)} placeholder="Describe your action…" aria-label="Your action" disabled={busy} /><HelpTip text="Describe what your character attempts. The AI uses your character state, world rules, and recent history to narrate the outcome." /></div>
        <button type="submit" disabled={busy || !text.trim()} aria-label="Send action">↗</button>
      </form>
      <div className="composer-hint">ENTER TO SEND <span>·</span> <code>/roll 1d20 vs 15</code> <span>·</span> <code>/recap</code> <span>·</span> <code>/ooc question</code></div>
    </section>
  );
}
