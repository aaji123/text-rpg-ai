import { useState } from "react";
import HelpTip from "./HelpTip.jsx";
import CharacterCreator, { defaultCharacter, STAT_LABELS } from "./CharacterCreator.jsx";
import WorldBuilder, { defaultWorldSettings } from "./WorldBuilder.jsx";

const STEPS = ["Story", "World", "Character", "Review"];
const POINT_BUDGET = 72;

/** Orchestrate world and character setup before creating a campaign folder. */
export default function StoryInitializer({ onCancel, onCreate, onBrainstorm, onGenerateExample, busy, externalError }) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [worldTemplate, setWorldTemplate] = useState("Xianxia");
  const [worldSettings, setWorldSettings] = useState(() => defaultWorldSettings("Xianxia"));
  const [character, setCharacter] = useState(() => defaultCharacter("Xianxia"));
  const [error, setError] = useState("");

  /** Reset genre-dependent defaults while preserving user-authored world details. */
  function changeWorldTemplate(template) {
    setWorldTemplate(template);
    setWorldSettings((current) => ({
      ...defaultWorldSettings(template),
      setting_description: current.setting_description,
      plot_pillars: current.plot_pillars,
      tone: current.tone,
      mode: current.mode,
      world_power_level: current.world_power_level,
      starting_plane: current.starting_plane,
      house_rules: current.house_rules,
      atmosphere: current.atmosphere,
    }));
    setCharacter((current) => ({ ...defaultCharacter(template), identity: current.identity, inventory: current.inventory }));
  }

  /** Check bounds that benefit from immediate feedback before the API request. */
  function validateStep() {
    if (step === 0 && !name.trim()) return "Give your story a name to continue.";
    if (step === 1) {
      const realms = worldSettings.realm_hierarchy;
      if (worldSettings.setting_description.trim().length === 0) return "Describe where and when this story begins.";
      if (realms.length < 2 || realms.length > 100 || new Set(realms.map((realm) => realm.toLocaleLowerCase())).size !== realms.length) return "Use 2–100 unique realm names.";
      if (realms.some((realm) => !realm.trim() || realm.length > 100)) return "Realm names must be 1–100 characters.";
      if (!realms.includes(worldSettings.highest_power_level)) return "Choose the highest power level from your realm list.";
      if (!worldSettings.starting_plane.trim()) return "Set a starting plane.";
    }
    if (step === 2) {
      if (!character.identity.name.trim()) return "Add a character name to continue.";
      if (!character.identity.background.trim()) return "Add a short starting background.";
      if (!Number.isInteger(character.identity.age) || character.identity.age < 1 || character.identity.age > 999) return "Character age must be from 1 to 999.";
      const stats = Object.values(character.stats);
      if (stats.some((value) => value < 3) || stats.reduce((sum, value) => sum + value, 0) > POINT_BUDGET) return "Stats must stay at 3 or above and use no more than 72 points.";
      if (character.inventory.length > 50) return "Keep starting inventory to 50 items or fewer.";
      if (character.inventory.some((item) => item.kind === "Consumable" && (!Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 999))) return "Consumable quantities must be from 1 to 999.";
      if (character.inventory.some((item) => item.kind === "Durable" && (!Number.isInteger(item.max_durability) || item.max_durability < 1 || item.max_durability > 1000))) return "Durable item maximums must be from 1 to 1,000.";
    }
    return "";
  }

  /** Advance after validating the current page, then submit one complete draft. */
  function nextStep() {
    const validationError = validateStep();
    if (validationError) return setError(validationError);
    setError("");
    if (step < STEPS.length - 1) return setStep((current) => current + 1);
    const { setting_description, plot_pillars, ...settings } = worldSettings;
    onCreate({ name: name.trim(), world_template: worldTemplate, setting_description, plot_pillars, character, world_settings: settings });
  }

  return (
    <div className="wizard-scrim" role="presentation">
      <section className="wizard-card expanded-wizard" role="dialog" aria-modal="true" aria-labelledby="wizard-title">
        <header className="wizard-header"><div><span className="eyebrow">BEFORE THE FIRST CHAPTER</span><h2 id="wizard-title">Create your campaign</h2></div><button className="icon-button" onClick={onCancel} aria-label="Close wizard">×</button></header>
        <nav className="wizard-steps" aria-label="Story setup steps">{STEPS.map((label, index) => <div className={index === step ? "wizard-step active" : index < step ? "wizard-step complete" : "wizard-step"} key={label}><span>{index < step ? "✓" : index + 1}</span>{label}</div>)}</nav>
        <div className="wizard-body">
          {step === 0 && <div className="creator-section campaign-step"><label className="wizard-field"><span className="label-with-help">Story name<HelpTip text="The campaign name is used in your story library and local folder label." /></span><input autoFocus value={name} maxLength={60} onChange={(event) => setName(event.target.value)} placeholder="The Jade Mountain" /></label><fieldset className="template-picker"><legend>World template <HelpTip text="Genre determines stat labels, resource type, default realm ladder, and examples shown in the next steps." /></legend><p>Genre determines stat labels, resource, and starting realm progression.</p><div className="template-grid">{Object.keys(STAT_LABELS).map((template) => <button type="button" className={worldTemplate === template ? "template-option selected" : "template-option"} key={template} onClick={() => changeWorldTemplate(template)}><span>{template === "Xianxia" ? "☯" : template === "Fantasy" ? "♜" : template === "Sci-Fi" ? "⌁" : "◇"}</span>{template}</button>)}</div><small>Stats: {STAT_LABELS[worldTemplate].join(" · ")}</small></fieldset></div>}
          <div hidden={step !== 1}><WorldBuilder worldTemplate={worldTemplate} value={worldSettings} onChange={setWorldSettings} onBrainstorm={onBrainstorm} onGenerateExample={onGenerateExample} /></div>
          <div hidden={step !== 2}><CharacterCreator worldTemplate={worldTemplate} value={character} onChange={setCharacter} /></div>
          {step === 3 && <div className="review-card"><span className="review-symbol">✧</span><h3>{name}</h3><div className="review-row"><span>World</span><strong>{worldTemplate} · {worldSettings.tone} · {worldSettings.mode}</strong></div><div className="review-row"><span>Opening</span><strong>{worldSettings.setting_description}</strong></div><div className="review-row"><span>Plane & ceiling</span><strong>{worldSettings.starting_plane} · {worldSettings.highest_power_level}</strong></div><div className="review-row"><span>Character</span><strong>{character.identity.name}, age {character.identity.age} · {character.identity.background}</strong></div><div className="review-row"><span>Attributes</span><strong>{Object.entries(character.stats).map(([label, score]) => `${label} ${score}`).join(" · ")}</strong></div><div className="review-row"><span>Starting items</span><strong>{character.inventory.map((item) => item.name).join(" · ") || "None"}</strong></div><div className="review-row"><span>Plot pillars</span><strong>{worldSettings.plot_pillars.join(" · ") || "None yet"}</strong></div><p>Your campaign will be saved locally as structured JSON and readable Markdown.</p></div>}
          {(error || externalError) && <p className="wizard-error" role="alert">{error || externalError}</p>}
        </div>
        <footer className="wizard-footer"><button className="text-button" onClick={step === 0 ? onCancel : () => { setError(""); setStep((current) => current - 1); }}>{step === 0 ? "Cancel" : "Back"}</button><button className="primary" disabled={busy} onClick={nextStep}>{step === STEPS.length - 1 ? busy ? "Creating…" : "Begin campaign" : "Continue"}<span> →</span></button></footer>
      </section>
    </div>
  );
}
