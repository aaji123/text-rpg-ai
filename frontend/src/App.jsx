import { useCallback, useEffect, useState } from "react";
import { api } from "./services/api.js";
import StorySelector from "./components/StorySelector.jsx";
import ChatInterface from "./components/ChatInterface.jsx";
import CharacterSheet from "./components/CharacterSheet.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";

/** Coordinate story selection, game actions, settings, and local status. */
export default function App() {
  const [stories, setStories] = useState([]);
  const [story, setStory] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  /** Rebuild the visible recent transcript from the portable Markdown event log. */
  function restoreMessages(history) {
    const restored = [];
    const events = history.split(/(?=^## )/m).filter((event) => event.trimStart().startsWith("## "));
    for (const event of events) {
      const player = event.match(/\*\*Player:\*\* ([\s\S]*?)(?=\n\n\*\*Narrator:\*\*|$)/);
      const narrator = event.match(/\*\*Narrator:\*\* ([\s\S]*)$/);
      const dice = event.match(/\*\*Notation:\*\* `([^`]+)`[\s\S]*?\*\*Dice:\*\* \[([^\]]*)\][\s\S]*?\*\*Modifier:\*\* ([+-]?\d+)[\s\S]*?\*\*Total:\*\* (-?\d+)/);
      if (player) restored.push({ role: "player", text: player[1].trim() });
      if (narrator) restored.push({ role: "narrator", text: narrator[1].trim() });
      if (dice) restored.push({ role: "roll", text: `${dice[1]}: [${dice[2]}] ${Number(dice[3]) >= 0 ? "+" : "−"}${Math.abs(Number(dice[3]))} = ${dice[4]}` });
    }
    return restored;
  }

  /** Reload summaries and restore the last campaign selected in this browser. */
  const refreshStories = useCallback(async () => {
    try {
      const items = await api.stories();
      setStories(items);
      const savedId = localStorage.getItem("text-rpg-story");
      if (!story && items.length) await selectStory(items.find((item) => item.id === savedId)?.id || items[0].id);
    } catch (reason) { setError(reason.message); }
  }, [story]);

  /** Load one campaign, making its state the source for the side panels. */
  async function selectStory(id) {
    if (!id) return;
    setError("");
    try {
      const loaded = await api.loadStory(id);
      setStory(loaded);
      setMessages(restoreMessages(loaded.recent_history || ""));
      localStorage.setItem("text-rpg-story", id);
    } catch (reason) { setError(reason.message); }
  }

  useEffect(() => { refreshStories(); }, []);

  /** Create a campaign from a browser prompt and open it immediately. */
  async function createStory() {
    const name = window.prompt("Name your new story:");
    if (!name?.trim()) return;
    try {
      const created = await api.createStory(name.trim());
      setStories((current) => [...current, created]);
      await selectStory(created.id);
    } catch (reason) { setError(reason.message); }
  }

  /** Send a player action and show both sides of the saved conversation turn. */
  async function sendMessage(text) {
    setBusy(true); setError("");
    setMessages((current) => [...current, { role: "player", text }]);
    try {
      const result = await api.sendMessage(story.id, text);
      setMessages((current) => [...current, { role: "narrator", text: result.response }]);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }

  /** Roll a requested check and expose individual results in the chat stream. */
  async function rollDice(notation) {
    setBusy(true); setError("");
    try {
      const result = await api.rollDice(story.id, notation);
      setMessages((current) => [...current, { role: "roll", text: `${result.notation}: [${result.rolls.join(", ")}] ${result.modifier >= 0 ? "+" : "−"}${Math.abs(result.modifier)} = ${result.total}` }]);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }

  /** Save preferences on each change so the next action uses current rules. */
  async function changeSettings(settings) {
    setStory((current) => ({ ...current, settings }));
    try {
      const saved = await api.saveSettings(story.id, settings);
      setStory((current) => ({ ...current, settings: saved }));
    } catch (reason) { setError(reason.message); }
  }

  return (
    <main className="app-shell">
      <header className="topbar"><a className="brand" href="#"><span className="brand-icon">✦</span><span>MYTHOS<small>LOCAL RPG ENGINE</small></span></a><StorySelector stories={stories} selectedId={story?.id} onSelect={selectStory} onCreate={createStory} /><span className="privacy"><i /> PRIVATE BY DESIGN</span></header>
      {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError("")}>×</button></div>}
      {!story ? <section className="empty-state"><span>✧</span><h1>A world, waiting.</h1><p>Create a story to begin your adventure.</p><button className="primary" onClick={createStory}>Create your first story</button></section> : <>
        <div className="campaign-heading"><div><span className="eyebrow">ACTIVE CAMPAIGN</span><h1>{story.name}</h1></div><span className="campaign-badge">✦ &nbsp;{story.settings.mode.toUpperCase()} MODE</span></div>
        <div className="workspace"><ChatInterface messages={messages} onSend={sendMessage} onRoll={rollDice} busy={busy} /><aside className="sidebar"><CharacterSheet character={story.character} goals={story.goals} /><SettingsPanel settings={story.settings} onChange={changeSettings} disabled={busy} /><p className="privacy-note">Your story data stays on this machine unless you choose to share its folder. Narrator messages are sent to Groq when you play.</p></aside></div>
      </>}
      <footer className="footer"><span>TEXT RPG AI</span><span>✦ &nbsp; YOUR STORY, YOURS TO KEEP</span></footer>
    </main>
  );
}
