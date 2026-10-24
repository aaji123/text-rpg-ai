import { useCallback, useEffect, useState } from "react";
import { api } from "./services/api.js";
import ChatInterface from "./components/ChatInterface.jsx";
import CharacterSheet from "./components/CharacterSheet.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import StoryInitializer from "./components/StoryInitializer.jsx";
import HomeHub from "./components/HomeHub.jsx";

/** Coordinate the home library, active story, theme, and local API actions. */
export default function App() {
  const [stories, setStories] = useState([]);
  const [story, setStory] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [initializerOpen, setInitializerOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [view, setView] = useState("home");
  const [recentStoryId, setRecentStoryId] = useState(() => localStorage.getItem("text-rpg-story") || "");
  const [theme, setTheme] = useState(() => localStorage.getItem("text-rpg-theme") || "dark");

  /** Apply the saved theme at the document root so dialogs and scrollbars match. */
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("text-rpg-theme", theme);
  }, [theme]);

  /** Rebuild recent transcript messages from the portable Markdown event log. */
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

  /** Load the campaign list without forcing the player into a story view. */
  const refreshStories = useCallback(async () => {
    try { setStories(await api.stories()); }
    catch (reason) { setError(reason.message); }
  }, []);

  useEffect(() => { refreshStories(); }, [refreshStories]);

  /** Load a campaign, restore its recent transcript, and open the story view. */
  async function selectStory(id) {
    if (!id) return;
    setError("");
    try {
      const loaded = await api.loadStory(id);
      setStory(loaded);
      setMessages(restoreMessages(loaded.recent_history || ""));
      localStorage.setItem("text-rpg-story", id);
      setRecentStoryId(id);
      setView("story");
    } catch (reason) { setError(reason.message); }
  }

  /** Open the guided campaign setup so required context is captured first. */
  function createStory() { setInitializerOpen(true); setError(""); }

  /** Persist wizard choices together and enter the new campaign. */
  async function submitStoryInitialization(storyDraft) {
    setCreating(true);
    try {
      const created = await api.createStory(storyDraft);
      setStories((current) => [...current, created]);
      setInitializerOpen(false);
      let openingError = "";
      try { await api.beginStory(created.id); }
      catch (reason) { openingError = `Campaign created, but the opening scene could not be generated: ${reason.message}`; }
      await selectStory(created.id);
      if (openingError) setError(openingError);
    } catch (reason) { setError(reason.message); }
    finally { setCreating(false); }
  }

  /** Pass plot ideas and world settings to the optional AI brainstorm endpoint. */
  async function brainstorm(idea, worldSettings) {
    const result = await api.brainstorm(idea, worldSettings);
    return result.suggestions;
  }

  /** Generate a short example for one setup field from current world settings. */
  async function generateExample(field, worldSettings) {
    const result = await api.generateExample(field, worldSettings);
    return result.example;
  }

  /** Import a validated story archive and open the resulting local campaign. */
  async function importStory(file) {
    try {
      const imported = await api.importStory(file);
      setStories((current) => [imported, ...current.filter((item) => item.id !== imported.id)]);
      setError("");
      await selectStory(imported.id);
    } catch (reason) { setError(reason.message); }
  }

  /** Download one portable archive while keeping all campaign files local. */
  async function exportStory(item) {
    try {
      const archive = await api.exportStory(item.id);
      const address = URL.createObjectURL(archive);
      const link = document.createElement("a");
      link.href = address;
      link.download = `${item.id}.zip`;
      link.click();
      URL.revokeObjectURL(address);
    } catch (reason) { setError(reason.message); }
  }

  /** Confirm before deleting a folder and clear the selected story if needed. */
  async function deleteStory(item) {
    if (!window.confirm(`Delete “${item.name}” and all its local story files? This cannot be undone.`)) return;
    try {
      await api.deleteStory(item.id);
      setStories((current) => current.filter((entry) => entry.id !== item.id));
      if (recentStoryId === item.id) {
        localStorage.removeItem("text-rpg-story");
        setRecentStoryId("");
      }
      if (story?.id === item.id) { setStory(null); setMessages([]); setView("home"); }
      setError("");
    } catch (reason) { setError(reason.message); }
  }

  /** Send a player action and refresh JSON-backed character data after success. */
  async function sendMessage(text) {
    setBusy(true); setError("");
    setMessages((current) => [...current, { role: "player", text }]);
    try {
      const result = await api.sendMessage(story.id, text);
      setMessages((current) => [...current, { role: "narrator", text: result.response }]);
      try { setStory(await api.loadStory(story.id)); }
      catch { setError("The turn was saved, but the character sheet could not refresh."); }
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }

  /** Roll a check and show the backend's persisted result in the conversation. */
  async function rollDice(notation) {
    setBusy(true); setError("");
    try {
      const result = await api.rollDice(story.id, notation);
      setMessages((current) => [...current, { role: "roll", text: `${result.notation}: [${result.rolls.join(", ")}] ${result.modifier >= 0 ? "+" : "−"}${Math.abs(result.modifier)} = ${result.total}` }]);
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  }

  /** Save preferences so the next narrator turn uses the latest rules. */
  async function changeSettings(settings) {
    setStory((current) => ({ ...current, settings }));
    try {
      const saved = await api.saveSettings(story.id, settings);
      setStory((current) => ({ ...current, settings: saved }));
    } catch (reason) { setError(reason.message); }
  }

  function returnHome(event) {
    event.preventDefault();
    setView("home");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" onClick={returnHome} aria-label="Mythos home"><span className="brand-icon">✦</span><span>MYTHOS<small>LOCAL RPG ENGINE</small></span></a>
        <div className="topbar-tools"><span className="privacy"><i /> PRIVATE BY DESIGN</span><button className="theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>{theme === "dark" ? "☼" : "☾"}<span>{theme === "dark" ? "Light" : "Dark"}</span></button></div>
      </header>
      {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError("")}>×</button></div>}
      {view === "story" && story ? <>
        <div className="campaign-heading"><div><button className="back-home" onClick={() => setView("home")}>← Story library</button><span className="eyebrow">ACTIVE CAMPAIGN</span><h1>{story.name}</h1></div><span className="campaign-badge">✦ &nbsp;{story.settings.mode.toUpperCase()} MODE</span></div>
        <div className="workspace"><ChatInterface messages={messages} onSend={sendMessage} onRoll={rollDice} busy={busy} /><aside className="sidebar"><CharacterSheet state={story.state} goals={story.goals} plotPillars={story.plot_pillars} worldTemplate={story.settings.world_template} /><SettingsPanel settings={story.settings} onChange={changeSettings} disabled={busy} /><p className="privacy-note">Your story data stays on this machine unless you choose to export or share its folder. Narrator, brainstorm, and example prompts are sent to Groq.</p></aside></div>
      </> : <HomeHub stories={stories} recentStoryId={recentStoryId} onCreate={createStory} onLoad={selectStory} onDelete={deleteStory} onImport={importStory} onExport={exportStory} />}
      {initializerOpen && <StoryInitializer onCancel={() => setInitializerOpen(false)} onCreate={submitStoryInitialization} onBrainstorm={brainstorm} onGenerateExample={generateExample} busy={creating} externalError={error} />}
      <footer className="footer"><span>TEXT RPG AI</span><span>✦ &nbsp; YOUR STORY, YOURS TO KEEP</span></footer>
    </main>
  );
}
