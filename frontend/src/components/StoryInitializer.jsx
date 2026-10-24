import { useState } from "react";

const WORLD_TEMPLATES = ["Xianxia", "Fantasy", "Sci-Fi", "Cyberpunk"];
const STEPS = ["Campaign", "Starting point", "Plot pillars", "Review"];

/** Collect a campaign's premise and narrative anchors before creating its folder. */
export default function StoryInitializer({ onCancel, onCreate, onBrainstorm, busy, externalError }) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [worldTemplate, setWorldTemplate] = useState("Xianxia");
  const [settingDescription, setSettingDescription] = useState("");
  const [plotPillars, setPlotPillars] = useState([]);
  const [newPillar, setNewPillar] = useState("");
  const [brainstormIdea, setBrainstormIdea] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [brainstorming, setBrainstorming] = useState(false);
  const [error, setError] = useState("");

  /** Add one player-authored anchor and keep the list within storage limits. */
  function addPillar(value = newPillar) {
    const clean = value.trim();
    if (!clean || plotPillars.includes(clean)) return;
    if (clean.length > 160 || plotPillars.length >= 12) {
      setError("Pillars must be 160 characters or fewer, with up to 12 total.");
      return;
    }
    setPlotPillars((current) => [...current, clean]);
    setNewPillar("");
    setError("");
  }

  /** Request optional AI ideas and display them as one-click anchor choices. */
  async function getSuggestions() {
    if (brainstormIdea.trim().length < 3) {
      setError("Add a short idea first so the brainstorm has a starting point.");
      return;
    }
    setBrainstorming(true); setError("");
    try { setSuggestions(await onBrainstorm(brainstormIdea.trim(), worldTemplate)); }
    catch (reason) { setError(reason.message); }
    finally { setBrainstorming(false); }
  }

  /** Move between wizard pages after validating the fields needed there. */
  function nextStep() {
    setError("");
    if (step === 0 && !name.trim()) return setError("Give your story a name to continue.");
    if (step < STEPS.length - 1) setStep((current) => current + 1);
    else onCreate({ name: name.trim(), world_template: worldTemplate, setting_description: settingDescription.trim(), plot_pillars: plotPillars });
  }

  return (
    <div className="wizard-scrim" role="presentation">
      <section className="wizard-card" role="dialog" aria-modal="true" aria-labelledby="wizard-title">
        <header className="wizard-header"><div><span className="eyebrow">BEFORE THE FIRST CHAPTER</span><h2 id="wizard-title">Shape your world</h2></div><button className="icon-button" onClick={onCancel} aria-label="Close wizard">×</button></header>
        <nav className="wizard-steps" aria-label="Story setup steps">{STEPS.map((label, index) => <div className={index === step ? "wizard-step active" : index < step ? "wizard-step complete" : "wizard-step"} key={label}><span>{index < step ? "✓" : index + 1}</span>{label}</div>)}</nav>
        <div className="wizard-body">
          {step === 0 && <>
            <label className="wizard-field">Story name<input autoFocus value={name} maxLength={60} onChange={(event) => setName(event.target.value)} placeholder="The Jade Mountain" /></label>
            <fieldset className="template-picker"><legend>World template</legend><p>Choose a genre to shape the character sheet's stats and resource.</p><div className="template-grid">{WORLD_TEMPLATES.map((template) => <button type="button" className={worldTemplate === template ? "template-option selected" : "template-option"} key={template} onClick={() => setWorldTemplate(template)}><span>{template === "Xianxia" ? "☯" : template === "Fantasy" ? "♜" : template === "Sci-Fi" ? "⌁" : "◇"}</span>{template}</button>)}</div><small>Stat labels: {worldTemplate === "Xianxia" ? "Strength · Agility · Comprehension · Willpower · Qi" : worldTemplate === "Fantasy" ? "Strength · Dexterity · Intelligence · Wisdom · Mana" : worldTemplate === "Sci-Fi" ? "Agility · Endurance · Technical Skill · Energy" : "Body · Reflexes · Cool · Empathy · Stamina"}</small></fieldset>
          </>}
          {step === 1 && <label className="wizard-field">Where and when does the story begin?<textarea autoFocus rows="6" maxLength={2000} value={settingDescription} onChange={(event) => setSettingDescription(event.target.value)} placeholder="A remote mountain sect during the first snowfall of the year…" /><small>Describe the opening place, era, and immediate atmosphere.</small></label>}
          {step === 2 && <>
            <div className="pillar-heading"><div><h3>Plot pillars</h3><p>Long-term goals the story can grow toward at your pace.</p></div><span>{plotPillars.length}/12</span></div>
            <div className="pillar-add"><input value={newPillar} maxLength={160} onChange={(event) => setNewPillar(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addPillar(); } }} placeholder="e.g. Join the Azure Cloud Sect" /><button type="button" onClick={() => addPillar()}>Add</button></div>
            {plotPillars.length > 0 ? <ul className="pillar-list">{plotPillars.map((pillar, index) => <li key={`${pillar}-${index}`}><span>◇</span>{pillar}<button type="button" aria-label={`Remove ${pillar}`} onClick={() => setPlotPillars((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button></li>)}</ul> : <div className="pillar-empty">Add your own goals or ask for ideas below.</div>}
            <div className="brainstorm-box"><div className="brainstorm-title"><span>✦ &nbsp; BRAINSTORM WITH AI</span><small>OPTIONAL</small></div><div className="pillar-add"><input value={brainstormIdea} maxLength={1000} onChange={(event) => setBrainstormIdea(event.target.value)} placeholder="A vague idea, rival, mystery, or ambition…" /><button type="button" disabled={brainstorming} onClick={getSuggestions}>{brainstorming ? "Thinking…" : "Suggest"}</button></div>{suggestions.length > 0 && <div className="suggestion-list">{suggestions.map((suggestion) => <button type="button" key={suggestion} onClick={() => addPillar(suggestion)} disabled={plotPillars.includes(suggestion)}><span>＋</span>{suggestion}</button>)}</div>}</div>
          </>}
          {step === 3 && <div className="review-card"><span className="review-symbol">✧</span><h3>{name}</h3><div className="review-row"><span>World</span><strong>{worldTemplate}</strong></div><div className="review-row"><span>Starting point</span><strong>{settingDescription || "A new adventure begins."}</strong></div><div className="review-row"><span>Plot pillars</span><strong>{plotPillars.length ? plotPillars.join(" · ") : "None yet — you can add them later"}</strong></div><p>Your campaign will be saved locally as Markdown and JSON files.</p></div>}
          {(error || externalError) && <p className="wizard-error" role="alert">{error || externalError}</p>}
        </div>
        <footer className="wizard-footer"><button className="text-button" onClick={step === 0 ? onCancel : () => setStep((current) => current - 1)}>{step === 0 ? "Cancel" : "Back"}</button><button className="primary" disabled={busy || brainstorming} onClick={nextStep}>{step === STEPS.length - 1 ? busy ? "Creating…" : "Begin campaign" : "Continue"}<span> →</span></button></footer>
      </section>
    </div>
  );
}
